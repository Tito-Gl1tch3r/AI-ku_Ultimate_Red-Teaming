import Stores from 'ember-cli-models/-private/stores';
import Store from 'ember-cli-models/-private/store';
import Database from 'ember-cli-models/-private/database';
import ClassFactory from 'ember-cli-models/-private/class-factory';
import ModelClassFactory from 'ember-cli-models/-private/model-class-factory';
import InternalModelFactory from 'ember-cli-models/-private/internal-model-factory';
import InternalModelManager from 'ember-cli-models/-private/internal-model-manager';
import InternalModelIdentity from 'ember-cli-models/-private/internal-model-identity';
import InternalFilterManager from 'ember-cli-models/-private/internal-filter-manager';
import InternalFilterFactory from 'ember-cli-models/-private/internal-filter-factory';
import ModelFactory from 'ember-cli-models/-private/model-factory';
import FilterFactory from 'ember-cli-models/-private/filter-factory';
import DatabaseIdentity from 'ember-cli-models/-private/identity/database';
import StoreIdentity from 'ember-cli-models/-private/identity/store';
import StoresIdentity from 'ember-cli-models/-private/identity/stores';
import FilterFind from 'ember-cli-models/-private/model/filter-find';
import DataAdapter from 'ember-cli-models/-private/data-adapter';

export default {
  name: 'ember-cli-models:internal',
  initialize(container) {
    container.register('models:stores', Stores);
    container.register('models:store', Store);
    container.register('models:database', Database);
    container.register('models:class-factory', ClassFactory);
    container.register('models:model-class-factory', ModelClassFactory);
    container.register('models:internal-model-factory', InternalModelFactory);
    container.register('models:internal-model-manager', InternalModelManager);
    container.register('models:internal-model-identity', InternalModelIdentity);
    container.register('models:internal-filter-manager', InternalFilterManager);
    container.register('models:internal-filter-factory', InternalFilterFactory);
    container.register('models:model-factory', ModelFactory);
    container.register('models:filter-factory', FilterFactory);
    container.register('models:database-identity', DatabaseIdentity);
    container.register('models:store-identity', StoreIdentity);
    container.register('models:stores-identity', StoresIdentity);
    container.register('models:filter-find', FilterFind);
    container.register('data-adapter:main', DataAdapter);
  }
};
