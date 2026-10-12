import configurations from '../helpers/configurations';
import { test } from '../helpers/qunit';

configurations(module => {

  module('database-internal-find-by-id', {
    beforeEach() {
      return this.recreate();
    }
  });

  test('load by id as a string', async function(assert) {
    let saved = await this.docs.save({ _id: 'duck:yellow' });
    let { type, result } = await this.db._internalDocumentFind('duck:yellow');
    assert.equal(type, 'single');
    assert.equal(result.getRev(), saved.rev);
    assert.ok(this.db._documents.saved['duck:yellow']);
    assert.deepEqual_(result.state, {
      "error": null,
      "isDeleted": false,
      "isDirty": false,
      "isError": false,
      "isLoaded": true,
      "isLoading": false,
      "isNew": false,
      "isSaving": false
    });
  });

  test('load by id prop', async function(assert) {
    await this.docs.save({ _id: 'duck:yellow' });
    let { type, result } = await this.db._internalDocumentFind({ id: 'duck:yellow' });
    assert.equal(type, 'single');
    assert.equal(result.getId(), 'duck:yellow');
  });

  test('load by id existing', async function(assert) {
    await this.docs.save({ _id: 'duck:yellow' });
    let doc = this.db.existing('duck:yellow', { create: true });
    let { result } = await this.db._internalDocumentFind('duck:yellow');
    assert.ok(doc._internal === result);
  });

  test('load missing', async function(assert) {
    try {
      await this.db._internalDocumentFind('duck:yellow');
      assert.ok(false);
    } catch(e) {
      assert.deepEqual(e.toJSON(), {
        "error": "not_found",
        "reason": e.reason,
        "status": 404
      });
    }
  });

  test('load first', async function(assert) {
    await this.docs.save({ _id: 'duck:yellow' });
    let doc = this.db.existing('duck:yellow', { create: true });
    let internal = await this.db._internalDocumentFirst('duck:yellow');
    assert.ok(doc._internal === internal);
  });

  test('load first missing', async function(assert) {
    try {
      await this.db._internalDocumentFirst('duck:yellow');
      assert.ok(false);
    } catch(e) {
      assert.deepEqual(e.toJSON(), {
        "error": "not_found",
        "reason": e.reason,
        "status": 404
      });
    }
  });

});
