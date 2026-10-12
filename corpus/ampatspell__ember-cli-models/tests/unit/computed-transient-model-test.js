import { assign } from '@ember/polyfills';
import { run } from '@ember/runloop';
import module from '../helpers/module-for-stores';
import { test } from '../helpers/qunit';
import Model from 'ember-cli-models/model/transient';
import { database, model } from 'ember-cli-models/computed';

module('computed-transient-model', {
  beforeEach() {
    this.register('model:changeset', Model.extend({ id: 'changeset' }));
    this.subject = opts => {
      opts = assign({ database: 'database', name: 'changeset' }, opts);
      this.register('model:duck', Model.extend({
        id: 'duck',
        database: database(),
        changeset: model(opts.database, function() {
          if(opts.noop) {
            return;
          }
          return {
            database: this.get(opts.database),
            name: opts.name,
            props: {
              duck: this
            }
          };
        })
      }));
      return this.database.model('duck');
    };
  }
});

test('duck exists', function(assert) {
  let duck = this.subject();
  assert.ok(duck);
});

test('duck has changeset', function(assert) {
  let duck = this.subject();
  let changeset = duck.get('changeset');
  assert.ok(changeset);
  assert.ok(changeset.get('duck') === duck);
});

test('changeset is destroyed with duck', function(assert) {
  let duck = this.subject();
  let changeset = duck.get('changeset');

  run(() => duck.destroy());

  assert.ok(changeset.isDestroyed);
});

test('destroyed changeset is not recreated', function(assert) {
  let duck = this.subject();
  let changeset = duck.get('changeset');
  let internal = changeset._internal;

  run(() => changeset.destroy());

  assert.ok(changeset.isDestroyed);
  assert.ok(internal.isDestroyed);
  assert.ok(!changeset._internal);

  let next = duck.get('changeset');
  assert.ok(next === changeset);
});

test('no database throws', function(assert) {
  let duck = this.subject({ database: 'missing' });
  try {
    duck.get('changeset');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "result.database must be database"
    });
  }
});

test('no result does not throw', function(assert) {
  let duck = this.subject({ noop: true });
  let changeset = duck.get('changeset');
  assert.ok(changeset === undefined);
});

test('missing name throws', function(assert) {
  let duck = this.subject({ name: null });
  try {
    duck.get('changeset');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "result.name must be string"
    });
  }
});

test('destroy duck removes duck and changeset from identity', function(assert) {
  let identity = this.database.get('identity');

  let duck = this.subject();
  let changeset = duck.get('changeset');

  assert.deepEqual(identity.mapBy('id'), [ 'duck', 'changeset' ]);

  run(() => duck.destroy());

  assert.ok(duck.isDestroyed);
  assert.ok(changeset.isDestroyed);

  assert.deepEqual(identity.mapBy('id'), []);
});

test('changeset is recreated on database change', function(assert) {
  let duck = this.subject();

  let firstChangeset = duck.get('changeset');
  let firstInternal = firstChangeset._internal;
  assert.ok(firstChangeset);
  assert.ok(firstInternal);

  duck.set('database', this.store.database('another'));

  let secondChangeset = run(() => duck.get('changeset'));
  let secondInternal = secondChangeset._internal;
  assert.ok(secondChangeset);
  assert.ok(secondInternal);

  assert.ok(secondChangeset !== firstChangeset);
  assert.ok(secondInternal !== firstInternal);

  assert.ok(firstChangeset.isDestroyed);
  assert.ok(firstInternal.isDestroyed);
});
