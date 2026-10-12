import module from '../helpers/module-for-stores';
import { test } from '../helpers/qunit';
import { run } from '@ember/runloop';

module('store-database');

test('create database with identifier', function(assert) {
  let db = this.store.database('main');
  assert.ok(db);
  assert.ok(db.get('store') === this.store);
  assert.ok(db.get('identifier') === 'main');
});

test('databases are cached', function(assert) {
  let a1 = this.store.database('main');
  let a2 = this.store.database('main');
  let b1 = this.store.database('other');
  let b2 = this.store.database('other');

  assert.ok(a1);
  assert.ok(a2);
  assert.ok(b1);
  assert.ok(b2);

  assert.ok(a1 === a2);
  assert.ok(b1 === b2);

  assert.ok(a1 !== b1);
});

test('store destroy destroys cached databases', function(assert) {
  let db = this.store.database('main');
  run(() => this.store.destroy());
  assert.ok(this.store.isDestroyed);
  assert.ok(db.isDestroyed);
});

test('adapter is set', function(assert) {
  let db = this.store.database('main');
  assert.ok(db._context.adapter);
});

test('adapter has store and store adapter', function(assert) {
  let db = this.store.database('main');
  assert.ok(db._context.adapter.store === this.store);
  assert.ok(db._context.adapter.adapter === this.store._context.adapter);
});
