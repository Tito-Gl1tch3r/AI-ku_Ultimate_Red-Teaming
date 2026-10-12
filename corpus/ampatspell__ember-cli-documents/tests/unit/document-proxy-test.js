import EmberObject from '@ember/object';
import { run } from '@ember/runloop';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

module('document-proxy', {
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
        if(!id) {
          return;
        }
        return { id };
      }
    };
    this.create = () => this.db._createInternalDocumentProxy(this.owner, this.opts).model(true);
  }
});

test('exists', function(assert) {
  let proxy = this.create();
  assert.ok(proxy);
  assert.ok(proxy._internal);
});

test('proxy has loader and filter', function(assert) {
  let proxy = this.create();
  assert.ok(proxy.get('loader'));
  assert.ok(proxy.get('filter'));
});

test('proxy has state', function(assert) {
  this.owner.set('id', 'foof');
  let proxy = this.create();
  assert.deepEqual(proxy.get('state'), {
    "error": null,
    "isError": false,
    "isLoaded": false,
    "isLoading": false,
    "isLoadable": true
  });
});

test('new doc appears in content', function(assert) {
  this.opts.autoload = false;
  this.owner.set('id', 'thing');
  let proxy = this.create();

  assert.ok(!proxy.get('content'));

  let doc = this.db.doc({ id: 'thing' });

  assert.ok(proxy.get('content') === doc);
});

test('new doc appears in content after owner prop change', function(assert) {
  this.opts.autoload = false;
  let proxy = this.create();
  let doc = this.db.doc({ id: 'thing' });
  assert.ok(!proxy.get('content'));

  this.owner.set('id', 'thing');

  assert.ok(proxy.get('content') === doc);
});

test('new doc appears in content after doc prop change', function(assert) {
  this.owner.set('id', 'thing');
  this.opts.autoload = false;
  let proxy = this.create();
  let doc = this.db.doc({});
  assert.ok(!proxy.get('content'));

  doc.set('id', 'thing');

  assert.ok(proxy.get('content') === doc);
});

test('content is unset on new document destroy', function(assert) {
  this.opts.autoload = false;
  this.owner.set('id', 'thing');
  let doc = this.db.doc({ id: 'thing' });
  let proxy = this.create();

  assert.ok(proxy.get('content') === doc);

  run(() => doc.destroy());

  assert.ok(!proxy.get('content'));
});

test('proxy destroy destroys loader and filter', function(assert) {
  let proxy = this.create();
  let loader = proxy.get('loader');
  let filter = proxy.get('filter');

  run(() => proxy.destroy());

  assert.ok(loader.isDestroyed);
  assert.ok(filter.isDestroyed);
});
