import DatabaseAdapter from 'ember-cli-models/adapter/database';
import { computed } from '@ember/object';
import { getOwner } from '@ember/application';
import { assign } from '@ember/polyfills';

const definition = {
  observe: [ 'type' ],
  type: storage => storage.get('type')
};

export default DatabaseAdapter.extend({

  _factory: computed(function() {
    return getOwner(this).factoryFor('models:stack/local/storage');
  }).readOnly(),

  modelDefinitionForStorage() {
    return definition;
  },

  storage(modelName, props) {
    return this.get('_factory').create(assign({}, props, { type: modelName }));
  }

});
