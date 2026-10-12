/* global emit */
import { all } from 'rsvp';

import configurations from '../helpers/configurations';
import { test } from '../helpers/qunit';

const main = {
  views: {
    'by-type': {
      map(doc) {
        emit(doc.type);
      }
    }
  }
};

configurations(module => {

  module('database-internal-find-view', {
    beforeEach() {
      return this.recreate().then(() => this.db.get('documents.design').save('main', main));
    }
  });

  test('find view returns empty array', async function(assert) {
    let { type, result } = await this.db._internalDocumentFind({ ddoc: 'main', view: 'by-type' });
    assert.equal(type, 'array');
    assert.equal(result.length, 0);
  });

  test('find view returns documents', async function(assert) {
    await all([
      this.docs.save({ _id: 'one', type: 'foo' }),
      this.docs.save({ _id: 'two', type: 'bar' }),
      this.docs.save({ _id: 'three', type: 'foo' })
    ]);

    let { type, result } = await this.db._internalDocumentFind({ ddoc: 'main', view: 'by-type', key: 'foo' });
    assert.equal(type, 'array');
    assert.equal(result.length, 2);
    assert.deepEqual(result.map(internal => internal.getId()), [ 'one', 'three' ]);
  });

  test('load first with existing docs', async function(assert) {
    await all([
      this.docs.save({ _id: 'one', type: 'foo' }),
      this.docs.save({ _id: 'two', type: 'bar' }),
      this.docs.save({ _id: 'three', type: 'foo' })
    ]);

    let internal = await this.db._internalDocumentFirst({ ddoc: 'main', view: 'by-type', key: 'foo' });
    assert.equal(internal.getId(), 'one');
  });

  test('load first with no docs', async function(assert) {
    try {
      await this.db._internalDocumentFirst({ ddoc: 'main', view: 'by-type', key: 'foo' });
      assert.ok(false);
    } catch(e) {
      assert.deepEqual(e.toJSON(), {
        "error": "not_found",
        "reason": "missing",
        "status": 404
      });
    }
  });

});
