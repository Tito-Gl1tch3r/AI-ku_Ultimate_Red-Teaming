import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

module('document-object');

test('set and replace object', function(assert) {
  let doc = this.db.doc({ thing: { name: 'Duck' } });

  assert.deepEqual(doc.serialize(), {
    "thing": {
      "name": "Duck"
    }
  });

  let thing = doc.get('thing');
  let internal = thing._internal;

  assert.ok(internal.parent === doc._internal);

  doc.set('thing', { name: 'The Duck' });

  assert.deepEqual(doc.serialize(), {
    "thing": {
      "name": "The Duck"
    }
  });

  assert.ok(thing === doc.get('thing'));
  assert.ok(internal === doc.get('thing._internal'));

  assert.ok(internal.parent === doc._internal);

  doc.set('thing', null);

  assert.deepEqual(doc.serialize(), {
    "thing": null
  });

  assert.ok(internal.parent === null);
});

test('set detached internal object', function(assert) {
  let thing = this.db.object({ name: 'Thing' });

  assert.ok(thing._internal.parent === null);

  let doc = this.db.doc({ thing });

  assert.ok(thing._internal.parent === doc._internal);
  assert.ok(doc.get('thing') === thing);
  assert.ok(doc.get('thing')._internal === thing._internal);
});

test('update document notifies parent on change', function(assert) {
  let doc = this.db.doc({
    id: 'duck:yellow',
    shipping: {
      address: { city: 'Yello', country: 'Duckland' }
    }
  });

  assert.deepEqual(doc.get('serialized'), {
    "id": "duck:yellow",
    "shipping": {
      "address": {
        "city": "Yello",
        "country": "Duckland"
      }
    }
  });

  doc.set('shipping.address.city', 'Yellow');

  assert.deepEqual(doc.get('serialized'), {
    "id": "duck:yellow",
    "shipping": {
      "address": {
        "city": "Yellow",
        "country": "Duckland"
      }
    }
  });

  doc.set('shipping', { ok: true });

  assert.deepEqual(doc.get('serialized'), {
    "id": "duck:yellow",
    "shipping": {
      "ok": true
    }
  });
});

test('underscore properties are allowed in nested objects', function(assert) {
  let doc = this.db.doc({ thing: { _name: 'thing', _nested: { _id: 'ok' } } });
  assert.equal(doc._internal.values.thing.values._name, 'thing');
  assert.equal(doc._internal.values.thing.values._nested.values._id, 'ok');
  assert.deepEqual(doc.serialize('model'), {
    "thing": {
      "_name": "thing",
      "_nested": {
        "_id": "ok"
      }
    }
  });
  assert.deepEqual(doc.serialize('document'), {
    "thing": {
      "_name": "thing",
      "_nested": {
        "_id": "ok"
      }
    }
  });
});
