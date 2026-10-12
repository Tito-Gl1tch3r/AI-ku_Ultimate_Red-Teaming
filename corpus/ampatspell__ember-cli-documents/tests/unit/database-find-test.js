import { all } from 'rsvp';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

module('database-find', {
  beforeEach() {
    return this.recreate();
  }
});

test('find by id', async function(assert) {
  await this.docs.save({ _id: 'hello' });
  let doc = await this.db.find('hello');
  assert.ok(doc);
  assert.equal(doc.get('id'), 'hello');
});

test('find by id missing', async function(assert) {
  try {
    await this.db.find('hello');
    assert.ok(false, 'should throw');
  } catch(e) {
    assert.deepEqual(e.toJSON(), {
      "error": "not_found",
      "reason": e.reason,
      "status": 404
    });
  }
});

test('find all empty', async function(assert) {
  let docs = await this.db.find({ all: true });
  assert.equal(docs.length, 0);
});

test('find all with docs', async function(assert) {
  await all([
    this.docs.save({ _id: 'one' }),
    this.docs.save({ _id: 'two' })
  ]);
  let docs = await this.db.find({ all: true });
  assert.deepEqual(docs.mapBy('id'), [ 'one', 'two' ]);
});

test('first with multiple docs', async function(assert) {
  await all([
    this.docs.save({ _id: 'one' }),
    this.docs.save({ _id: 'two' })
  ]);
  let doc = await this.db.first({ all: true });
  assert.equal(doc.get('id'), 'one');
});

test('first by id', async function(assert) {
  await this.docs.save({ _id: 'one' })
  let doc = await this.db.first('one');
  assert.equal(doc.get('id'), 'one');
});

test('first by id missing', async function(assert) {
  try {
    await this.db.first('one');
    assert.ok(false, 'should throw');
  } catch(e) {
    assert.deepEqual(e.toJSON(), {
      "error": "not_found",
      "reason": e.reason,
      "status": 404
    });
  }
});

test('first all missing', async function(assert) {
  try {
    await this.db.first({ all: true });
    assert.ok(false, 'should throw');
  } catch(e) {
    assert.deepEqual(e.toJSON(), {
      "error": "not_found",
      "reason": e.reason,
      "status": 404
    });
  }
});

test('first with match rejects', async function(assert) {
  await this.docs.save({ _id: 'foo' });
  let doc;
  try {
    await this.db.first({
      all: true,
      match(doc_) {
        doc = doc_;
        return false;
      }
    });
    assert.ok(false, 'should throw');
  } catch(e) {
    assert.ok(doc);
    assert.deepEqual(e.toJSON(), {
      "error": "not_found",
      "reason": e.reason,
      "status": 404
    });
  }
});

test('first with match resolves', async function(assert) {
  await this.docs.save({ _id: 'thing' });
  let doc;
  let result = await this.db.first({
    all: true,
    match(doc_) {
      doc = doc_;
      return true;
    }
  });
  assert.equal(result.get('id'), 'thing');
  assert.ok(result === doc);
});

test('find by ids with all found', async function(assert) {
  await all([
    this.docs.save({ _id: 'one' }),
    this.docs.save({ _id: 'two' })
  ]);

  let result = await this.db.find({ ids: [ 'one', 'two' ] });
  assert.deepEqual(result.mapBy('id'), [ 'one', 'two' ]);
});
