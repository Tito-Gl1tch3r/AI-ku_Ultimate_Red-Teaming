import EmberObject from '@ember/object';
import { all } from 'rsvp';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

const ddoc = {
  views: {
    'by-type': {
      map(doc) {
        /* global emit */
        emit(doc.type);
      }
    }
  }
};

module('document-array-proxy-remote', {
  async beforeEach() {
    this.owner = EmberObject.create({ type: 'duck' });
    this.opts = {
      owner: [ 'type' ],
      document: [ 'type' ],
      matches(doc, owner) {
        return doc.get('type') === owner.get('type');
      },
      query(owner) {
        let type = owner.get('type');
        return { ddoc: 'main', view: 'by-type', key: type };
      }
    };
    this.create = () => this.db._createInternalArrayProxy(this.owner, this.opts).model(true);
    await this.recreate();
    await this.docs.get('design').save('main', ddoc);
  }
});

test('proxy starts loading on isLoading', async function(assert) {
  let proxy = this.create();
  assert.ok(proxy.get('isLoading'));

  assert.ok(this.db._operations.length === 1);
  await this.db.settle();

  assert.ok(!proxy.get('isLoading'));
  assert.ok(proxy.get('isLoaded'));
  assert.equal(proxy.get('length'), 0);
});

test('proxy load result appears in content', async function(assert) {
  await all([
    this.docs.save({ _id: 'yellow', name: 'Yellow', type: 'duck' }),
    this.docs.save({ _id: 'green', name: 'Green', type: 'duck' })
  ]);

  let proxy = this.create();
  assert.ok(proxy.get('isLoading'));

  assert.ok(this.db._operations.length === 1);
  await this.db.settle();

  assert.deepEqual(proxy.mapBy('id'), [ 'green', 'yellow' ]);
});
