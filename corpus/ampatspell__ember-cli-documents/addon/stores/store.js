import Mixin from '@ember/object/mixin';
import { getOwner } from '@ember/application';
import { assign } from '@ember/polyfills';
import { dasherize } from '@ember/string';
import { object } from '../util/computed';
import { omit, pick } from '../util/object';
import { assert, isString, isObject } from '../util/assert';
import createNestedRegistry from '../util/create-nested-registry';

const StoresRegistry = createNestedRegistry({ key: '_stores' });

export default Mixin.create(StoresRegistry, {

  _stores: null,

  __storeFactory: null,
  __adapterFactories: object(),

  _storeFactory() {
    let Factory = this.__storeFactory;
    if(!Factory) {
      Factory = getOwner(this).factoryFor('documents:store');
      this.__storeFactory = Factory;
    }
    return Factory;
  },

  _adapterFactory(name, type) {
    let factories = this.get('__adapterFactories');
    let fullName = `${name}/${type}`;
    let factory = factories[fullName];
    if(!factory) {
      factory = getOwner(this).factoryFor(`documents:adapter/${fullName}`);
      factories[fullName] = factory;
    }
    return factory;
  },

  storeOptionsForIdentifier() {
    assert('override store.storeOptionsForIdentifier', false);
  },

  _storeOptionsForIdentifier(identifier) {
    let opts = this.storeOptionsForIdentifier(identifier);
    isObject('storeOptionsForIdentifier result', opts);
    return assign({ adapter: 'couch', fastboot: true }, opts);
  },

  _createStoreForIdentifier(identifier) {
    let opts = this._storeOptionsForIdentifier(identifier);

    let Adapter = this._adapterFactory(opts.adapter, 'store');

    let _adapter = Adapter.create({
      stores: this,
      adapter: opts.adapter,
      opts: omit(opts, [ 'adapter', 'databaseNameForIdentifier', 'fastboot' ])
    });

    let store = this._storeFactory().create({
      stores: this,
      identifier,
      _adapter,
      _opts: pick(opts, [ 'databaseNameForIdentifier', 'fastboot' ])
    });

    _adapter.setProperties({ store });

    let registry = this._stores;
    registry.set(identifier, store);

    store._didInitialize();

    return store;
  },

  _normalizeStoreIdentifier(identifier) {
    isString('identifier', identifier);
    return dasherize(identifier.trim());
  },

  store(identifier) {
    let normalizedIdentifier = this._normalizeStoreIdentifier(identifier);
    let registry = this._stores;
    let store = registry.get(normalizedIdentifier);
    if(!store) {
      store = this._createStoreForIdentifier(normalizedIdentifier);
    }
    return store;
  },

  _storeWillDestroy(store) {
    let identifier = store.get('identifier');
    this._stores.remove(identifier);
  },

  willDestroy() {
    this._stores.destroy();
    this._super();
  }

});
