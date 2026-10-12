import EmberObject from '@ember/object';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

module('document-proxy-remote', {
  async beforeEach() {
    this.owner = EmberObject.create({ id: null });
    this.opts = {
      owner: [ 'id' ],
      document: [ 'id' ],
      matches(doc, owner) {
        return doc.get('id') === owner.get('id');
      },
      query(owner) {
        let id = owner.get('id');
        return { id };
      }
    };
    this.create = () => this.db._createInternalDocumentProxy(this.owner, this.opts).model(true);
    await this.recreate();
  }
});

test('proxy starts loading on isLoading', async function(assert) {
  this.owner.set('id', 'foof');

  let proxy = this.create();
  assert.ok(proxy.get('isLoading'));

  assert.ok(this.db._operations.length === 1);
  await this.db.settle();

  assert.ok(!proxy.get('isLoading'));
  assert.equal(proxy.get('error').error, 'not_found');
});

test('proxy load result appears in content', async function(assert) {
  await this.docs.save({ _id: 'duck', name: 'Yellow' });
  this.owner.set('id', 'duck');

  let proxy = this.create();
  assert.ok(proxy.get('isLoading'));

  assert.ok(this.db._operations.length === 1);
  await this.db.settle();

  assert.equal(proxy.get('name'), 'Yellow');
});

test('deleted doc', async function(assert) {
  this.opts.autoload = false;
  this.owner.set('id', 'duck');
  await this.docs.save({ _id: 'duck', name: 'Yellow' });

  let proxy = this.create();

  await proxy.load();

  let duck = proxy.get('content');

  assert.equal(proxy.get('name'), 'Yellow');

  await duck.delete();

  assert.ok(!proxy.get('content'));
});
