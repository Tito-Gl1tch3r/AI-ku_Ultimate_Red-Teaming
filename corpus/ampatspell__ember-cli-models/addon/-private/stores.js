import EmberObject from '@ember/object';
import { Context, makeContextMixin, identity } from './util/make-context-mixin';
import { assign } from '@ember/polyfills';
import Registry from './util/registry';
import normalizeIdentifier from './util/normalize-identifier';
import { assert, isObject, isString } from './util/assert';
import { omit } from './util/object';
import factoryFor from './util/factory-for';
import ExistingMixin from './existing-mixin';
import FilterByClass from './identity/by-class';

class StoresContext extends Context {
  constructor(owner) {
    super(owner);
    this.stores = new Registry();
    this.classFactory = this.create('models:class-factory');
    this.modelClassFactory = this.create('models:model-class-factory');
    this.modelFactory = this.create('models:model-factory');
    this.internalModelFactory = this.create('models:internal-model-factory');
    this.internalFilterFactory = this.create('models:internal-filter-factory');
    this.internalFilterManager = this.create('models:internal-filter-manager');
    this.filterFactory = this.create('models:filter-factory');
  }
  get identity() {
    let identity = this._identity;
    if(!identity) {
      identity = this.create('models:stores-identity');
      this._identity = identity;
    }
    return identity;
  }
  get identityByClass() {
    let identityByClass = this._identityByClass;
    if(!identityByClass) {
      identityByClass = new FilterByClass(this.identity);
      this._identityByClass = identityByClass;
    }
    return identityByClass;
  }
  destroy() {
    this._identityByClass && this._identityByClass.destroy();
    this.stores.destroy();
  }
}

const ContextMixin = makeContextMixin(StoresContext);

export default EmberObject.extend(ContextMixin, ExistingMixin, {

  identity: identity(),

  storeOptionsForIdentifier() {
    assert(`override storeOptionsForIdentifier`, false);
  },

  _storeOptionsForIdentifier(identifier) {
    let opts = this.storeOptionsForIdentifier(identifier);
    isObject(`options for '${identifier}' store`, opts);
    isString(`store adapter for '${identifier}'`, opts.adapter);
    return opts;
  },

  _createAdapterForOptions(store, opts) {
    let name = opts.adapter;
    let identifier = normalizeIdentifier(name);
    let factory = factoryFor(this, `models:stack/${identifier}/store/adapter`);
    assert(`store adapter '${identifier}' is not registered`, !!factory);
    let props = assign({ identifier, store, options: omit(opts, [ 'adapter' ]) });
    return factory.create(props);
  },

  _createStoreForIdentifier(identifier, adapter) {
    let factory = factoryFor(this, `models:stack/${adapter}/store`);
    if(!factory) {
      factory = factoryFor(this, 'models:store');
    }
    return factory.create({ stores: this, identifier });
  },

  store(identifier) {
    let normalizedIdentifier = normalizeIdentifier(identifier);
    let stores = this._context.stores;

    let store = stores.get(normalizedIdentifier);
    if(!store) {
      let options = this._storeOptionsForIdentifier(identifier);
      store = this._createStoreForIdentifier(normalizedIdentifier, options.adapter);
      store._context.adapter = this._createAdapterForOptions(store, options);
      stores.set(normalizedIdentifier, store);
      store._context.start();
    }

    return store;
  },

  database(storeIdentifier, databaseIdentifier) {
    return this.store(storeIdentifier).database(databaseIdentifier);
  },

  model(storeIdentifier, databaseIdentifier, ...remaining) {
    return this.database(storeIdentifier, databaseIdentifier).model(...remaining);
  },

  compact() {
    this._context.stores.map(store => store.compact());
  }

});
