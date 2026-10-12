import EmberObject from '@ember/object';
import { all } from 'rsvp';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

/* global emit */
const ddoc = {
  views: {
    'by-id-with-feathers': {
      map: function(doc) {
        if(doc.type !== 'duck') {
          return;
        }
        emit(doc._id);
        var feathers = doc.feathers;
        if(!feathers) {
          return;
        }
        for(var i = 0; i < feathers.length; i++) {
          var id = feathers[i];
          emit(doc._id, { _id: id });
        }
      }
    }
  }
};

module('document-proxy-linked-remote', {
  async beforeEach() {
    this.owner = EmberObject.create({ key: 'duck:yellow' });
    this.opts = {
      owner: [ 'key' ],
      document: [ 'type' ],
      matches(doc) {
        return doc.get('type') === 'duck';
      },
      query(owner) {
        let key = owner.get('key');
        return { ddoc: 'duck', view: 'by-id-with-feathers', limit: undefined, key };
      }
    };
    this.create = () => this.db._createInternalDocumentProxy(this.owner, this.opts).model(true);
    this.insertDuck = () => this.docs.save({
      _id: 'duck:yellow',
      type: 'duck',
      feathers: [ 'duck:yellow:feather:yellow', 'duck:yellow:feather:green' ]
    });
    this.insertFeathers = () => all([
      this.docs.save({
        _id: 'duck:yellow:feather:yellow',
        type: 'feather'
      }),
      this.docs.save({
        _id: 'duck:yellow:feather:green',
        type: 'feather'
      })
    ]);
    this.insert = () => all([ this.insertDuck(), this.insertFeathers() ]);
    await this.recreate();
    await this.docs.get('design').save('duck', ddoc);
  }
});

test('load', async function(assert) {
  await this.insert();
  let proxy = this.create();
  await proxy.load();
  let duck = this.db.existing('duck:yellow');
  assert.ok(duck);
  assert.ok(this.db.existing('duck:yellow:feather:yellow'));
  assert.ok(this.db.existing('duck:yellow:feather:green'));
  assert.ok(proxy.get('content') === duck);
});

test('load fails for missing duck', async function(assert) {
  await this.insertFeathers();
  let proxy = this.create();
  try {
    await proxy.load();
  } catch(err) {
    assert.ok(!this.db.existing('duck:yellow'));
    assert.ok(!this.db.existing('duck:yellow:feather:yellow'));
    assert.ok(!this.db.existing('duck:yellow:feather:green'));
    assert.deepEqual(err.toJSON(), {
      "error": "not_found",
      "reason": "missing",
      "status": 404
    });
  }
});
