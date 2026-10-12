import EmberObject from '@ember/object';
import { merge } from '@ember/polyfills';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import { getDefinition, prop } from 'documents/properties';
import { pick } from 'documents/util/object';
import { firstById, isNewMixin } from '../helpers/properties';

const byId = opts => firstById(merge({ database: 'db' }, opts));
const isNewById = opts => byId(isNewMixin(opts));

module('property-by-id');

test('plain', function(assert) {
  let Owner = EmberObject.extend({
    duckId: 'duck',
    doc: byId({ id: prop('duckId') })
  });

  let owner = Owner.create({ db: this.db });
  let opts = getDefinition(owner, 'doc');

  assert.deepEqual(pick(opts, ['database', 'owner', 'document']), {
    database: 'db',
    owner: [ 'duckId' ],
    document: [ 'id' ]
  });

  assert.ok(!opts.matches(EmberObject.create({ id: 'rabbit' }), owner));
  assert.ok(opts.matches(EmberObject.create({ id: 'duck' }), owner));

  assert.deepEqual(opts.query(owner), {
    id: 'duck'
  });
});

test('isNew mixin', function(assert) {
  let Owner = EmberObject.extend({
    duckId: 'duck',
    isNew: null,
    doc: isNewById({ id: prop('duckId'), new: prop('isNew') })
  });

  let owner = Owner.create({ db: this.db });
  let opts = getDefinition(owner, 'doc');

  assert.ok(opts.matches(EmberObject.create({ id: 'duck', isNew: false }), owner));
  assert.ok(opts.matches(EmberObject.create({ id: 'duck', isNew: true }), owner));

  owner.set('isNew', undefined);

  assert.ok(opts.matches(EmberObject.create({ id: 'duck', isNew: false }), owner));
  assert.ok(opts.matches(EmberObject.create({ id: 'duck', isNew: true }), owner));

  owner.set('isNew', false);

  assert.ok(opts.matches(EmberObject.create({ id: 'duck', isNew: false }), owner));
  assert.ok(!opts.matches(EmberObject.create({ id: 'duck', isNew: true }), owner));

  owner.set('isNew', true);

  assert.ok(!opts.matches(EmberObject.create({ id: 'duck', isNew: false }), owner));
  assert.ok(opts.matches(EmberObject.create({ id: 'duck', isNew: true }), owner));
});
