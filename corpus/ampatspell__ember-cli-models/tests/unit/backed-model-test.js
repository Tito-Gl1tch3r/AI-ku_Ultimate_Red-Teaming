import EmberObject from '@ember/object';
import { assign } from '@ember/polyfills';
import { run } from '@ember/runloop';
import module from '../helpers/module-for-stores';
import { test } from '../helpers/qunit';
import BackedModel from 'ember-cli-models/model/backed';
import TransientModel from 'ember-cli-models/model/transient';
import StoreAdapter from 'ember-cli-models/adapter/store';
import DatabaseAdapter from 'ember-cli-models/adapter/database';

const Storage = EmberObject.extend({

  willDestroy() {
    this._super();
    this._adapter.get('content').removeObject(this);
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

  _storage(modelName, data) {
    let storage = Storage.create(assign({  _destroysModel: true }, data, { type: modelName, _adapter: this }));
    this.get('content').pushObject(storage);
    return storage;
  },

  build(modelName, data) {
    return this._storage(modelName, data);
  },

  compact(storage) {
    return !!storage.get('_destroysModel');
  }

});

const Duck = BackedModel.extend();
const Thing = TransientModel.extend();
const YellowDuck = Duck.extend();
const GreenDuck = Duck.extend();

module('backed-model', {
  beforeEach() {
    this.register('model:thing', Thing);
    this.register('model:duck', Duck);
    this.register('model:yellow-duck', YellowDuck);
    this.register('model:green-duck', GreenDuck);
    this.registerAdapters('mock', MockStoreAdapter, MockDatabaseAdapter);
    this.adapter = 'mock';
  }
});

test('model is created with internal model', function(assert) {
  let model = this.database.model('duck');
  assert.ok(model);
  assert.ok(model._internal);
  assert.ok(model._internal._model === model);
  assert.ok(this.identity.all.includes(model._internal));
  assert.ok(this.identity.storage.get(model._internal.storage));
});

test('model destroy unsets internalModel._model', function(assert) {
  let model = this.database.model('duck');
  let internal = model._internal;

  assert.ok(internal._model === model);
  assert.ok(this.identity.all.includes(internal));
  assert.ok(this.identity.storage.get(internal.storage));

  run(() => model.destroy());

  assert.ok(internal._model === null);
  assert.ok(!this.identity.all.includes(internal));
  assert.ok(!this.identity.storage.get(internal.storage));
});

test('storage is accessible', function(assert) {
  let model = this.database.model('duck');
  assert.ok(model._internal.storage);
  assert.ok(model.get('storage') === model._internal.storage);
  assert.equal(model.get('storage.type'), 'duck');
});

test('model is created with storage and props provided by adapter', function(assert) {
  let model = this.database.model('duck', { id: 'duck:yellow' });
  let internal = model._internal;
  let storage = internal.storage;
  assert.ok(model);
  assert.ok(internal);
  assert.ok(storage);
  assert.equal(storage.get('id'), 'duck:yellow');
  assert.equal(storage.get('type'), 'duck');
});

test('model is recreated on type change', function(assert) {
  let model = this.database.model('duck');
  let internal = model._internal;

  assert.equal(model.get('storage.type'), 'duck');
  assert.ok(!model.isDestroyed);
  assert.ok(Duck.detectInstance(model));

  run(() => internal.storage.set('type', 'duck'));
  assert.ok(!model.isDestroyed);

  run(() => internal.storage.set('type', 'yellow-duck'));
  assert.ok(model.isDestroyed);
  assert.ok(!model._internal);
  model = internal.model(true);
  assert.ok(model);
  assert.ok(YellowDuck.detectInstance(model));

  run(() => internal.storage.set('type', 'green-duck'));
  assert.ok(model.isDestroyed);
  assert.ok(!model._internal);
  model = internal.model(true);
  assert.ok(model);
  assert.ok(GreenDuck.detectInstance(model));
});

test('model must be backed on recreate', function(assert) {
  let model = this.database.model('duck');
  let internal = model._internal;
  run(() => model.set('storage.type', 'thing'));
  try {
    internal.model(true);
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "model 'thing' must be backed model"
    });
  }
});

test('props are set to storage', function(assert) {
  let model = this.database.model('duck', { message: 'hey', id: 'duck:yellow' });

  assert.equal(model.get('storage.message'), 'hey');
  assert.equal(model.get('storage.id'), 'duck:yellow');
});

test('push storage returns Push', function(assert) {
  let adapter = this.database.get('adapter');
  let storage = adapter._storage('duck', { id: 'yellow' });

  let [ result ] = adapter.push([ storage ]);

  assert.ok(result);
  assert.ok(result.modelName);
  assert.ok(result.modelType);
  assert.ok(!result._internal._model);

  let model = result.model;
  assert.ok(result._internal._model);
  assert.ok(model.get('storage') === storage);

  assert.ok(this.identity.all.includes(model._internal));
  assert.ok(this.identity.storage.get(model._internal.storage));
});

test('push the same does not make a duplicate model', function(assert) {
  let adapter = this.database.get('adapter');
  let storage = adapter._storage('duck', { id: 'yellow' });

  let [ first ] = adapter.push([ storage ]);
  let [ second ] = adapter.push([ storage ]);

  assert.ok(first._internal === second._internal);
  assert.ok(first.model === second.model);

  assert.equal(this.identity.all.get('length'), 1);
  assert.ok(this.identity.storage.get(first._internal.storage));
});

test('delete storage and push again', function(assert) {
  let adapter = this.database.get('adapter');
  let storage = adapter._storage('duck', { id: 'yellow' });

  let internal = adapter.push([ storage ])[0]._internal;

  assert.ok(!internal.state.isDeleted);
  assert.equal(this.identity.all.get('length'), 1);
  assert.equal(this.identity.deleted.get('length'), 0);
  assert.ok(this.identity.all.includes(internal));
  assert.ok(this.identity.storage.get(storage));

  adapter.delete([ storage ]);

  assert.ok(internal.state.isDeleted);
  assert.equal(this.identity.all.get('length'), 0);
  assert.equal(this.identity.deleted.get('length'), 1);
  assert.ok(!this.identity.all.includes(internal));
  assert.ok(this.identity.storage.get(storage));

  adapter.push([ storage ]);

  assert.ok(!internal.state.isDeleted);
  assert.equal(this.identity.all.get('length'), 1);
  assert.equal(this.identity.deleted.get('length'), 0);
  assert.ok(this.identity.all.includes(internal));
  assert.ok(this.identity.storage.get(storage));
});

test('model name is required', function(assert) {
  let adapter = this.database.get('adapter');
  let storage = adapter._storage(null, { id: 'yellow' });
  try {
    adapter.push([ storage ])[0].model;
    assert.ok(false, 'should throw');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "definition.type must return type"
    });
  }
});

test('destroy model', function(assert) {
  let model = this.database.model('duck', { id: 'duck:yellow' });
  let internal = model._internal;
  let storage = model.get('storage');

  assert.ok(this.identity.all.includes(internal));
  assert.ok(!this.identity.deleted.includes(internal));
  assert.ok(this.identity.storage.get(storage));

  run(() => model.destroy());

  assert.ok(!this.identity.all.includes(internal));
  assert.ok(!this.identity.deleted.includes(internal));
  assert.ok(!this.identity.storage.get(storage));

  assert.ok(internal.isDestroyed);
  assert.ok(!internal.model(true));
});

test('remove storage object marks model as deleted', function(assert) {
  let adapter = this.database.get('adapter');
  let content = adapter.get('content');
  let identity = this.database.get('identity');
  let deleted = this.identity.deleted;

  let model = this.database.model('duck');
  let internal = model._internal;
  let storage = model.get('storage');

  content.removeObject(storage);

  assert.ok(!model.isDestroyed);
  assert.equal(internal.state.isDeleted, true);
  assert.deepEqual(identity.map(m => m), []);
  assert.deepEqual(deleted.map(m => m), [ internal ]);

  content.addObject(storage);

  assert.equal(internal.state.isDeleted, false);
  assert.deepEqual(identity.map(m => m), [ model ]);
  assert.deepEqual(deleted.map(m => m), []);
});

test('compact database destroys internal models and models', function(assert) {
  let adapter = this.database.get('adapter');
  let content = adapter.get('content');
  let deleted = this.identity.deleted;

  let model = this.database.model('duck');
  let internal = model._internal;
  let storage = model.get('storage');

  content.removeObject(storage);

  assert.equal(internal.isDestroyed, false);
  assert.equal(model.isDestroyed, false);
  assert.deepEqual(deleted.map(m => m), [ internal ]);

  run(() => this.stores.compact());

  assert.equal(internal.isDestroyed, true);
  assert.equal(model.isDestroyed, true);
  assert.deepEqual(deleted.map(m => m), []);
});

test('adapter chooses whether to destroy on compact', function(assert) {
  let adapter = this.database.get('adapter');
  let content = adapter.get('content');
  let deleted = this.identity.deleted;

  let model = this.database.model('duck');
  let internal = model._internal;
  let storage = model.get('storage');
  storage._destroysModel = false;

  content.removeObject(storage);

  assert.equal(internal.isDestroyed, false);
  assert.equal(model.isDestroyed, false);
  assert.deepEqual(deleted.map(m => m), [ internal ]);

  run(() => this.stores.compact());

  assert.equal(internal.isDestroyed, false);
  assert.equal(model.isDestroyed, false);
  assert.deepEqual(deleted.map(m => m), [ internal ]);
});
