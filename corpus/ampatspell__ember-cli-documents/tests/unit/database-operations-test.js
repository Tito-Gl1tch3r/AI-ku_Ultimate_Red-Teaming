import { run } from '@ember/runloop';
import { Promise } from 'rsvp';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

module('database-operations', {
  async beforeEach() {
    await this.recreate();
  }
});

test('internal operation is registered in database', async function(assert) {
  let doc = this.db.doc({ id: 'one' });
  let promise = doc.save();

  assert.equal(this.db._operations.get('length'), 1);

  await promise;

  assert.equal(this.db._operations.get('length'), 0);
});

test('database operation is registered in database', async function(assert) {
  let promise = this.db.find({ all: true })

  assert.equal(this.db._operations.get('length'), 1);

  await promise;

  assert.equal(this.db._operations.get('length'), 0);
});

test('settle with next', async function(assert) {
  let one = this.db.doc({ id: 'one' });
  one.save();

  let promise = run(() => this.db.settle());

  let two = this.db.doc({ id: 'two' });

  two.save().then(() => two.delete());

  await promise;

  assert.equal(one.get('isNew'), false);
  assert.equal(two.get('isNew'), false);
  assert.equal(two.get('isDeleted'), true);
});

test('settle without ops', async function(assert) {
  let promise = run(() => this.db.settle());
  await promise;
  assert.ok(true);
});

test('register function as an operation', async function(assert) {
  let done = false;
  this.db.operation('random', {}, () => {
    return new Promise(resolve => {
      run.later(() => {
        done = true;
        resolve();
      }, 100);
    });
  });

  let promise = run(() => this.db.settle());

  assert.ok(!done);

  await promise;

  assert.ok(done);
});

test('cancel queued operations on willDestroy', async function(assert) {
  let invoked = false;
  let promise = this.db.operation('random', {}, () => {
    invoked = true;
  });

  assert.ok(this.db._operations.get('length') === 1);

  run(() => this.db.destroy());

  let settle = run(() => this.db.settle());

  await settle;

  assert.ok(!invoked);

  try {
    await promise;
    assert.ok(false, 'should throw');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "internal",
      "reason": "operation_destroyed"
    });
  }

  assert.ok(this.db._operations.get('length') === 0);
});
