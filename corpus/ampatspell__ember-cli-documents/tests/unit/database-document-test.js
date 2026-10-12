import { run } from '@ember/runloop';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

module('database-document');

test('doc creates a new document which is added to identity.new', function(assert) {
  let doc = this.db.doc();
  assert.ok(doc);
  assert.equal(doc.get('isNew'), true);
  let internal = doc._internal;
  let identity = this.db._documents;
  assert.ok(identity.all.includes(internal));
  assert.ok(identity.new.includes(internal));
});

test('destroyed new document is removed from identity', function(assert) {
  let doc = this.db.doc();
  let internal = doc._internal;

  run(() => doc.destroy());

  let identity = this.db._documents;
  assert.ok(!identity.all.includes(internal));
  assert.ok(!identity.new.includes(internal));
});

test('destroyed existing document is not removed from identity', function(assert) {
  let doc = this.db.push({ _id: 'duck' });
  let internal = doc._internal;

  run(() => doc.destroy());

  let identity = this.db._documents;
  assert.ok(identity.all.includes(internal));
  assert.ok(identity.saved.duck);

  assert.ok(doc.isDestroyed);
  assert.ok(!internal.model());

  let model = this.db.existing('duck');
  assert.ok(model);
  assert.ok(model !== doc);
});

test('existing document by default returns undefined', function(assert) {
  let doc = this.db.existing('foo');
  let documents = this.db._documents;
  assert.ok(!doc);
  assert.ok(documents.all.length === 0);
});

test('created existing document has state', function(assert) {
  let doc = this.db.existing('foo', { create: true });
  assert.deepEqual(doc.get('state'), {
    "error": null,
    "isDeleted": false,
    "isDirty": false,
    "isError": false,
    "isLoaded": false,
    "isLoading": false,
    "isNew": false,
    "isSaving": false
  });
});
