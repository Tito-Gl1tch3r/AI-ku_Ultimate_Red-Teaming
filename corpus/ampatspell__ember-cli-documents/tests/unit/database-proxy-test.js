import EmberObject from '@ember/object';
import { run } from '@ember/runloop';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

module('database-proxy', {
  beforeEach() {
    this.owner = EmberObject.create();
  }
});

test('create document proxy without owner and opts', async function(assert) {
  try {
    this.db.proxy('first', null, null);
    assert.ok(false);
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "query must be function"
    });
  }
});

test('create document proxy without owner', async function(assert) {
  await this.recreate();
  await this.docs.save({ _id: 'hello' });

  let proxy = this.db.proxy('first', null, {
    document: [ 'id' ],
    query() {
      return { id: 'hello' };
    },
    matches(doc) {
      return doc.get('id') === 'hello';
    }
  });

  let result = await proxy.load();
  assert.ok(result === proxy);

  assert.equal(proxy.get('id'), 'hello');

  run(() => proxy.destroy());
});

test('create paginated proxy without loaded', function(assert) {
  try {
    this.db.proxy('paginated', null, {
      document: [ 'id' ],
      query() {
        return { id: 'hello' };
      },
      matches(doc) {
        return doc.get('id') === 'hello';
      }
    });
    assert.ok(false, 'should throw');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "loaded must be function"
    });
  }
});
