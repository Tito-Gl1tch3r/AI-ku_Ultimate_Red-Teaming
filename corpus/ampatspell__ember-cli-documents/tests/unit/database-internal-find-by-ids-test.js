import { all } from 'rsvp';
import configurations from '../helpers/configurations';
import { test } from '../helpers/qunit';

configurations(module => {

  module('database-internal-find-by-ids', {
    beforeEach() {
      return this.recreate();
    }
  });

  test('load by ids', async function(assert) {
    await all([
      this.docs.save({ _id: 'one' }),
      this.docs.save({ _id: 'two' })
    ]);

    let { type, result } = await this.db._internalDocumentFind({ ids: [ 'one', 'two' ] });
    assert.equal(type, 'array');
    assert.equal(result.length, 2);
    assert.deepEqual(result.map(internal => internal.getId()), [ 'one', 'two' ]);
  });

  test('load by ids with one already loaded', async function(assert) {
    this.db.existing('one', { create: true });

    await all([
      this.docs.save({ _id: 'one' }),
      this.docs.save({ _id: 'two' })
    ]);

    let { type, result } = await this.db._internalDocumentFind({ ids: [ 'one', 'two' ] });
    assert.equal(type, 'array');
    assert.equal(result.length, 2);
    assert.deepEqual(result.map(internal => internal.getId()), [ 'one', 'two' ]);
  });

  test('load by ids rejects if some of ids not found', async function(assert) {
    await this.docs.save({ _id: 'two' });

    try {
      await this.db._internalDocumentFind({ ids: [ 'one', 'two' ] });
    } catch(err) {
      assert.deepEqual(err.toJSON(), {
        "error": "not_found",
        "reason": "missing"
      });
      assert.deepEqual(err.missing, [ 'one' ]);
    }
  });

  test('load by ids rejects if existing was deleted', async function(assert) {
    let one = this.db.doc({ id: 'one' });
    await all([
      one.save(),
      this.docs.save({ _id: 'two' })
    ]);

    await one.delete();

    try {
      await this.db._internalDocumentFind({ ids: [ 'one', 'two' ] });
    } catch(err) {
      assert.deepEqual(err.toJSON(), {
        "error": "not_found",
        "reason": "missing"
      });
      assert.deepEqual(err.missing, [ 'one' ]);
    }
  });

  test('load by ids resolve if existing was deleted but has a rev in db', async function(assert) {
    let one = this.db.doc({ id: 'one' });

    await all([
      one.save(),
      this.docs.save({ _id: 'two' })
    ]);

    await one.delete();

    await this.docs.save({ _id: 'one', resurrected: true });

    let { result } = await this.db._internalDocumentFind({ ids: [ 'one', 'two' ], force: true });

    assert.deepEqual(result.map(internal => internal.getId()), [ 'one', 'two' ]);
    assert.equal(this.db.existing('one').get('resurrected'), true);
  });

});
