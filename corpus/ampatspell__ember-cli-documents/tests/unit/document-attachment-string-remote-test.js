import configurations from '../helpers/configurations';
import { test } from '../helpers/qunit';

configurations(module => {

  module('document-attachment-string-remote', {
    beforeEach() {
      return this.recreate();
    }
  });

  test('save', async function(assert) {
    let doc = this.db.doc({ id: 'foo' });
    doc.get('attachments').set('message', { data: 'hey there' });

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
    await this.docs.save({ _id: 'thing', _attachments: { message: { content_type: 'text/plain', data: 'hey there' } } });
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

  test('document is reloaded after save and string content is replaced by stub', async function(assert) {
    let doc = this.db.doc({ id: 'foo' });
    doc.get('attachments').set('message', { data: 'hey there' });

    let internal = doc.get('attachments.message')._internal;
    let content = internal.content;

    await doc.save();

    assert.equal(doc.get('attachments.message.type'), 'stub');
    assert.ok(internal === doc.get('attachments.message')._internal);
    assert.ok(content !== doc.get('attachments.message')._internal.content);
  });

});
