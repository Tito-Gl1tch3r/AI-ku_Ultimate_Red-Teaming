import configurations from '../helpers/configurations';
import { test } from '../helpers/qunit';
import createBlob from 'couch/util/create-blob';

configurations(module => {

  module('document-attachment-file-remote', {
    beforeEach() {
      return this.recreate();
    }
  });

  test('save', async function(assert) {
    let data = createBlob('hey there', 'text/plain');
    let doc = this.db.doc({ id: 'foo' });
    doc.get('attachments').set('message', { data });

    await doc.save();

    let json = await this.docs.load('foo');

    assert.deepEqual_(json, {
      "_attachments": {
        "message": {
          "content_type": "text/plain",
          "digest": "ignored",
          "length": 9,
          "revpos": "ignored",
          "stub": true
        }
      },
      "_id": "foo",
      "_rev": "ignored"
    });
  });

  test('load', async function(assert) {
    let data = createBlob('hey there', 'text/plain');
    await this.docs.save({ _id: 'thing', _attachments: { message: { data } } });

    let doc = await this.db.find('thing');
    assert.ok(doc.get('attachments.message'));
    assert.deepEqual_(doc.get('attachments.message')._internal.content.props, {
      "content_type": "text/plain",
      "digest": "ignored",
      "length": 9,
      "revpos": "ignored",
      "stub": true
    });
  });

});
