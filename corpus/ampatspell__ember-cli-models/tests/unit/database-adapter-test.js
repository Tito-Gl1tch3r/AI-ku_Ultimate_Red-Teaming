import EmberObject from '@ember/object';
import { run } from '@ember/runloop';
import { assign } from '@ember/polyfills';
import module from '../helpers/module-for-stores';
import { test } from '../helpers/qunit';
import Model from 'ember-cli-models/model/backed';
import StoreAdapter from 'ember-cli-models/adapter/store';
import DatabaseAdapter from 'ember-cli-models/adapter/database';

const Duck = Model.extend();

const Storage = EmberObject.extend({
  willDestroy() {
    this._adapter.storageWillDestroy(this);
    this._super();
  }
});

const MockStoreAdapter = StoreAdapter.extend();
const MockDatabaseAdapter = DatabaseAdapter.extend({

  modelDefinitionForStorage() {
    return {
      observe: [ 'type' ],
      type: storage => storage.get('type')
    };
  },

  build(modelName, data) {
    let storage = Storage.create(assign({}, data, { type: modelName, _adapter: this }));
    let content = this.get('content');
    if(content) {
      content.pushObject(storage);
    }
    return storage;
  },

  storageWillDestroy(storage) {
    let content = this.get('content');
    if(content) {
      content.removeObject(storage);
    }
  },

});

module('database-adapter-test', {
  beforeEach() {
    this.register('model:duck', Duck);
    this.registerAdapters('mock', MockStoreAdapter, MockDatabaseAdapter);
    this.adapter = 'mock';
  }
});

test('adapter observes add and remove content', function(assert) {
  let db = this.database;

  let one = db.model('duck', { id: '1' });
  let two = db.model('duck', { id: '2' });

  let one_ = one.get('storage');
  let two_ = two.get('storage');

  assert.deepEqual(db.get('identity').map(model => model), [ one, two ]);
  assert.deepEqual(db.get('adapter.content').map(storage => storage), [ one_, two_ ] );

  run(() => one.destroy());

  assert.deepEqual(db.get('identity').map(model => model), [ two ]);
  assert.deepEqual(db.get('adapter.content').map(storage => storage), [ two_ ]);
});

test('adapter ignores missing content', function(assert) {
  this.registerAdapters('mock', MockStoreAdapter, MockDatabaseAdapter.extend({
    content: null
  }));
  let db = this.database;
  let one = db.model('duck', { id: '1' });
  assert.deepEqual(db.get('identity').map(model => model), [ one ]);
});
