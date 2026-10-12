import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

module('document-fastboot');

test('new document is not serialized for fastboot', function(assert) {
  let doc = this.db.doc({ id: 'foo' });
  let json = doc.serialize('shoebox');
  assert.equal(json, undefined);
});

test('saved document is serialized for fastboot', function(assert) {
  let doc = this.db.push({ _id: 'author:duck', type: 'author', name: 'duck' });
  let json = doc.serialize('shoebox');
  assert.deepEqual(json, {
    "_id": "author:duck",
    "name": "duck",
    "type": "author"
  });
});

test('unsaved attachments should not be serialized', async function(assert) {
  let doc = this.db.doc({ attachments: { saved: { data: 'hey' }} });
  await doc.save();
  doc.get('attachments').set('local', { data: 'hello' });
  let json = doc.serialize('shoebox');
  assert.deepEqual_(json, {
    "_attachments": {
      "saved": {
        "content_type": "text/plain",
        "digest": "ignored",
        "length": 3,
        "revpos": "ignored",
        "stub": true
      }
    },
    "_id": doc.get('id'),
    "_rev": "ignored"
  });
});

test('push from shoebox', function(assert) {
  let internal = this.db.__deserialzieShoeboxDocument({
    _id: 'duck:yellow',
    _rev: '1-asd',
    _attachments: {
      saved: {
        "content_type": "text/plain",
        "digest": "ignored",
        "length": 3,
        "revpos": "ignored",
        "stub": true
      }
    },
    name: 'yellow'
  });
  assert.equal(internal.getId(), 'duck:yellow');
  assert.ok(internal.values.attachments.values.saved);
  assert.deepEqual_(internal.state, {
    "error": null,
    "isDeleted": false,
    "isDirty": false,
    "isError": false,
    "isLoaded": true,
    "isLoading": false,
    "isNew": false,
    "isSaving": false
  });
  assert.ok(this.db._documents.saved['duck:yellow']);
});
