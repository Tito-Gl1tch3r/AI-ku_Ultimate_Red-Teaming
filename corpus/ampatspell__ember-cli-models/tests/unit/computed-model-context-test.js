import { run } from '@ember/runloop';
import module from '../helpers/module-for-stores';
import { test } from '../helpers/qunit';
import Model from 'ember-cli-models/model/backed';
import { stores, store, database } from 'ember-cli-models/computed';

module('computed-model-context', {
  beforeEach() {
    this.subject = (opts={}) => {
      let props = {
        stores: stores(),
        store: opts.store ? store(opts.store) : store(),
        database: opts.database ? database(opts.database) : database()
      };
      this.register('model:duck', Model.extend(props));
      return this.database.model('duck');
    };
  }
});

test('lookup works', function(assert) {
  let duck = this.subject();
  assert.ok(duck.get('stores') === this.stores);
  assert.ok(duck.get('store') === this.store);
  assert.ok(duck.get('database') === this.database);
});

test('lookup another database', function(assert) {
  let duck = this.subject({ database: 'another' });
  assert.ok(duck.get('database') === this.store.database('another'));
});

test('lookup another store', function(assert) {
  let duck = this.subject({ store: 'remote' });
  assert.ok(duck.get('store') === this.stores.store('remote'));
});

test('lookup after model destroy', function(assert) {
  let duck = this.subject();
  run(() => duck.destroy());
  assert.ok(duck.get('stores') === undefined);
  assert.ok(duck.get('store') === undefined);
  assert.ok(duck.get('database') === undefined);
});
