import module from '../helpers/module-for-stores';
import { test } from '../helpers/qunit';
import Stores from 'ember-cli-models/stores';
import StoreAdapter from 'ember-cli-models/adapter/store';
import DatabaseAdapter from 'ember-cli-models/adapter/database';

module('store-adapter', {
  beforeEach() {
    this.create = () => {
      const StoreAdapterImpl = StoreAdapter.extend();
      const DatabaseAdapterImpl = DatabaseAdapter.extend();
      const StoresImpl = Stores.extend({
        storeOptionsForIdentifier(identifier) {
          if(identifier === 'local') {
            return {
              adapter: 'local'
            }
          } else if(identifier === 'no-adapter') {
            return {};
          }
        }
      });
      this.register('models:stack/local/store/adapter', StoreAdapterImpl);
      this.register('models:stack/local/database/adapter', DatabaseAdapterImpl);
      this.register('models:stores', StoresImpl);
      return this.lookup('models:stores');
    };
  }
});

test('it exists', function(assert) {
  let stores = this.create();
  assert.ok(stores);
});

test('adapter is set', function(assert) {
  let stores = this.create();
  let store = stores.store('local');
  assert.ok(store._context.adapter);
  assert.ok(store._context.adapter.store === store);
});

test('adapter has identifier', function(assert) {
  let stores = this.create();
  let store = stores.store('local');
  assert.equal(store._context.adapter.identifier, 'local');
});

test('throws for missing opts', function(assert) {
  let stores = this.create();
  try {
    stores.store('something');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "options for 'something' store must be object"
    });
  }
});

test('throws for missing adapter', function(assert) {
  let stores = this.create();
  try {
    stores.store('no-adapter');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "store adapter for 'no-adapter' must be string"
    });
  }
});
