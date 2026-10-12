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
	"fmt"
	"time"

	"bytes"
	"html/template"

	"github.com/golang/glog"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/util/runtime"
	"k8s.io/apimachinery/pkg/util/wait"
	coreinformers "k8s.io/client-go/informers/core/v1"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/kubernetes/scheme"
	typedcorev1 "k8s.io/client-go/kubernetes/typed/core/v1"
	corelisters "k8s.io/client-go/listers/core/v1"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/record"
	"k8s.io/client-go/util/workqueue"

	cmtv1alpha1 "github.com/openixia/kube-bro-configmaptemplate/pkg/apis/cmt/v1alpha1"
	clientset "github.com/openixia/kube-bro-configmaptemplate/pkg/client/clientset/versioned"
	cmtscheme "github.com/openixia/kube-bro-configmaptemplate/pkg/client/clientset/versioned/scheme"
	informers "github.com/openixia/kube-bro-configmaptemplate/pkg/client/informers/externalversions/cmt/v1alpha1"
	listers "github.com/openixia/kube-bro-configmaptemplate/pkg/client/listers/cmt/v1alpha1"
)

const controllerAgentName = "cmt"

const (
	// SuccessSynced is used as part of the Event 'reason' when a
	// ConfigMapTemplate is synced
	SuccessSynced = "Synced"
	// ErrResourceExists is used as part of the Event 'reason' when a
	// ConfigMapTemplate fails
	// to sync due to a ConfigMap of the same name already existing.
	ErrResourceExists = "ErrResourceExists"

	// MessageResourceExists is the message used for Events when a resource
	// fails to sync due to a ConfigMap already existing
	MessageResourceExists = "Resource %q already exists and is not managed by ConfigMapTemplate"
	// MessageResourceSynced is the message used for an Event fired when a
	// ConfigMapTemplate
	// is synced successfully
	MessageResourceSynced = "ConfigMapTemplate synced successfully"
)

// Controller is the controller implementation for ConfigMapTemplate resources
type Controller struct {
	// kubeclientset is a standard kubernetes clientset
	kubeclientset kubernetes.Interface
	// cmtclientset is a clientset for our own API group
	cmtclientset clientset.Interface

	configMapLister          corelisters.ConfigMapLister
	configMapsSynced         cache.InformerSynced
	configMapTemplatesLister listers.ConfigMapTemplateLister
	configMapTemplatesSynced cache.InformerSynced

	podLister corelisters.PodLister

	// workqueue is a rate limited work queue. This is used to queue work to be
	// processed instead of performing it as soon as a change happens. This
	// means we can ensure we only process a fixed amount of resources at a
	// time, and makes it easy to ensure we are never processing the same item
	// simultaneously in two different workers.
	workqueue workqueue.RateLimitingInterface
	// recorder is an event recorder for recording Event resources to the
	// Kubernetes API.
	recorder record.EventRecorder
}

// NewController returns a new cmt controller
func NewController(
	kubeclientset kubernetes.Interface,
	cmtclientset clientset.Interface,
	configMapInformer coreinformers.ConfigMapInformer,
	podInformer coreinformers.PodInformer,
	configMapTemplateInformer informers.ConfigMapTemplateInformer) *Controller {

	// Create event broadcaster
	// Add cmt types to the default Kubernetes Scheme so Events can be
	// logged for cmt types.
	cmtscheme.AddToScheme(scheme.Scheme)
	glog.V(4).Info("Creating event broadcaster")
	eventBroadcaster := record.NewBroadcaster()
	eventBroadcaster.StartLogging(glog.Infof)
	eventBroadcaster.StartRecordingToSink(&typedcorev1.EventSinkImpl{Interface: kubeclientset.CoreV1().Events("")})
	recorder := eventBroadcaster.NewRecorder(scheme.Scheme, corev1.EventSource{Component: controllerAgentName})

	controller := &Controller{
		kubeclientset:            kubeclientset,
		cmtclientset:      cmtclientset,
		configMapLister:          configMapInformer.Lister(),
		configMapsSynced:         configMapInformer.Informer().HasSynced,
		configMapTemplatesLister: configMapTemplateInformer.Lister(),
		configMapTemplatesSynced: configMapTemplateInformer.Informer().HasSynced,
		podLister:                podInformer.Lister(),
		workqueue:                workqueue.NewNamedRateLimitingQueue(workqueue.DefaultControllerRateLimiter(), "ConfigMapTemplates"),
		recorder:                 recorder,
	}

	glog.Info("Setting up event handlers")
	// Set up an event handler for when ConfigMapTemplate resources change
	configMapTemplateInformer.Informer().AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc: controller.enqueueConfigMapTemplate,
		UpdateFunc: func(old, new interface{}) {
			controller.enqueueConfigMapTemplate(new)
		},
	})
	// Set up an event handler for when ConfigMap resources change. This
	// handler will lookup the owner of the given ConfigMap, and if it is
	// owned by a ConfigMapTemplate resource will enqueue that ConfigMapTemplate resource for
	// processing. This way, we don't need to implement custom logic for
	// handling ConfigMap resources. More info on this pattern:
	// https://github.com/kubernetes/community/blob/8cafef897a22026d42f5e5bb3f104febe7e29830/contributors/devel/controllers.md
	configMapInformer.Informer().AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc: controller.handleObject,
		UpdateFunc: func(old, new interface{}) {
			newCfgMap := new.(*corev1.ConfigMap)
			oldCfgMap := old.(*corev1.ConfigMap)
			if newCfgMap.ResourceVersion == oldCfgMap.ResourceVersion {
				// Periodic resync will send update events for all known ConfigMaps.
				// Two different versions of the same ConfigMap will always have different RVs.
				return
			}
			controller.handleObject(new)
		},
		DeleteFunc: controller.handleObject,
	})

	// Set up an event handler for pod changes.
	podInformer.Informer().AddEventHandler(cache.ResourceEventHandlerFuncs{
		AddFunc: controller.handlePod,
		UpdateFunc: func(old, new interface{}) {
			controller.handlePod(new)
		},
		DeleteFunc: controller.handlePod,
	})

	return controller
}

// Run will set up the event handlers for types we are interested in, as well
// as syncing informer caches and starting workers. It will block until stopCh
// is closed, at which point it will shutdown the workqueue and wait for
// workers to finish processing their current work items.
func (c *Controller) Run(threadiness int, stopCh <-chan struct{}) error {
	defer runtime.HandleCrash()
	defer c.workqueue.ShutDown()

	// Start the informer factories to begin populating the informer caches
	glog.Info("Starting ConfigMapTemplate controller")

	// Wait for the caches to be synced before starting workers
	glog.Info("Waiting for informer caches to sync")
	if ok := cache.WaitForCacheSync(stopCh, c.configMapsSynced, c.configMapTemplatesSynced); !ok {
		return fmt.Errorf("failed to wait for caches to sync")
	}

	glog.Info("Starting workers")
	// Launch two workers to process ConfigMapTemplate resources
	for i := 0; i < threadiness; i++ {
		go wait.Until(c.runWorker, time.Second, stopCh)
	}

	glog.Info("Started workers")
	<-stopCh
	glog.Info("Shutting down workers")

	return nil
}

// runWorker is a long-running function that will continually call the
// processNextWorkItem function in order to read and process a message on the
// workqueue.
func (c *Controller) runWorker() {
	for c.processNextWorkItem() {
	}
}

// processNextWorkItem will read a single work item off the workqueue and
// attempt to process it, by calling the syncHandler.
func (c *Controller) processNextWorkItem() bool {
	obj, shutdown := c.workqueue.Get()

	if shutdown {
		return false
	}

	// We wrap this block in a func so we can defer c.workqueue.Done.
	err := func(obj interface{}) error {
		// We call Done here so the workqueue knows we have finished
		// processing this item. We also must remember to call Forget if we
		// do not want this work item being re-queued. For example, we do
		// not call Forget if a transient error occurs, instead the item is
		// put back on the workqueue and attempted again after a back-off
		// period.
		defer c.workqueue.Done(obj)
		var key string
		var ok bool
		// We expect strings to come off the workqueue. These are of the
		// form namespace/name. We do this as the delayed nature of the
		// workqueue means the items in the informer cache may actually be
		// more up to date that when the item was initially put onto the
		// workqueue.
		if key, ok = obj.(string); !ok {
			// As the item in the workqueue is actually invalid, we call
			// Forget here else we'd go into a loop of attempting to
			// process a work item that is invalid.
			c.workqueue.Forget(obj)
			runtime.HandleError(fmt.Errorf("expected string in workqueue but got %#v", obj))
			return nil
		}
		// Run the syncHandler, passing it the namespace/name string of the
		// ConfigMapTemplate resource to be synced.
		if err := c.syncHandler(key); err != nil {
			return fmt.Errorf("error syncing '%s': %s", key, err.Error())
		}
		// Finally, if no error occurs we Forget this item so it does not
		// get queued again until another change happens.
		c.workqueue.Forget(obj)
		glog.Infof("Successfully synced '%s'", key)
		return nil
	}(obj)

	if err != nil {
		runtime.HandleError(err)
		return true
	}

	return true
}

// syncHandler compares the actual state with the desired, and attempts to
// converge the two.
func (c *Controller) syncHandler(key string) error {
	// Convert the namespace/name string into a distinct namespace and name
	namespace, name, err := cache.SplitMetaNamespaceKey(key)
	if err != nil {
		runtime.HandleError(fmt.Errorf("invalid resource key: %s", key))
		return nil
	}

	// Get the ConfigMapTemplate resource with this namespace/name
	configMapTemplate, err := c.configMapTemplatesLister.ConfigMapTemplates(namespace).Get(name)
	if err != nil {
		// The ConfigMapTemplate resource may no longer exist, in which case we stop
		// processing.
		if errors.IsNotFound(err) {
			runtime.HandleError(fmt.Errorf("configMapTemplate '%s' in work queue no longer exists", key))
			return nil
		}

		return err
	}

	configMapName := configMapTemplate.ConfigMapName
	if configMapName == "" {
		// We choose to absorb the error here as the worker would requeue the
		// resource otherwise. Instead, the next time the resource is updated
		// the resource will be queued again.
		runtime.HandleError(fmt.Errorf("%s: ConfigMap name must be specified", key))
		return nil
	}

	// Get the ConfigMap with the name specified in ConfigMapTemplate.spec
	configmap, err := c.configMapLister.ConfigMaps(configMapTemplate.Namespace).Get(configMapName)
	mayneedupdate := true
	// If the resource doesn't exist, we'll create it
	if errors.IsNotFound(err) {
		configmap, err = c.kubeclientset.CoreV1().ConfigMaps(configMapTemplate.Namespace).Create(c.newConfigMap(configMapTemplate))
		mayneedupdate = false
	}

	// If an error occurs during Get/Create, we'll requeue the item so we can
	// attempt processing again later. This could have been caused by a
	// temporary network failure, or any other transient reason.
	if err != nil {
		return err
	}

	// If the ConfigMap is not controlled by this ConfigMapTemplate resource, we should log
	// a warning to the event recorder and ret
	if !metav1.IsControlledBy(configmap, configMapTemplate) {
		msg := fmt.Sprintf(MessageResourceExists, configmap.Name)
		c.recorder.Event(configMapTemplate, corev1.EventTypeWarning, ErrResourceExists, msg)
		return fmt.Errorf(msg)
	}

	// If this data does not equal the current desired data on the ConfigMap, we
	// should update the ConfigMap resource. Since the data is generated from a
	// template, the only way to know is to regen the data. So might as well
	// just update.
	if mayneedupdate {
		configmap, err = c.kubeclientset.CoreV1().ConfigMaps(configMapTemplate.Namespace).Update(c.newConfigMap(configMapTemplate))
	}

	// If an error occurs during Update, we'll requeue the item so we can
	// attempt processing again later. THis could have been caused by a
	// temporary network failure, or any other transient reason.
	if err != nil {
		return err
	}

	c.recorder.Event(configMapTemplate, corev1.EventTypeNormal, SuccessSynced, MessageResourceSynced)
	return nil
}

// enqueueConfigMapTemplate takes a ConfigMapTemplate resource and converts it into a namespace/name
// string which is then put onto the work queue. This method should *not* be
// passed resources of any type other than ConfigMapTemplate.
func (c *Controller) enqueueConfigMapTemplate(obj interface{}) {
	var key string
	var err error
	if key, err = cache.MetaNamespaceKeyFunc(obj); err != nil {
		runtime.HandleError(err)
		return
	}
	c.workqueue.AddRateLimited(key)
}

func (c *Controller) handlePod(obj interface{}) {
	var object metav1.Object
	var ok bool
	if object, ok = obj.(metav1.Object); !ok {
		tombstone, ok := obj.(cache.DeletedFinalStateUnknown)
		if !ok {
			runtime.HandleError(fmt.Errorf("error decoding object, invalid type"))
			return
		}
		object, ok = tombstone.Obj.(metav1.Object)
		if !ok {
			runtime.HandleError(fmt.Errorf("error decoding object tombstone, invalid type"))
			return
		}
		// glog.V(4).Infof("Recovered deleted object '%s' from tombstone", object.GetName())
	}
	// since templates may reference pods, but only within the same namespace,
	// we may need to reinstantiate any ConfigMapTemplates that live in the same namespace
	// as this pod
	glog.V(4).Infof("Processing pod: %s", object.GetName())
	relevant, err := c.configMapTemplatesLister.ConfigMapTemplates(object.GetNamespace()).List(labels.Everything())
	if err != nil {
		runtime.HandleError(fmt.Errorf("error listing ConfigMapTemplates for pod"))
		return
	}
	for _, t := range relevant {
		c.enqueueConfigMapTemplate(t)
	}
}

// handleObject will take any resource implementing metav1.Object and attempt
// to find the ConfigMapTemplate resource that 'owns' it. It does this by looking at the
// objects metadata.ownerReferences field for an appropriate OwnerReference.
// It then enqueues that ConfigMapTemplate resource to be processed. If the object does not
// have an appropriate OwnerReference, it will simply be skipped.
func (c *Controller) handleObject(obj interface{}) {
	var object metav1.Object
	var ok bool
	if object, ok = obj.(metav1.Object); !ok {
		tombstone, ok := obj.(cache.DeletedFinalStateUnknown)
		if !ok {
			runtime.HandleError(fmt.Errorf("error decoding object, invalid type"))
			return
		}
		object, ok = tombstone.Obj.(metav1.Object)
		if !ok {
			runtime.HandleError(fmt.Errorf("error decoding object tombstone, invalid type"))
			return
		}
		glog.V(4).Infof("Recovered deleted object '%s' from tombstone", object.GetName())
	}
	glog.V(4).Infof("Processing object: %s", object.GetName())
	if ownerRef := metav1.GetControllerOf(object); ownerRef != nil {
		// If this object is not owned by a ConfigMapTemplate, we should not do anything more
		// with it.
		if ownerRef.Kind != "ConfigMapTemplate" {
			return
		}

		configMapTemplate, err := c.configMapTemplatesLister.ConfigMapTemplates(object.GetNamespace()).Get(ownerRef.Name)
		if err != nil {
			glog.V(4).Infof("ignoring orphaned object '%s' of configMapTemplate '%s'", object.GetSelfLink(), ownerRef.Name)
			return
		}

		c.enqueueConfigMapTemplate(configMapTemplate)
		return
	}
}

// newConfigMap creates a new ConfigMap for a ConfigMapTemplate resource. It also sets
// the appropriate OwnerReferences on the resource so handleObject can discover
// the ConfigMapTemplate resource that 'owns' it.
func (c *Controller) newConfigMap(configMapTemplate *cmtv1alpha1.ConfigMapTemplate) *corev1.ConfigMap {
	ret := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:      configMapTemplate.ConfigMapName,
			Namespace: configMapTemplate.Namespace,
			OwnerReferences: []metav1.OwnerReference{
				*metav1.NewControllerRef(configMapTemplate, schema.GroupVersionKind{
					Group:   cmtv1alpha1.SchemeGroupVersion.Group,
					Version: cmtv1alpha1.SchemeGroupVersion.Version,
					Kind:    "ConfigMapTemplate",
				}),
			},
		},
		Data: map[string]string{},
	}
	funcMap := template.FuncMap{
		"pods": func(selectorstring string) ([]*corev1.Pod, error) {
			selector := labels.NewSelector()
			err := metav1.Convert_string_To_labels_Selector(&selectorstring, &selector, nil)
			if err != nil {
				return nil, err
			}
			podlist, err := c.podLister.Pods(configMapTemplate.Namespace).List(selector)
			if err != nil {
				return nil, err
			}
			glog.Infof("Pod list is '%s'", podlist)
			return podlist, nil
		},
		"modulo": func(i, j int) int { return i % j },
	}

	for k, v := range configMapTemplate.Data {
		t, err := template.New(k).Funcs(funcMap).Parse(v)
		if err != nil {
			runtime.HandleError(fmt.Errorf("error parsing template definition: " + err.Error()))
			continue;
		}

		var tpl bytes.Buffer
		err = t.Execute(&tpl, configMapTemplate)
		if err != nil {
			runtime.HandleError(fmt.Errorf("error instantiating template: " + err.Error()))
			continue;
		}

		ret.Data[k] = tpl.String()
	}
	return ret
}
