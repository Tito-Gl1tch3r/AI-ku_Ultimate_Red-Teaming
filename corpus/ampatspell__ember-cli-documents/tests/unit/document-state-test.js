import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

module('document-state');

test('new document has state', function(assert) {
  let doc = this.db.doc();
  assert.deepEqual(doc.get('state'), {
    "error": null,
    "isDeleted": false,
    "isDirty": false,
    "isError": false,
    "isLoaded": false,
    "isLoading": false,
    "isNew": true,
    "isSaving": false
  });
});

test('document has separate state properties', function(assert) {
  let doc = this.db.doc();
  assert.equal(doc.get('isNew'), true);
});

test('document state properties are aliases for internal state', function(assert) {
  let doc = this.db.doc();
  doc._internal.state.isNew = 'hello';
  assert.equal(doc.get('isNew'), 'hello');
});

test('document state properties are notified for changes', function(assert) {
  let doc = this.db.doc();

  assert.equal(doc.get('isNew'), true);
  assert.equal(doc.get('state').isNew, true);

  doc._internal.withPropertyChanges(changed => doc._internal.state.set({ isNew: false }, changed), true);

  assert.equal(doc.get('isNew'), false);
  assert.equal(doc.get('state').isNew, false);
});
