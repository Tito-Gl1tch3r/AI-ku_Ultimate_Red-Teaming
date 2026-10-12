import EmberObject from '@ember/object';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import { prop } from 'documents/properties';
import { firstById } from '../helpers/properties';

module('property-prop');

test('property with string value', function(assert) {
  let Owner = EmberObject.extend({
    doc: firstById({ database: 'db', id: 'yellow' })
  });

  let owner = Owner.create({ db: this.db });

  let opts = owner.get('doc._internal.opts');

  assert.deepEqual(opts, {
    autoload: true,
    document: [ 'id' ],
    owner: [],
    matches: opts.matches,
    query: opts.query,
  });

  assert.deepEqual(opts.query(owner), {
    id: 'yellow'
  });
});

test('property with prop', function(assert) {
  let Owner = EmberObject.extend({
    duckId: 'yellow',
    doc: firstById({ database: 'db', id: prop('duckId') })
  });

  let owner = Owner.create({ db: this.db });

  let opts = owner.get('doc._internal.opts');

  assert.deepEqual(opts, {
    autoload: true,
    document: [ 'id' ],
    owner: [ 'duckId' ],
    matches: opts.matches,
    query: opts.query,
  });

  assert.deepEqual(opts.query(owner), {
    id: 'yellow'
  });
});

test('prop has a nice toString', function(assert) {
  let str;

  str = prop('foo')+'';
  assert.ok(str.includes('Property:') && str.includes(':foo'));

  str = prop.wrap('foo')+'';
  assert.ok(str.includes('Static:') && str.includes(':foo'));
});
