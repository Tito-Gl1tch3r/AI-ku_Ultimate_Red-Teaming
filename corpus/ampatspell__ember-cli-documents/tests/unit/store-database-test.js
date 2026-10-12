import { run } from '@ember/runloop';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

module('store-database');

test('create database', function(assert) {
  let db = this.store.database('foof');
  assert.ok(db);
  assert.equal(db.get('identifier'), 'foof');
});

test('create database always returns the same db for identifier', function(assert) {
  let one = this.store.database('foofBar');
  let two = this.store.database('foofBar');
  let three = this.store.database(' foofBar ');
  assert.ok(one === two);
  assert.ok(two === three);
});

test('id.identifier', function(assert) {
  let one = this.store.database('foofBar');
  let two = this.store.get('id.foofBar');
  assert.ok(one === two);
});

test('create database returns another db for another identifier', function(assert) {
  let one = this.store.database('duck');
  let two = this.store.database('hamster');
  assert.ok(one !== two);
});

test('database is added to open databases', function(assert) {
  let dbs = this.store._databases;
  assert.ok(!dbs.duck);
  let db = this.store.database('duck');
  assert.ok(dbs.keyed.duck === db);
  assert.ok(dbs.all.includes(db));
});

test('database on destroy is removed from open databases', function(assert) {
  let dbs = this.store._databases;
  let db = this.store.database('duck');
  assert.ok(dbs.keyed.duck);
  assert.ok(dbs.all.includes(db));
  run(() => db.destroy());
  assert.ok(!dbs.keyed.duck);
  assert.ok(!dbs.all.includes(db));
});

test('dataabse identifier must be string', function(assert) {
  try {
    this.store.database({});
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "identifier must be string"
    });
  }
});
