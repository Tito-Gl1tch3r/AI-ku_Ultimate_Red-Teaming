import { run } from '@ember/runloop';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import createBlob from 'couch/util/create-blob';
import Attachments from 'documents/document/attachments/internal/attachments';
import Attachment from 'documents/document/attachments/internal/attachment';

module('document-attachments');

test('doc has attachments', function(assert) {
  let doc = this.db.doc();
  assert.ok(doc.get('attachments'));
});

test('attachments has _internal', function(assert) {
  let doc = this.db.doc();
  assert.ok(doc.get('attachments')._internal);
});

test('_model is unset on attachments destroy', function(assert) {
  let doc = this.db.doc();
  let attachments = doc.get('attachments');
  let internal = attachments._internal;
  assert.ok(internal._model);

  run(() => attachments.destroy());

  assert.ok(attachments.isDestroyed);
  assert.ok(!internal._model);
});

test('detached attachment can be attached', function(assert) {
  let doc = this.db.doc();
  let msg = this.db.attachment({ data: 'hey there' });
  doc.get('attachments').set('message', msg);
  assert.ok(doc.get('attachments.message') === msg);
  assert.ok(msg._internal.parent === doc.get('attachments')._internal);
});

test('detached attachment can be used in db.doc', function(assert) {
  let msg = this.db.attachment({ data: 'hey there' });
  let doc = this.db.doc({ attachments: { message: msg }});
  assert.ok(doc.get('attachments.message') === msg);
  assert.ok(msg._internal.parent === doc.get('attachments')._internal);
  assert.ok(msg._internal === doc.get('attachments.message')._internal);
});

test('attachment can be created from object', function(assert) {
  let doc = this.db.doc();
  doc.get('attachments').set('message', { data: 'hey there' });
  assert.equal(doc.get('attachments.message')._internal.content.value, 'hey there');
});

test('add attachment marks document dirty', function(assert) {
  let doc = this.db.doc();
  let attachments = doc.get('attachments');
  assert.equal(doc.get('isDirty'), false);
  attachments.set('message', { data: 'hey there' });
  assert.equal(doc.get('isDirty'), true);
});

test('attachments can be created in db.doc', function(assert) {
  let doc = this.db.doc({
    attachments: {
      one: {
        contentType: 'text/plain',
        data: 'hey there'
      },
      two:  {
        data: createBlob('hey there', 'text/plain')
      }
    }
  });
  assert.equal(doc.get('attachments')._internal.values.one.content.type, 'string');
  assert.equal(doc.get('attachments')._internal.values.two.content.type, 'file');
});

test('attachment names', function(assert) {
  let doc = this.db.doc({
    attachments: {
      one: {
        contentType: 'text/plain',
        data: 'hey there'
      },
      two:  {
        data: createBlob('hey there', 'text/plain')
      }
    }
  });

  assert.deepEqual(doc.get('attachments.names'), [ 'one', 'two' ]);

  doc.get('attachments').set('two', null);

  assert.deepEqual(doc.get('attachments.names'), [ 'one' ]);
});

test('attachment object keys are serialized', function(assert) {
  let doc = this.db.doc({
    attachments: {
      fooBar: { contentType: 'text/plain', data: 'hey there' }
    }
  });

  assert.deepEqual(doc.get('attachments.names'), [ 'fooBar' ]);

  assert.deepEqual(doc.serialize('model'), {
    "attachments": {
      "fooBar": {
        "type": "string",
        "content_type": "text/plain",
        "value": "hey there"
      }
    }
  });

  assert.deepEqual(doc.serialize('document'), {
    "_attachments": {
      "fooBar": {
        "content_type": "text/plain",
        "data": "hey there"
      }
    }
  });
});

test('attachment object keys are deserialized', function(assert) {
  let doc = this.db.push({
    _id: 'foo',
    "_attachments": {
      "foo_bar": {
        "content_type": "text/plain",
        "data": "hey there"
      }
    }
  });

  assert.deepEqual(doc.get('serialized'), {
    "attachments": {
      "foo_bar": {
        "type": "string",
        "content_type": "text/plain",
        "value": "hey there"
      }
    },
    "id": "foo"
  });
});

test('attachment remove', function(assert) {
  let doc = this.db.doc({
    attachments: {
      thing: { contentType: 'text/plain', data: 'hey there' }
    }
  });

  assert.deepEqual(doc.get('attachments.names'), [ 'thing' ]);

  let thing = doc.get('attachments.thing');
  thing.remove();

  assert.ok(!doc.get('attachments.thing'));
  assert.ok(!thing._internal.parent);

  assert.deepEqual(doc.get('attachments.names'), []);
});

test('set doc.attachments', function(assert) {
  let doc = this.db.doc();

  assert.deepEqual(doc.get('serialized'), {});

  doc.set('attachments', { foo: { data: 'hey' } });
  assert.ok(doc.get('attachments')._internal instanceof Attachments);
  assert.ok(doc.get('attachments.foo')._internal instanceof Attachment);

  assert.deepEqual(doc.get('serialized'), {
    "attachments": {
      "foo": {
        "content_type": "text/plain",
        "type": "string",
        "value": "hey"
      }
    }
  });
});
