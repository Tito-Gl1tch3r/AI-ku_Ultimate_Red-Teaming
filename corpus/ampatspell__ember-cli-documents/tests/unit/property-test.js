import EmberObject from '@ember/object';
import { run } from '@ember/runloop';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import { getDefinition } from 'documents';
import { firstById as docById } from '../helpers/properties';

module('property');

test('property destroys proxy', function(assert) {
  let Owner = EmberObject.extend({
    id: 'duck',
    doc: docById({ database: 'db', id: 'id' })
  });

  let owner = Owner.create({ db: this.db });

  let proxy = owner.get('doc');
  assert.ok(proxy);

  run(() => owner.destroy());

  assert.ok(proxy.isDestroyed);
});

test('property has definition meta', function(assert) {
  let Owner = EmberObject.extend({
    id: 'duck',
    doc: docById({ database: 'db', id: 'id' })
  });

  let classDef = getDefinition(Owner, 'doc');
  assert.equal(classDef.database, 'db');

  let owner = Owner.create();
  let instanceDef = getDefinition(owner, 'doc');
  assert.equal(instanceDef.database, 'db');
});

test('property destroys previous proxy on database change', function(assert) {
  let Owner = EmberObject.extend({
    id: 'duck',
    doc: docById({ database: 'db', id: 'id' })
  });

  let owner = Owner.create({ db: this.db });

  let first = owner.get('doc');
  owner.set('db', this.store.database('another'));
  let second = run(() => owner.get('doc'));

  assert.ok(second._internal);

  assert.ok(first !== second);
  assert.ok(first.isDestroying);
});

test('property does not recreate proxy on same database set', function(assert) {
  let Owner = EmberObject.extend({
    id: 'duck',
    doc: docById({ database: 'db', id: 'id' })
  });

  let owner = Owner.create({ db: this.db });

  let first = owner.get('doc');
  owner.set('db', this.db);
  let second = owner.get('doc');

  assert.ok(first === second);
  assert.ok(!first.isDestroying);
});
