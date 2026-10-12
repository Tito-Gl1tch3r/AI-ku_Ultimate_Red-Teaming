import { run } from '@ember/runloop';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

module('database-identity');

test('it exists', function(assert) {
  let identity = this.db.get('documentsIdentity');
  assert.ok(identity);
  assert.ok(identity.get('length') === 0);
});

test('identity includes new docs', function(assert) {
  let identity = this.db.get('documentsIdentity');
  assert.ok(identity.get('length') === 0);
  let doc = this.db.doc();
  assert.ok(identity.get('length') === 1);
  assert.ok(identity.get('lastObject') === doc);
});

test('docs are removed from identity', function(assert) {
  let identity = this.db.get('documentsIdentity');
  assert.ok(identity.get('length') === 0);

  let doc = this.db.doc();
  assert.ok(identity.get('lastObject') === doc);

  run(() => doc.destroy());

  assert.ok(identity.get('length') === 0);
});

test('identity is immutable', function(assert) {
  let identity = this.db.get('documentsIdentity');

  try {
    identity.pushObject('foo');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "internal",
      "reason": "immutable array"
    });
  }

  let doc = this.db.doc();

  try {
    identity.removeObject(doc);
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "internal",
      "reason": "immutable array"
    });
  }
});
