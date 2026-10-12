import { run } from '@ember/runloop';
import { module } from 'qunit';
import { resolve } from 'rsvp';
import startApp from '../helpers/start-app';
import destroyApp from '../helpers/destroy-app';
import EmberObject from '@ember/object';
import { assign } from '@ember/polyfills';
import Stores from 'ember-cli-models/stores';
import StoreAdapter from 'ember-cli-models/adapter/store';
import DatabaseAdapter from 'ember-cli-models/adapter/database';

const getter = (object, name, fn) => Object.defineProperty(object, name, { get: () => fn() });

const StoreNoopAdapter = StoreAdapter.extend();
const DatabaseNoopAdapter = DatabaseAdapter.extend({
  modelDefinitionForStorage() {
    return {
      observe: [ 'type' ],
      type: storage => storage.get('type')
    };
  },
  storage(name, props) {
    return EmberObject.create(assign(props, { type: name }));
  }
});

const createStores = owner => Stores.extend({
  storeOptionsForIdentifier() {
    let adapter = owner.adapter;
    return { adapter };
  }
});

export default function(name, options={}) {
  module(name, {
    beforeEach() {
      this.application = startApp();
      this.instance = this.application.buildInstance();

      this.register = (name, factory) => this.instance.register(name, factory);
      this.lookup = name => this.instance.lookup(name);

      this.adapter = 'noop';

      this.registerAdapters = (name, storeFactory, databaseFactory) => {
        this.register(`models:stack/${name}/store/adapter`, storeFactory);
        this.register(`models:stack/${name}/database/adapter`, databaseFactory)
      };

      this.registerAdapters('noop', StoreNoopAdapter, DatabaseNoopAdapter);

      this.register('models:stores', createStores(this));

      getter(this, 'stores', () => this.lookup('models:stores'));
      getter(this, 'store', () => this.stores.store('default'));
      getter(this, 'database', () => this.store.database('main'));

      this.identityForDatabase = database => database._context.internalModelIdentity._identity;
      getter(this, 'identity', () => this.identityForDatabase(this.database));

      let beforeEach = options.beforeEach && options.beforeEach.apply(this, arguments);
      return resolve(beforeEach);
    },
    afterEach() {
      let afterEach = options.afterEach && options.afterEach.apply(this, arguments);
      return resolve(afterEach).then(() => {
        run(() => this.instance.destroy());
        destroyApp(this.application);
      });
    }
  });
}
