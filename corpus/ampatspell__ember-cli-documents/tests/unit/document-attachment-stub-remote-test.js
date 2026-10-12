import configurations from '../helpers/configurations';
import { test } from '../helpers/qunit';

configurations(module => {

  module('document-attachment-stub-remote', {
    beforeEach() {
      return this.recreate();
    }
  });

  test('stub is not replaced by different stub', async function(assert) {
    let doc = this.db.doc({
      id: 'thing',
      attachments: {
        message: {
          contentType: 'text/plain', data: 'hey there'
        }
      }
    });

    let zeroAttachment = doc.get('attachments.message')._internal;
    let zeroContent = doc.get('attachments.message')._internal.content;
    assert.ok(zeroContent.type, 'string');

    await doc.save();

    let firstAttachment = doc.get('attachments.message')._internal;
    let firstContent = doc.get('attachments.message')._internal.content;
    assert.ok(firstContent.type, 'stub');

    await doc.reload();

    let secondAttachment = doc.get('attachments.message')._internal;
    let secondContent = doc.get('attachments.message')._internal.content;
    assert.ok(secondContent.type, 'stub');

    assert.ok(zeroAttachment === firstAttachment);
    assert.ok(zeroContent !== firstContent);

    assert.ok(firstAttachment === secondAttachment);
    assert.ok(firstContent === secondContent);
  });

  test('stub model basic properties', async function(assert) {
    let doc = this.db.doc({
      id: 'thing',
      attachments: {
        message: {
          contentType: 'text/plain', data: 'hey there'
        }
      }
    });

    await doc.save();

    let att = doc.get('attachments.message');
    let content = att._internal.content;

    assert.equal(att.get('contentType'), 'text/plain');
    assert.equal(att.get('digest'), content.props.digest);
    assert.equal(att.get('revpos'), content.props.revpos);
    assert.equal(att.get('length'), 9);
  });

  test('content change notifies serialized prop change', async function(assert) {
    let doc = this.db.doc({
      id: 'thing',
      attachments: {
        message: {
          contentType: 'text/plain', data: 'hey there'
        }
      }
    });

    assert.deepEqual(doc.get('serialized'), {
      "attachments": {
        "message": {
          "content_type": "text/plain",
          "type": "string",
          "value": "hey there"
        }
      },
      "id": "thing"
    });

    await doc.save();

    assert.deepEqual_(doc.get('serialized'), {
      "attachments": {
        "message": {
          "content_type": "text/plain",
          "digest": "ignored",
          "length": 9,
          "revpos": "ignored",
          "stub": true
        }
      },
      "id": "thing",
      "rev": "ignored"
    });
  });

});
