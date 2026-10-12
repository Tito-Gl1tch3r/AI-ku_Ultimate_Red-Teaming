import Component from '@ember/component';
import { getOwner } from '@ember/application';
import { inject as service } from '@ember/service';
import { computed } from '@ember/object';
import { reads } from '@ember/object/computed';
import layout from './template';
import { info } from 'documents/util/logger';

export default Component.extend({
  classNameBindings: [ ':ui-block', ':stores-identity' ],
  layout,

  stores: computed(function() {
    return getOwner(this).lookup('documents:stores');
  }),

  router: service(),

  documents: reads('stores.documentsIdentity'),
  models: reads('stores.modelsIdentity'),

  actions: {
    doc(doc) {
      this.get('router').transitionTo('documents.document', doc.get('id'));
    },
    model(model) {
      info(`window.model = ${model}`);
      window.model = model;
    }
  }

});
