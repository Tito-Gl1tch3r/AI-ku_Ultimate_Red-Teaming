import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

module('document-push');

test('push fresh', function(assert) {
  let docs = this.db._documents;
  let doc = this.db.push({ _id: 'hello' });
  assert.ok(doc);
  assert.equal(doc.get('id'), 'hello');
  assert.ok(docs.all.includes(doc._internal));
  assert.ok(!docs.new.includes(doc._internal));
  assert.ok(docs.saved.hello === doc._internal);
  assert.deepEqual(doc.get('state'), {
    "error": null,
    "isDeleted": false,
    "isDirty": false,
    "isError": false,
    "isLoaded": true,
    "isLoading": false,
    "isNew": false,
    "isSaving": false
  });
});

test('push update to existing', function(assert) {
  let first = this.db.push({ _id: 'hello', name: 'one', old: true });

  assert.equal(first.get('name'), 'one');
  assert.equal(first.get('old'), true);
  assert.deepEqual(first.get('state'), {
    "error": null,
    "isDeleted": false,
    "isDirty": false,
    "isError": false,
    "isLoaded": true,
    "isLoading": false,
    "isNew": false,
    "isSaving": false
  });

  let second = this.db.push({ _id: 'hello', name: 'two', fresh: true });

  assert.ok(first === second);
  assert.ok(first._internal === second._internal);

  assert.equal(second.get('name'), 'two');
  assert.equal(second.get('fresh'), true);
  assert.equal(second.get('old'), undefined);
  assert.deepEqual(second.get('state'), {
    "error": null,
    "isDeleted": false,
    "isDirty": false,
    "isError": false,
    "isLoaded": true,
    "isLoading": false,
    "isNew": false,
    "isSaving": false
  });
});

test('push fresh deleted', function(assert) {
  let docs = this.db._documents;
  let doc = this.db.push({ _id: 'hello', _deleted: true });
  assert.ok(doc);
  assert.deepEqual(doc.get('state'), {
    "error": null,
    "isDeleted": true,
    "isDirty": false,
    "isError": false,
    "isLoaded": true,
    "isLoading": false,
    "isNew": false,
    "isSaving": false
  });
  assert.ok(!docs.all.includes(doc._internal));
  assert.ok(!docs.new.includes(doc._internal));
  assert.ok(!docs.saved.hello);
  assert.ok(docs.deleted.hello);
});

test('resurrect deleted', function(assert) {
  let docs = this.db._documents;
  let doc = this.db.push({ _id: 'hello', _deleted: true });
  let res = this.db.push({ _id: 'hello', name: 'foof' });
  assert.ok(doc === res);

  assert.ok(docs.all.includes(doc._internal));
  assert.ok(!docs.new.includes(doc._internal));
  assert.ok(docs.saved.hello);
  assert.ok(!docs.deleted.hello);
});

test('existing create returns deleted doc', function(assert) {
  let doc = this.db.push({ _id: 'hello', _deleted: true });
  let ret = this.db.existing('hello', { create: true });
  assert.ok(ret === doc);
});

test('instantiate false returns push info', function(assert) {
  let push = this.db.push({ _id: 'hello' }, { instantiate: false });
  assert.ok(push);
  assert.equal(push.id, 'hello');
  assert.equal(push.isDeleted, false);
  let doc = push.get();
  assert.ok(doc);
});

test('instantiate false returns push info for deleted doc', function(assert) {
  let push = this.db.push({ _id: 'hello', _deleted: true }, { instantiate: false });
  assert.ok(push);
  assert.equal(push.id, 'hello');
  assert.equal(push.isDeleted, true);
  let doc = push.get({ deleted: true });
  assert.ok(doc);
});

test('push with underscored nested keys', function(assert) {
  let doc = this.db.push({ _id: 'foof', thing: { _name: 'thing', _nested: { _id: 'ok', _foo_bar: 'naiss' } } });
  assert.equal(doc._internal.values.thing.values._name, 'thing');
  assert.equal(doc._internal.values.thing.values._nested.values._id, 'ok');
  assert.equal(doc._internal.values.thing.values._nested.values._foo_bar, 'naiss');
  assert.deepEqual(doc.serialize('model'), {
    "id": "foof",
    "thing": {
      "_name": "thing",
      "_nested": {
        "_foo_bar": "naiss",
        "_id": "ok"
      }
    }
  });
  assert.deepEqual(doc.serialize('document'), {
    "_id": "foof",
    "thing": {
      "_name": "thing",
      "_nested": {
        "_foo_bar": "naiss",
        "_id": "ok"
      }
    }
  });
});

test('push does not deserialize identical rev', function(assert) {
  this.db.push({ _id: 'foof', _rev: '1-asd', message: 'one' });
  assert.equal(this.db.existing('foof').get('message'), 'one');

  this.db.push({ _id: 'foof', _rev: '1-asd', message: 'two' });
  assert.equal(this.db.existing('foof').get('message'), 'one');

  this.db.push({ _id: 'foof', _rev: '2-asd', message: 'three' });
  assert.equal(this.db.existing('foof').get('message'), 'three');
});

test('push always deserialize for missing rev', function(assert) {
  this.db.push({ _id: 'foof', message: 'one' });
  assert.equal(this.db.existing('foof').get('message'), 'one');

  this.db.push({ _id: 'foof', message: 'two' });
  assert.equal(this.db.existing('foof').get('message'), 'two');
});

test('reload same rev is deserialized', async function(assert) {
  await this.recreate();
  await this.docs.save({ _id: 'duck', name: 'Yellow' });

  let doc = await this.db.first('duck');
  assert.equal(doc.get('name'), 'Yellow');

  doc.set('name', 'Green');
  await doc.reload();

  assert.equal(doc.get('name'), 'Yellow');
});

test('push based on rev', async function(assert) {
  this.db.push({ _id: 'thing', _rev: '163-6708c0ea6856db4df198825fd3ee32cc', version: '163' });

  assert.deepEqual(this.db.existing('thing').get('serialized'), {
    "id": "thing",
    "rev": "163-6708c0ea6856db4df198825fd3ee32cc",
    "version": "163"
  });

  this.db.push({ _id: 'thing', _rev: '164-dd30b2560a17fd63f4198bd3a3f948b9', version: '164' });

  assert.deepEqual(this.db.existing('thing').get('serialized'), {
    "id": "thing",
    "rev": "164-dd30b2560a17fd63f4198bd3a3f948b9",
    "version": "164"
  });

  this.db.push({ _id: 'thing', _rev: '163-6708c0ea6856db4df198825fd3ee32cc', version: '163' });

  assert.deepEqual(this.db.existing('thing').get('serialized'), {
    "id": "thing",
    "rev": "164-dd30b2560a17fd63f4198bd3a3f948b9",
    "version": "164"
  });

  this.db.push({ _id: 'thing', _rev: '162-6708c0ea6856db4df198825fd3ee32cc', version: '162' });

  assert.deepEqual(this.db.existing('thing').get('serialized'), {
    "id": "thing",
    "rev": "164-dd30b2560a17fd63f4198bd3a3f948b9",
    "version": "164"
  });

  this.db.push({ _id: 'thing', _rev: '', version: 'unknown' });

  assert.deepEqual(this.db.existing('thing').get('serialized'), {
    "id": "thing",
    "rev": "",
    "version": "unknown"
  });

  this.db.push({ _id: 'thing', _rev: '163-6708c0ea6856db4df198825fd3ee32cc', version: '163' });

  assert.deepEqual(this.db.existing('thing').get('serialized'), {
    "id": "thing",
    "rev": "163-6708c0ea6856db4df198825fd3ee32cc",
    "version": "163"
  });
});
