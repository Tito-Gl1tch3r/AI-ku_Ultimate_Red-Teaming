import EmberObject from '@ember/object';
import { run } from '@ember/runloop';
import { all } from 'rsvp';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

module('query-loader', {
  async beforeEach() {
    this.owner = EmberObject.create({ id: null });
    this.opts = {
      owner: [ 'id' ],
      query(owner) {
        let id = owner.get('id');
        if(!id) {
          return;
        }
        return { id };
      }
    };
    this.parent = {
      withPropertyChanges() {}
    };
    this.first = () => this.db._createInternalQueryLoader(this.parent, this.owner, this.opts, 'first').model(true);
    this.settle = loader => loader._internal.settle();
  }
});

test('it exists', function(assert) {
  this.opts.autoload = false;

  let loader = this.first();
  assert.ok(loader);
  run(() => loader.destroy());
});

test('loader has query', function(assert) {
  this.opts.autoload = false;

  this.owner.set('id', 'duck');
  let loader = this.first();
  assert.deepEqual(loader._internal._query(true), {
    query: {
      id: 'duck'
    }
  });
  run(() => loader.destroy());
});

test('load succeeds', async function(assert) {
  await this.recreate();

  this.opts.autoload = false;

  await this.docs.save({ _id: 'duck' });
  this.owner.set('id', 'duck');

  let loader = this.first();
  assert.ok(!loader.get('isLoading'));

  let promise = loader.load();
  assert.ok(loader.get('isLoading'));

  let result = await promise;
  assert.ok(result === loader);
  assert.ok(this.db.existing('duck'));

  run(() => loader.destroy());
});

test('load fails', async function(assert) {
  await this.recreate();

  this.opts.autoload = false;

  this.owner.set('id', 'duck');
  let loader = this.first();

  try {
    await loader.load();
  } catch(err) {
    assert.equal(err.error, 'not_found');
  }

  assert.equal(loader._internal.state.error.error, 'not_found');

  run(() => loader.destroy());
});

test('two loads. second returns 1st promise', async function(assert) {
  await this.recreate();

  this.opts.autoload = false;

  await this.docs.save({ _id: 'duck' });
  this.owner.set('id', 'duck');

  let loader = this.first();

  let one = loader._internal.reload();
  let two = loader._internal.reload();

  await all([ one, two ]);

  assert.ok(this.db.existing('duck'));
  assert.ok(one === two);

  run(() => loader.destroy());
});

test('destroy while loading', async function(assert) {
  await this.recreate();

  this.opts.autoload = false;
  await this.docs.save({ _id: 'duck' });
  this.owner.set('id', 'duck');

  let loader = this.first();
  let promise = loader._internal.reload();

  run(() => loader.destroy());

  await promise;

  assert.ok(loader._internal.state.isLoaded);
});

test('autoload for isLoading, isLoaded', async function(assert) {
  await this.recreate();

  await this.docs.save({ _id: 'duck' });
  this.owner.set('id', 'duck');
  let loader = this.first();

  assert.equal(loader._internal.state.isLoading, false);
  assert.equal(loader.get('isLoading'), true);
  assert.equal(loader._internal.state.isLoading, true);
  assert.equal(loader._internal.operations.get('length'), 1);

  assert.equal(loader.get('isLoading'), true);
  assert.equal(loader.get('isLoaded'), false);
  assert.equal(loader._internal.operations.get('length'), 1);

  await this.settle(loader);
});

test('autoload and force load', async function(assert) {
  await this.recreate();

  await this.docs.save({ _id: 'duck' });
  this.owner.set('id', 'duck');
  let loader = this.first();

  assert.equal(loader._internal.state.isLoading, false);
  assert.equal(loader.get('isLoading'), true);
  assert.equal(loader._internal.state.isLoading, true);
  assert.equal(loader._internal.operations.get('length'), 1);

  loader.reload();
  assert.equal(loader._internal.operations.get('length'), 1);

  await this.settle(loader);
});

test('load and force load', async function(assert) {
  await this.recreate();

  await this.docs.save({ _id: 'duck' });
  this.owner.set('id', 'duck');
  let loader = this.first();

  loader.load();
  assert.equal(loader._internal.operations.get('length'), 1);

  loader.reload();
  assert.equal(loader._internal.operations.get('length'), 1);

  loader.reload();
  assert.equal(loader._internal.operations.get('length'), 1);

  await this.settle(loader);
});

test('load on owner property change', async function(assert) {
  await this.recreate();

  await this.docs.save({ _id: 'duck' });
  let loader = this.first();

  assert.equal(loader._internal.operations.get('length'), 0);

  this.owner.set('id', 'du');
  assert.equal(loader._internal.operations.get('length'), 0);
  assert.equal(loader.get('isLoading'), true);
  assert.equal(loader._internal.operations.get('length'), 1);

  this.owner.set('id', 'duc');
  assert.equal(loader._internal.operations.get('length'), 1);
  assert.equal(loader.get('isLoading'), true);
  assert.equal(loader._internal.operations.get('length'), 2);

  this.owner.set('id', 'duck');
  assert.equal(loader._internal.operations.get('length'), 2);
  assert.equal(loader.get('isLoading'), true);
  assert.equal(loader._internal.operations.get('length'), 3);

  await this.settle(loader);

  assert.ok(this.db.existing('duck'));
});

test('loadable is false', async function(assert) {
  let loader = this.first();
  assert.equal(loader.get('isLoadable'), false);
  await this.settle(loader);
});

test('loadable updates on owner prop change', async function(assert) {
  let loader = this.first();

  assert.equal(loader.get('isLoadable'), false);
  this.owner.set('id', 'foo');
  assert.equal(loader.get('isLoadable'), true);

  await this.settle(loader);
});

test('loadable is set to false on owner prop change', async function(assert) {
  this.owner.set('id', 'duck');
  let loader = this.first();

  assert.equal(loader.get('isLoadable'), true);
  this.owner.set('id', null);
  assert.equal(loader.get('isLoadable'), false);

  await this.settle(loader);
});

test('not loadable load rejects', async function(assert) {
  let loader = this.first();
  try {
    await loader.load();
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "loader",
      "reason": "not_loadable"
    });
  }

  await this.settle(loader);
});

test('reload reject if not loadable', async function(assert) {
  let loader = this.first();
  try {
    await loader.reload();
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "loader",
      "reason": "not_loadable"
    });
  }

  await this.settle(loader);
});

test('isLoadable does not start loading', async function(assert) {
  this.owner.set('id', 'duck');
  let loader = this.first();

  assert.equal(loader.get('isLoadable'), true);
  assert.equal(loader._internal.operations.get('length'), 0);

  await this.settle(loader);
});

test('state.isLoadable is false', async function(assert) {
  let loader = this.first();

  assert.deepEqual(loader.get('state'), {
    "error": null,
    "isError": false,
    "isLoadable": false,
    "isLoaded": false,
    "isLoading": false
  });

  assert.equal(loader.get('isLoadable'), false);
  assert.equal(loader.get('isLoaded'), false);

  await this.settle(loader);
});

test('state.isLoadable is true', async function(assert) {
  this.owner.set('id', 'hello');
  let loader = this.first();

  assert.deepEqual(loader.get('state'), {
    "error": null,
    "isError": false,
    "isLoadable": true,
    "isLoaded": false,
    "isLoading": false
  });

  await this.settle(loader);
});

test('state.isLoadable becomes true, load starts on state query', async function(assert) {
  await this.recreate();
  await all([
    this.docs.save({ _id: 'hello' }),
    this.docs.save({ _id: 'another' })
  ]);

  let loader = this.first();

  assert.deepEqual(loader.get('state'), {
    "error": null,
    "isError": false,
    "isLoadable": false,
    "isLoaded": false,
    "isLoading": false
  });

  assert.equal(loader.get('isLoading'), false);
  assert.equal(loader.get('isLoadable'), false);

  this.owner.set('id', 'hello');

  assert.deepEqual(loader.get('state'), {
    "error": null,
    "isError": false,
    "isLoadable": true,
    "isLoaded": false,
    "isLoading": false
  });

  assert.equal(loader._internal.operations.get('length'), 0);

  assert.equal(loader.get('isLoadable'), true);
  assert.equal(loader.get('isLoading'), true);

  assert.equal(loader._internal.operations.get('length'), 1);

  await this.settle(loader);

  assert.ok(this.db.existing('hello'));

  this.owner.set('id', null);

  assert.equal(loader.get('isLoadable'), false);
  assert.equal(loader.get('isLoading'), false);

  this.owner.set('id', 'second');

  assert.equal(loader.get('isLoadable'), true, 'isLoadable');
  assert.equal(loader.get('isLoading'), true, 'isLoading');

  assert.equal(loader._internal.operations.get('length'), 1, 'load operation scheduled');

  await this.settle(loader);

  assert.ok(this.db.existing('hello'));
});
