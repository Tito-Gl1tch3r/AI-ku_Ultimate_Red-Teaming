import configurations from '../helpers/configurations';
import { test } from '../helpers/qunit';
import { next } from '../helpers/run';

configurations(module => {

  module('document-load', {
    beforeEach() {
      return this.recreate();
    }
  });

  test('load succeeds', async function(assert) {
    let json = await this.docs.save({ _id: 'thing', name: 'hello' });
    let doc = this.db.existing('thing', { create: true });

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

    let promise = doc.load();

    await next();

    assert.deepEqual(doc.get('state'), {
      "error": null,
      "isDeleted": false,
      "isDirty": false,
      "isError": false,
      "isLoaded": false,
      "isLoading": true,
      "isNew": false,
      "isSaving": false
    });

    let ret = await promise;
    assert.ok(ret === doc);

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

    assert.deepEqual(doc.get('serialized'), {
      "id": "thing",
      "rev": json.rev,
      "name": "hello"
    });
  });

  test('load isNew resolves', async function(assert) {
    let doc = this.db.doc();

    let res = await doc.load();
    assert.ok(res === doc);

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

  test('load missing is marked as deleted', async function(assert) {
    let doc = this.db.existing('thing', { create: true });
    try {
      await doc.load();
    } catch(e) {
      assert.deepEqual(e.toJSON(), {
        "error": "not_found",
        "reason": e.reason,
        "status": 404
      });
      assert.ok(this.db._documents.deleted.thing);
    }
  });

  test('reload resolves for isNew', async function(assert) {
    let doc = this.db.doc();
    let r = await doc.reload();
    assert.ok(r === doc);
  });

  test('load loaded resolves', async function(assert) {
    await this.docs.save({ _id: 'thing' });
    let doc = this.db.existing('thing', { create: true });

    await doc.load();
    assert.ok(doc.get('rev'));
    doc._internal.values._rev = null;

    await doc.load();
    assert.equal(doc._internal.values._rev, null);
  });

  test('load loaded with force loads', async function(assert) {
    await this.docs.save({ _id: 'thing' });
    let doc = this.db.existing('thing', { create: true });

    await doc.load();
    let rev = doc.get('rev');
    doc._internal.values.rev = null;

    await doc.load({ force: true });
    assert.equal(doc._internal.values.rev, rev);
  });

});
