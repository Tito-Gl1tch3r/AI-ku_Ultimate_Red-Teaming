import EmberObject from '@ember/object';
import { Context, makeContextMixin, adapter, identity } from './util/make-context-mixin';
import Registry from './util/registry';
import factoryFor from './util/factory-for';
import normalizeIdentifier from './util/normalize-identifier';
import { assert } from './util/assert';
import ExistingMixin from './existing-mixin';

class StoreContext extends Context {
  constructor(owner) {
    super(owner, owner.stores._context);
    this.adapter = null;
    this.databases = new Registry();
    this.internalModelFactory = this.parent.internalModelFactory;
    this.modelClassFactory = this.parent.modelClassFactory;
    this.modelFactory = this.parent.modelFactory;
  }
  get identity() {
    let identity = this._identity;
    if(!identity) {
      identity = this.create('models:store-identity');
      this._identity = identity;
    }
    return identity;
  }
  start() {
    this.adapter.start();
  }
  destroy() {
    this.adapter.destroy();
    this.databases.destroy();
  }
}

const StoreContextMixin = makeContextMixin(StoreContext);

export default EmberObject.extend(StoreContextMixin, ExistingMixin, {

  stores: null,
  identifier: null,

  adapter: adapter(),
  identity: identity(),

  _createAdapterForDatabase(database) {
    let adapter = this._context.adapter;
    let identifier = adapter.identifier;
    let factory = factoryFor(this, `models:stack/${identifier}/database/adapter`);
    assert(`database adapter '${identifier}' not registered`, !!factory);
    return factory.create({ store: this, adapter, database });
  },

  _createDatabaseForIdentifier(identifier) {
    let adapter = this._context.adapter.identifier;
    let factory = factoryFor(this, `models:stack/${adapter}/database`);
    if(!factory) {
      factory = factoryFor(this, 'models:database');
    }
    return factory.create({ store: this, identifier });
  },

  database(identifier) {
    let normalizedIdentifier = normalizeIdentifier(identifier);
    let databases = this._context.databases;

    let database = databases.get(normalizedIdentifier);
    if(!database) {
      database = this._createDatabaseForIdentifier(normalizedIdentifier);
      database._context.adapter = this._createAdapterForDatabase(database);
      databases.set(normalizedIdentifier, database);
      database._context.start();
    }

    return database;
  },

  model(databaseIdentifier, ...remaining) {
    return this.database(databaseIdentifier).model(...remaining);
  },

  compact() {
    this._context.databases.map(database => database.compact());
  },

  toStringExtension() {
    return this.get('identifier');
  }

});
