import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import createBlob from 'couch/util/create-blob';

module('document-attachment-file');

test('attachment has fil content', function(assert) {
  let data = createBlob('hey there', 'text/plain');
  let attachment = this.db.attachment({ data });
  let content = attachment.get('content');
  assert.ok(content);
  assert.equal(content.get('type'), 'file');
});

test('attachment has file content internal', function(assert) {
  let data = createBlob('hey there', 'text/plain');
  let attachment = this.db.attachment({ data });
  let content = attachment.get('content');
  let internal = content._internal;
  assert.equal(internal.type, 'file');
});

test('attachment file content internal has data', function(assert) {
  let data = createBlob('hey there', 'text/plain');
  let attachment = this.db.attachment({ data });
  let internal = attachment.get('content')._internal;
  assert.equal(internal.file, data);
  assert.equal(internal.contentType, 'text/plain');
});

test('serialize model', function(assert) {
  let data = createBlob('hey there', 'text/plain');
  let doc = this.db.doc();
  doc.get('attachments').set('blob', { data });
  assert.deepEqual(doc.serialize(), {
    "attachments": {
      "blob": {
        "type": "file",
        "content_type": "text/plain",
        "filename": undefined,
        "size": 9
      }
    }
  });
});

test('serialize document', function(assert) {
  let data = createBlob('hey there', 'text/plain');
  let doc = this.db.doc();
  doc.get('attachments').set('blob', { data });
  assert.deepEqual(doc.serialize('document'), {
    "_attachments": {
      "blob": {
        "data": doc.get('attachments.blob')._internal.content.loader
      }
    }
  });
});
