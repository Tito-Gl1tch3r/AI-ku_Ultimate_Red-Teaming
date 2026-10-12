import { run } from '@ember/runloop';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

module('database-changes');

test('changes are registered', function(assert) {
  let changes = this.db.changes({ feed: this.config.feed });
  assert.ok(this.db.get('_changes').includes(changes._internal));
});

test('changes are destroyed with db', function(assert) {
  let changes = this.db.changes({ feed: this.config.feed });
  assert.ok(this.db.get('_changes').includes(changes._internal));

  run(() => this.db.destroy());

  assert.ok(!this.db.get('_changes').includes(changes._internal));
  assert.ok(!changes._internal._model);
});

test('database changes model has ref to database', function(assert) {
  let changes = this.db.changes();
  assert.ok(changes.get('database') === this.db);
});

test('changes has adapter', function(assert) {
  let changes = this.db.changes();
  assert.ok(changes.get('_adapter'));
  assert.ok(changes._internal._adapter);
});

test('adapter is destroyed with changes', function(assert) {
  let changes = this.db.changes({ feed: this.config.feed });
  let adapter = changes.get('_adapter');

  run(() => this.db.destroy());

  assert.ok(adapter.isDestroyed);
  assert.ok(!changes._internal._adapter);
});

test('changes has state', function(assert) {
  let changes = this.db.changes({ feed: this.config.feed });
  assert.deepEqual(changes.get('state'), {
    "error": null,
    "isError": false,
    "isStarted": false,
    "isSuspended": false
  });
});
