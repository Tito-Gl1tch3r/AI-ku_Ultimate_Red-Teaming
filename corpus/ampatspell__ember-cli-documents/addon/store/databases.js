import Mixin from '@ember/object/mixin';
import { get } from '@ember/object';
import { isString } from '../util/assert';
import createNestedRegistry from '../util/create-nested-registry';

const DatabasesRegistry = createNestedRegistry({ key: '_databases' });

export default Mixin.create(DatabasesRegistry, {

  _databases: null,

  _normalizeDatabaseIdentifier(identifier) {
    isString('identifier', identifier);
    return identifier.trim();
  },

  _databaseNameForIdentifier(identifier) {
    let fn = get(this._opts, 'databaseNameForIdentifier');
    if(fn) {
      let name = fn(identifier);
      isString('database name', name);
      return name;
    }
    return identifier;
  },

  _createDatabase(identifier, name) {
    let store = this;
    let _adapter = this.get('_adapter').createDatabaseAdapter();
    let database = this._factoryFor(`documents:database`).create({ store, _adapter, name, identifier });
    _adapter.setProperties({ database });
    return database;
  },

  database(identifier) {
    let databases = this._databases;
    let normalizedIdentifier = this._normalizeDatabaseIdentifier(identifier);
    let database = databases.get(normalizedIdentifier);
    if(!database) {
      let name = this._databaseNameForIdentifier(normalizedIdentifier);
      database = this._createDatabase(normalizedIdentifier, name);
      databases.set(normalizedIdentifier, database);
    }
    return database;
  },

  _databaseWillDestroy(db) {
    let identifier = db.get('identifier');
    this._databases.remove(identifier);
  },

  willDestroy() {
    this._databases.destroy();
    this._super();
  }

});
