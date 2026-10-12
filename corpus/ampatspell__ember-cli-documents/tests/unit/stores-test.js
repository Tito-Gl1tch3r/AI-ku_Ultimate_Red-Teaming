import { run } from '@ember/runloop';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import { Stores, Model } from 'documents';

module('stores');

test('stores.storeOptionsForIdentifier throws', function(assert) {
  let stores = Stores.create();
  try {
    stores.storeOptionsForIdentifier();
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "override store.storeOptionsForIdentifier"
    });
  }
});

test('stores exist', function(assert) {
  assert.ok(this.stores);
});

test('store is created only once', function(assert) {
  let one = this.stores.store('default');
  let two = this.stores.store('default');
  assert.ok(one === two);
});

test('stores.id.identifier', function(assert) {
  let id = this.stores.get('id.default');
  let normal = this.stores.store('default');
  assert.ok(id === normal);
});

test('stores destory destroys stores', function(assert) {
  let store = this.stores.store('default');
  run(() => this.stores.destroy());
  assert.ok(store.isDestroyed);
});

test('store destroy removes store from stores', function(assert) {
  let store = this.stores.store('default');
  let identifier = store.get('identifier');
  assert.equal(identifier, 'default');
  assert.ok(this.stores._stores.keyed[identifier]);
  run(() => store.destroy());
  assert.ok(!this.stores._stores.keyed[identifier]);
});

test('stores destory destroys documents identity', function(assert) {
  let identity = this.stores.get('documentsIdentity');
  run(() => this.stores.destroy());
  assert.ok(identity.isDestroyed);
});

test('stores destory destroys models identity', function(assert) {
  let Thing = Model.extend();
  this.register('model:thing', Thing);
  let model = this.stores.model('thing');
  let identity = this.stores.get('modelsIdentity');
  assert.equal(identity.modelsByClass(Thing).get('length'), 1);
  run(() => this.stores.destroy());
  assert.ok(identity.isDestroyed);
  assert.ok(model.isDestroyed);
});

test('stores throws if no options are returned', function(assert) {
  try {
    this.stores.store('noop');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "storeOptionsForIdentifier result must be object"
    });
  }
});
