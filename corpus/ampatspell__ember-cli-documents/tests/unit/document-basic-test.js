import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

module('document-basic');

test('document has an id', function(assert) {
  let doc = this.db.doc({ id: 'hello' });
  assert.equal(doc.get('id'), 'hello');
});

test('document allows setting id', function(assert) {
  let doc = this.db.doc();
  assert.equal(doc.set('id', 'hello'), 'hello');
  assert.equal(doc.get('id'), 'hello');
});

test('document has a rev', function(assert) {
  let doc = this.db.doc({ rev: '1-hello' });
  assert.equal(doc.get('rev'), '1-hello');
});

test('document has a reference to database', function(assert) {
  let doc = this.db.doc();
  assert.ok(doc.get('database') === this.db);
});

test('document serialize as document', function(assert) {
  let doc = this.db.doc({ id: 'duck:yellow', rev: '1-asd', type: 'duck', name: 'Yellow' });
  assert.deepEqual(doc.serialize('document'), {
    "_id": "duck:yellow",
    "_rev": "1-asd",
    "name": "Yellow",
    "type": "duck"
  });
});

test('document serialized serializes as model', function(assert) {
  let doc = this.db.doc({ id: 'duck:yellow', rev: '1-asd', type: 'duck', name: 'Yellow' });

  assert.deepEqual(doc.get('serialized'), {
    "id": "duck:yellow",
    "rev": "1-asd",
    "name": "Yellow",
    "type": "duck"
  });
});

test('document serialized property change is notified', function(assert) {
  let doc = this.db.doc({ _id: 'duck:yellow', _rev: '1-asd', type: 'duck', name: 'Yellow' });
  assert.equal(doc.get('serialized').name, 'Yellow');
  doc.set('name', 'Another');
  assert.equal(doc.get('serialized').name, 'Another');
});

test('document set and get property', function(assert) {
  let doc = this.db.doc({ _id: 'duck:yellow', _rev: '1-asd', type: 'duck', name: 'Yellow' });
  assert.equal(doc.get('name'), 'Yellow');
  doc.set('name', 'Another');
  assert.equal(doc.get('name'), 'Another');
});

test('document set undefined removes value', function(assert) {
  let doc = this.db.doc({ _id: 'duck:yellow', _rev: '1-asd', type: 'duck', name: 'Yellow' });
  assert.equal(doc.get('name'), 'Yellow');
  doc.set('name', undefined);
  assert.equal(doc.get('name'), undefined);
  assert.ok(!Object.hasOwnProperty(doc.serialize(), 'name'));
});

test('attempt to set _id and _rev directly is ignored', function(assert) {
  let doc = this.db.doc();

  doc.set('_id', 'qwe');
  assert.ok(!doc.get('id'));

  doc.set('_rev', 'qwe');
  assert.ok(!doc.get('rev'));
});

test('get _id and _rev are ignored', function(assert) {
  let doc = this.db.doc({ _id: 'one', _rev: '1-one' });
  assert.ok(!doc.get('_id'));
  assert.ok(!doc.get('_rev'));
});

test('init document with id and rev', function(assert) {
  let doc = this.db.doc({ id: 'asd', rev: '1-asd', _rev: '1-skip' });

  assert.deepEqual_(doc._internal.values, {
    id: 'asd',
    rev: '1-asd'
  });

  assert.equal(doc.get('id'), 'asd');
  assert.equal(doc.get('rev'), '1-asd');

  assert.deepEqual(doc.serialize('document'), {
    _id: 'asd',
    _rev: '1-asd'
  });

  assert.deepEqual(doc.serialize('model'), {
    id: 'asd',
    rev: '1-asd'
  });
});

test('id, name and fooBar set, get, serialize, deserialize', function(assert) {
  let doc = this.db.doc();

  doc.set('id', 'hello');
  assert.equal(doc.get('id'), 'hello', 'doc id must be hello');
  assert.equal(doc._internal.values.id, 'hello', 'doc _id must be hello');
  assert.equal(doc.serialize('model').id, 'hello', 'doc.serialized id must be hello');
  assert.equal(doc.serialize('document')._id, 'hello', 'doc.serialized _id must be hello');

  doc.set('name', 'hello');
  assert.equal(doc.get('name'), 'hello', 'doc name must be hello');
  assert.equal(doc._internal.values.name, 'hello', 'doc name must be hello');
  assert.equal(doc.serialize('model').name, 'hello', 'doc.serialized name must be hello');
  assert.equal(doc.serialize('document').name, 'hello', 'doc.serialized name must be hello');

  doc.set('fooBar', 'hello');
  assert.equal(doc.get('fooBar'), 'hello', 'doc fooBar must be hello');
  assert.equal(doc._internal.values.fooBar, 'hello', 'doc foo_bar must be hello');
  assert.equal(doc.serialize('model').fooBar, 'hello', 'doc.serialized fooBar must be hello');
  assert.equal(doc.serialize('document').fooBar, 'hello', 'doc.serialized foo_bar must be hello');
});

test('document has toString extension', function(assert) {
  let doc = this.db.doc();
  assert.ok((doc+'').includes('ember-cli-documents/>'));
  doc.set('id', 'thing');
  assert.ok((doc+'').includes('ember-cli-documents/thing>'));
});
