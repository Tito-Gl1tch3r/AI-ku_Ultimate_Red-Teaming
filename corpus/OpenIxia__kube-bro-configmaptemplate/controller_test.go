/*
Copyright 2017 Keysight Technologies

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package main

import (
	"reflect"
	"testing"
	"time"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/util/diff"
	kubeinformers "k8s.io/client-go/informers"
	k8sfake "k8s.io/client-go/kubernetes/fake"
	core "k8s.io/client-go/testing"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/record"

	cmt "github.com/openixia/kube-bro-configmaptemplate/pkg/apis/cmt/v1alpha1"
	"github.com/openixia/kube-bro-configmaptemplate/pkg/client/clientset/versioned/fake"
	informers "github.com/openixia/kube-bro-configmaptemplate/pkg/client/informers/externalversions"
)

var (
	alwaysReady        = func() bool { return true }
	noResyncPeriodFunc = func() time.Duration { return 0 }
)

type fixture struct {
	t *testing.T

	client     *fake.Clientset
	kubeclient *k8sfake.Clientset
	// Objects to put in the store.
	configMapTemplateLister []*cmt.ConfigMapTemplate
	configMapLister         []*corev1.ConfigMap
	// Actions expected to happen on the client.
	kubeactions []core.Action
	actions     []core.Action
	// Objects from here preloaded into NewSimpleFake.
	kubeobjects []runtime.Object
	objects     []runtime.Object
}

func newFixture(t *testing.T) *fixture {
	f := &fixture{}
	f.t = t
	f.objects = []runtime.Object{}
	f.kubeobjects = []runtime.Object{}
	return f
}

func newConfigMapTemplate(name string, replicas *int32) *cmt.ConfigMapTemplate {
	return &cmt.ConfigMapTemplate{
		TypeMeta: metav1.TypeMeta{APIVersion: cmt.SchemeGroupVersion.String()},
		ObjectMeta: metav1.ObjectMeta{
			Name:      name,
			Namespace: metav1.NamespaceDefault,
		},
		ConfigMapName: "testname",
		Data: map[string]string{
			"Test": "{{ .Name }}",
		},
	}
}

func (f *fixture) newController() (*Controller, informers.SharedInformerFactory, kubeinformers.SharedInformerFactory) {
	f.client = fake.NewSimpleClientset(f.objects...)
	f.kubeclient = k8sfake.NewSimpleClientset(f.kubeobjects...)

	i := informers.NewSharedInformerFactory(f.client, noResyncPeriodFunc())
	k8sI := kubeinformers.NewSharedInformerFactory(f.kubeclient, noResyncPeriodFunc())

	c := NewController(f.kubeclient, f.client,
		k8sI.Core().V1().ConfigMaps(), k8sI.Core().V1().Pods(), i.CMT().V1alpha1().ConfigMapTemplates())

	c.configMapTemplatesSynced = alwaysReady
	c.configMapsSynced = alwaysReady
	c.recorder = &record.FakeRecorder{}

	for _, f := range f.configMapTemplateLister {
		i.CMT().V1alpha1().ConfigMapTemplates().Informer().GetIndexer().Add(f)
	}

	for _, d := range f.configMapLister {
		k8sI.Core().V1().ConfigMaps().Informer().GetIndexer().Add(d)
	}

	return c, i, k8sI
}

func (f *fixture) run(configMapTemplateName string) {
	f.runController(configMapTemplateName, true, false)
}

func (f *fixture) runExpectError(configMapTemplateName string) {
	f.runController(configMapTemplateName, true, true)
}

func (f *fixture) runController(configMapTemplateName string, startInformers bool, expectError bool) {
	c, i, k8sI := f.newController()
	if startInformers {
		stopCh := make(chan struct{})
		defer close(stopCh)
		i.Start(stopCh)
		k8sI.Start(stopCh)
	}

	err := c.syncHandler(configMapTemplateName)
	if !expectError && err != nil {
		f.t.Errorf("error syncing configMapTemplate: %v", err)
	} else if expectError && err == nil {
		f.t.Error("expected error syncing configMapTemplate, got nil")
	}

	actions := filterInformerActions(f.client.Actions())
	for i, action := range actions {
		if len(f.actions) < i+1 {
			f.t.Errorf("%d unexpected actions: %+v", len(actions)-len(f.actions), actions[i:])
			break
		}

		expectedAction := f.actions[i]
		checkAction(expectedAction, action, f.t)
	}

	if len(f.actions) > len(actions) {
		f.t.Errorf("%d additional expected actions:%+v", len(f.actions)-len(actions), f.actions[len(actions):])
	}

	k8sActions := filterInformerActions(f.kubeclient.Actions())
	for i, action := range k8sActions {
		if len(f.kubeactions) < i+1 {
			f.t.Errorf("%d unexpected actions: %+v", len(k8sActions)-len(f.kubeactions), k8sActions[i:])
			break
		}

		expectedAction := f.kubeactions[i]
		checkAction(expectedAction, action, f.t)
	}

	if len(f.kubeactions) > len(k8sActions) {
		f.t.Errorf("%d additional expected actions:%+v", len(f.kubeactions)-len(k8sActions), f.kubeactions[len(k8sActions):])
	}
}

// checkAction verifies that expected and actual actions are equal and both have
// same attached resources
func checkAction(expected, actual core.Action, t *testing.T) {
	if !(expected.Matches(actual.GetVerb(), actual.GetResource().Resource) && actual.GetSubresource() == expected.GetSubresource()) {
		t.Errorf("Expected\n\t%#v\ngot\n\t%#v", expected, actual)
		return
	}

	if reflect.TypeOf(actual) != reflect.TypeOf(expected) {
		t.Errorf("Action has wrong type. Expected: %t. Got: %t", expected, actual)
		return
	}

	switch a := actual.(type) {
	case core.CreateAction:
		e, _ := expected.(core.CreateAction)
		expObject := e.GetObject()
		object := a.GetObject()

		if !reflect.DeepEqual(expObject, object) {
			t.Errorf("Action %s %s has wrong object\nDiff:\n %s",
				a.GetVerb(), a.GetResource().Resource, diff.ObjectGoPrintDiff(expObject, object))
		}
	case core.UpdateAction:
		e, _ := expected.(core.UpdateAction)
		expObject := e.GetObject()
		object := a.GetObject()

		if !reflect.DeepEqual(expObject, object) {
			t.Errorf("Action %s %s has wrong object\nDiff:\n %s",
				a.GetVerb(), a.GetResource().Resource, diff.ObjectGoPrintDiff(expObject, object))
		}
	case core.PatchAction:
		e, _ := expected.(core.PatchAction)
		expPatch := e.GetPatch()
		patch := a.GetPatch()

		if !reflect.DeepEqual(expPatch, expPatch) {
			t.Errorf("Action %s %s has wrong patch\nDiff:\n %s",
				a.GetVerb(), a.GetResource().Resource, diff.ObjectGoPrintDiff(expPatch, patch))
		}
	}
}

// filterInformerActions filters list and watch actions for testing resources.
// Since list and watch don't change resource state we can filter it to lower
// nose level in our tests.
func filterInformerActions(actions []core.Action) []core.Action {
	ret := []core.Action{}
	for _, action := range actions {
		if len(action.GetNamespace()) == 0 &&
			(action.Matches("list", "configMapTemplates") ||
				action.Matches("watch", "configMapTemplates") ||
				action.Matches("list", "configmaps") ||
				action.Matches("watch", "configmaps") ||
				action.Matches("list", "pods") ||
				action.Matches("watch", "pods")) {
			continue
		}
		ret = append(ret, action)
	}

	return ret
}

func (f *fixture) expectCreateConfigMapAction(d *corev1.ConfigMap) {
	f.kubeactions = append(f.kubeactions, core.NewCreateAction(schema.GroupVersionResource{Resource: "configmaps"}, d.Namespace, d))
}

func (f *fixture) expectUpdateConfigMapAction(d *corev1.ConfigMap) {
	f.kubeactions = append(f.kubeactions, core.NewUpdateAction(schema.GroupVersionResource{Resource: "configmaps"}, d.Namespace, d))
}

func getKey(configMapTemplate *cmt.ConfigMapTemplate, t *testing.T) string {
	key, err := cache.DeletionHandlingMetaNamespaceKeyFunc(configMapTemplate)
	if err != nil {
		t.Errorf("Unexpected error getting key for configMapTemplate %v: %v", configMapTemplate.Name, err)
		return ""
	}
	return key
}

func TestCreatesConfigMap(t *testing.T) {
	f := newFixture(t)
	c, _, _ := f.newController()

	configMapTemplate := newConfigMapTemplate("test", int32Ptr(1))

	f.configMapTemplateLister = append(f.configMapTemplateLister, configMapTemplate)
	f.objects = append(f.objects, configMapTemplate)

	expConfigMap := c.newConfigMap(configMapTemplate)
	f.expectCreateConfigMapAction(expConfigMap)

	f.run(getKey(configMapTemplate, t))
}

/* This no longer plays out this way; we can't easily judge whether a
   change like new pods will alter the output of a template. So we must
   err on the side of updating. That makes this test fail.
func TestDoNothing(t *testing.T) {
	f := newFixture(t)
	c, _, _ := f.newController()

	configMapTemplate := newConfigMapTemplate("test", int32Ptr(1))
	d := c.newConfigMap(configMapTemplate)

	f.configMapTemplateLister = append(f.configMapTemplateLister, configMapTemplate)
	f.objects = append(f.objects, configMapTemplate)
	f.configMapLister = append(f.configMapLister, d)
	f.kubeobjects = append(f.kubeobjects, d)

	f.run(getKey(configMapTemplate, t))
}
*/

func TestUpdateConfigMap(t *testing.T) {
	f := newFixture(t)
	c, _, _ := f.newController()

	configMapTemplate := newConfigMapTemplate("test", int32Ptr(1))
	d := c.newConfigMap(configMapTemplate)

	// Update replicas
	expConfigMap := c.newConfigMap(configMapTemplate)

	f.configMapTemplateLister = append(f.configMapTemplateLister, configMapTemplate)
	f.objects = append(f.objects, configMapTemplate)
	f.configMapLister = append(f.configMapLister, d)
	f.kubeobjects = append(f.kubeobjects, d)

	f.expectUpdateConfigMapAction(expConfigMap)
	f.run(getKey(configMapTemplate, t))
}

func TestNotControlledByUs(t *testing.T) {
	f := newFixture(t)
	c, _, _ := f.newController()

	configMapTemplate := newConfigMapTemplate("test", int32Ptr(1))
	d := c.newConfigMap(configMapTemplate)

	d.ObjectMeta.OwnerReferences = []metav1.OwnerReference{}

	f.configMapTemplateLister = append(f.configMapTemplateLister, configMapTemplate)
	f.objects = append(f.objects, configMapTemplate)
	f.configMapLister = append(f.configMapLister, d)
	f.kubeobjects = append(f.kubeobjects, d)

	f.runExpectError(getKey(configMapTemplate, t))
}

func int32Ptr(i int32) *int32 { return &i }
