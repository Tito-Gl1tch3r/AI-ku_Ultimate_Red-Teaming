import EmberObject from '@ember/object';
import { A } from '@ember/array';
import { run } from '@ember/runloop';
import { all } from 'rsvp';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import { getDefinition, prop } from 'documents/properties';
import { pick } from 'documents/util/object';
import { findByIds } from '../helpers/properties';

module('property-by-ids', {
  beforeEach() {
    this.settle = proxy => proxy._internal.loader(true).settle();
  }
});

test('build', function(assert) {
  let Owner = EmberObject.extend({
    duckIds: [ 'yellow' ],
    doc: findByIds({ database: 'db', ids: prop('duckIds') })
  });

  let owner = Owner.create({ db: this.db });
  let opts = getDefinition(owner, 'doc');

  assert.deepEqual(pick(opts, ['database', 'owner', 'document']), {
    database: 'db',
    owner: [ 'duckIds.[]' ],
    document: [ 'id' ]
  });

  assert.ok(!opts.matches(EmberObject.create({ id: 'green' }), owner));
  assert.ok(opts.matches(EmberObject.create({ id: 'yellow' }), owner));

  assert.deepEqual(opts.query(owner), {
    all: true,
    keys: [ 'yellow' ]
  });
});

test('load', async function(assert) {
  await this.recreate();
  await all([
    this.docs.save({ _id: 'yellow' }),
    this.docs.save({ _id: 'green' })
  ]);

  let Owner = EmberObject.extend({
    duckIds: A([]),
    docs: findByIds({ database: 'db', ids: prop('duckIds') })
  });

  let owner = Owner.create({ db: this.db });
  let proxy = owner.get('docs');

  assert.equal(proxy._internal.loader(true).state.isLoaded, false);
  assert.equal(proxy._internal.loader(true).state.isLoading, false);

  assert.equal(proxy.get('isLoading'), false);
  assert.equal(proxy.get('length'), 0);

  owner.get('duckIds').pushObject('yellow');

  assert.equal(proxy._internal.loader(true).state.isLoading, false);
  assert.equal(proxy.get('isLoading'), true);
  await this.settle(proxy);

  owner.get('duckIds').pushObject('green');

  assert.equal(proxy._internal.loader(true).state.isLoading, false);
  assert.equal(proxy.get('isLoading'), true);
  await this.settle(proxy);

  assert.deepEqual(proxy.mapBy('id'), [ 'yellow', 'green' ]);

  run(() => owner.destroy());
});

test('manual load', async function(assert) {
  await this.recreate();
  await all([
    this.docs.save({ _id: 'yellow' }),
    this.docs.save({ _id: 'green' })
  ]);

  let Owner = EmberObject.extend({
    duckIds: A([ 'green', 'yellow' ]),
    docs: findByIds({ database: 'db', ids: prop('duckIds'), autoload: false })
  });

  let owner = Owner.create({ db: this.db });
  let proxy = owner.get('docs');

  let result = await proxy.load();
  assert.ok(result === proxy);

  assert.deepEqual(proxy.mapBy('id'), [ 'green', 'yellow' ]);

  run(() => owner.destroy());
});
