import configurations from '../helpers/configurations';
import { test } from '../helpers/qunit';
import { next } from '../helpers/run';

configurations(module => {

  module('document-delete', {
    beforeEach() {
      return this.recreate();
    }
  });

  test('delete succeeds', async function(assert) {
    let doc = this.db.doc({ id: 'duck:yellow', type: 'duck', name: 'Yellow' });

    await doc.save();

    assert.ok(this.db._documents.saved['duck:yellow']);

    assert.deepEqual(doc.get('state'), {
      "error": null,
      "isDeleted": false,
      "isDirty": false,
      "isError": false,
      "isLoaded": true,
      "isLoading": false,
      "isNew": false,
      "isSaving": false
    });

    let promise = doc.delete();

    await next();

    assert.deepEqual(doc.get('state'), {
      "error": null,
      "isDeleted": false,
      "isDirty": false,
      "isError": false,
      "isLoaded": true,
      "isLoading": false,
      "isNew": false,
      "isSaving": true
    });

    await promise;

    assert.deepEqual(doc.get('state'), {
      "error": null,
      "isDeleted": true,
      "isDirty": false,
      "isError": false,
      "isLoaded": true,
      "isLoading": false,
      "isNew": false,
      "isSaving": false
    });

    assert.deepEqual_(doc.get('serialized'), {
      "id": "duck:yellow",
      "name": "Yellow",
      "rev": "ignored",
      "type": "duck"
    });

    assert.ok(this.db._documents.deleted['duck:yellow']);
    assert.ok(!this.db._documents.saved['duck:yellow']);
  });

  test('reject already deleted', async function(assert) {
    let doc = this.db.doc({ id: 'thing' });

    await doc.save();
    await doc.delete();

    try {
      await doc.delete();
      assert.ok(false, 'should throw');
    } catch(e) {
      assert.deepEqual(e.toJSON(), {
        "error": "deleted",
        "reason": "Document is already deleted"
      });
    }
  });

  test('reject isNew', async function(assert) {
    let doc = this.db.doc({ id: 'thing' });
    try {
      await doc.delete();
      assert.ok(false, 'should throw');
    } catch(e) {
      assert.deepEqual(e.toJSON(), {
        "error": "not_saved",
        "reason": "Document is not yet saved"
      });
    }
  });

  test('delete missing is marked as deleted', async function(assert) {
    let doc = this.db.doc({ id: 'thing' });
    await doc.save();
    await this.docs.delete('thing', doc.get('rev'));
    try {
      await doc.delete();
      assert.ok(false, 'should throw');
    } catch(e) {
      assert.deepEqual(e.toJSON(), {
        "error": "not_found",
        "reason": "deleted",
        "status": 404
      });
      assert.ok(doc.get('isDeleted'));
      assert.ok(this.db._documents.deleted.thing);
    }
  });

});
