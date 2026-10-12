import EmberObject from '@ember/object';
import { run } from '@ember/runloop';
import { all } from 'rsvp';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

const ddoc = {
  views: {
    'all': {
      map(doc) {
        /* global emit */
        emit(doc._id);
      }
    }
  }
};

let _opts = {
  ddoc: 'main',
  view: 'all',
  limit: 3,
  start: null,
  end: {}
};

module('document-paginated-proxy-remote', {
  async beforeEach() {
    this.owner = EmberObject.create({ type: 'duck' });
    this.opts = {
      query(owner, state) {
        let opts = _opts;

        let ddoc = opts.ddoc;
        let view = opts.view;
        let limit = opts.limit + 1;
        let skip;
        let startkey;
        let startkey_docid;
        let endkey = opts.end;

        if(state) {
          skip = 1;
          startkey_docid = state.id;
          startkey = state.value;
          skip = 1;
        } else {
          startkey = opts.start;
        }

        return {
          ddoc,
          view,
          skip,
          limit,
          startkey,
          startkey_docid,
          endkey
        };
      },
      loaded(state_, array) {
        let opts = _opts;

        let { length, lastObject: last } = array.getProperties('length', 'lastObject');

        let isMore = false;
        let state = null;

        if(last) {
          let value;
          if(state_) {
            value = array.objectAt(length - 2) || last;
          } else {
            value = last;
          }
          state = {
            id:    last.get('id'),
            value: value.get('id')
          };
          isMore = length > opts.limit;
        }

        return {
          isMore,
          state
        };
      },
      matches(doc, owner, state) {
        if(state) {
          return doc.get('id') < state.value;
        }
        return doc.get('type') === 'duck';
      },
    };
    this.create = () => this.db._createInternalPaginatedProxy(this.owner, this.opts).model(true);
    this.insert = (count=10) => {
      let promises = [];
      for(let i = 0; i < count; i++) {
        promises.push(this.docs.save({ _id: `duck:${i}`, type: 'duck' }));
      }
      return all(promises);
    }
    await this.recreate();
    await this.docs.get('design').save('main', ddoc);
  }
});

test('exists', function(assert) {
  let proxy = this.create();
  assert.ok(proxy);
  assert.ok(proxy._internal);
  run(() => proxy.destroy());
});

test('content includes only state-matched docs', async function(assert) {
  await this.insert();
  let proxy = this.create();

  assert.equal(proxy.get('length'), 0);

  await proxy.load();

  assert.equal(proxy.get('length'), 3);

  run(() => proxy.destroy());
});

test('content includes only state-matched docs with all loaded previously', async function(assert) {
  await this.insert();
  await this.db.find({ ddoc: 'main', view: 'all' });
  let proxy = this.create();

  assert.equal(proxy.get('length'), 0);
  assert.equal(proxy.get('all.length'), 10);

  await proxy.load();

  assert.equal(proxy.get('length'), 3);
  assert.equal(proxy.get('all.length'), 10);

  run(() => proxy.destroy());
});

test('content includes only state-matched docs with some loaded previously', async function(assert) {
  await this.insert();
  await this.db.find({ ddoc: 'main', view: 'all', keys: [ 'duck:5', 'duck:3' ] });

  let proxy = this.create();

  assert.deepEqual(proxy.get('state'), {
    "isLoadable": true,
    "error": null,
    "isError": false,
    "isLoaded": false,
    "isLoading": false,
    "isMore": false
  });
  assert.deepEqual(proxy.mapBy('id'), [ ]);
  assert.equal(proxy.get('all.length'), 2);

  await proxy.load();

  assert.deepEqual(proxy.get('state'), {
    "isLoadable": true,
    "error": null,
    "isError": false,
    "isLoaded": true,
    "isLoading": false,
    "isMore": true
  });
  assert.deepEqual(proxy.mapBy('id'), [ "duck:0", "duck:1", "duck:2" ]);
  assert.equal(proxy.get('all.length'), 5);

  await proxy.loadMore();

  assert.deepEqual(proxy.get('state'), {
    "isLoadable": true,
    "error": null,
    "isError": false,
    "isLoaded": true,
    "isLoading": false,
    "isMore": true
  });
  assert.deepEqual(proxy.mapBy('id'), [ "duck:0", "duck:1", "duck:2", "duck:5", "duck:3", "duck:4" ]);
  assert.equal(proxy.get('all.length'), 8);

  await proxy.loadMore();

  assert.deepEqual(proxy.get('state'), {
    "isLoadable": true,
    "error": null,
    "isError": false,
    "isLoaded": true,
    "isLoading": false,
    "isMore": false
  });
  assert.deepEqual(proxy.mapBy('id'), [ "duck:0", "duck:1", "duck:2", "duck:5", "duck:3", "duck:4", "duck:6", "duck:7" ]);
  assert.equal(proxy.get('all.length'), 10);

  run(() => proxy.destroy());
});
