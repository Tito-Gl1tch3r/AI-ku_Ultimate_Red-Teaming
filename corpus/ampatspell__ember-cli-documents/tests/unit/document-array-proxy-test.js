import EmberObject from '@ember/object';
import { run } from '@ember/runloop';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

module('document-array-proxy', {
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
  }
});

test('exists', function(assert) {
  let proxy = this.create();
  assert.ok(proxy);
  assert.ok(proxy._internal);
});

test('has filtered content', function(assert) {
  this.db.doc({ id: 'one', type: 'duck' });
  this.db.doc({ id: 'two', type: 'duck' });
  this.db.doc({ id: 'three', type: 'building' });
  let proxy = this.create();
  assert.deepEqual(proxy.mapBy('id'), [ 'one', 'two' ]);
});

test('proxy has state', function(assert) {
  let proxy = this.create();
  assert.deepEqual(proxy.get('state'), {
    "error": null,
    "isError": false,
    "isLoadable": true,
    "isLoaded": false,
    "isLoading": false
  });
});

test('new doc appears in content', function(assert) {
  this.opts.autoload = false;
  let proxy = this.create();

  assert.equal(proxy.get('length'), 0);

  let doc = this.db.doc({ type: 'duck' });

  assert.equal(proxy.get('length'), 1);
  assert.ok(proxy.objectAt(0) === doc);
});

test('new doc appears in content after owner prop change', function(assert) {
  this.opts.autoload = false;
  let proxy = this.create();

  let doc = this.db.doc({ type: 'building' });
  assert.equal(proxy.get('length'), 0);

  this.owner.set('type', 'building');

  assert.equal(proxy.get('length'), 1);
  assert.ok(proxy.objectAt(0) === doc);
});

test('new doc appears in content after doc prop change', function(assert) {
  this.opts.autoload = false;
  let proxy = this.create();

  let doc = this.db.doc({});
  assert.equal(proxy.get('length'), 0);

  doc.set('type', 'duck');

  assert.equal(proxy.get('length'), 1);
  assert.ok(proxy.objectAt(0) === doc);
});

test('content is unset on new document destroy', function(assert) {
  this.opts.autoload = false;
  let doc = this.db.doc({ type: 'duck' });
  let proxy = this.create();

  assert.ok(proxy.objectAt(0) === doc);

  run(() => doc.destroy());

  assert.ok(!proxy.objectAt(0));
});

test('proxy destroy destroys loader and filter', function(assert) {
  let proxy = this.create();
  let loader = proxy.get('loader');
  let filter = proxy.get('filter');

  run(() => proxy.destroy());

  assert.ok(loader.isDestroyed);
  assert.ok(filter.isDestroyed);
});
