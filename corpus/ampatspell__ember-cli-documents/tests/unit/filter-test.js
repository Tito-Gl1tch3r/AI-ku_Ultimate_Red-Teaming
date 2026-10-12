import EmberObject from '@ember/object';
import { run } from '@ember/runloop';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';

module('filter', {
  beforeEach() {
    this.owner = EmberObject.create({ type: null });
    this.opts = {
      owner: [ 'type' ],
      document: [ 'type' ],
      matches(doc, owner) {
        return doc.get('type') === owner.get('type');
      }
    };
    this.filter = () => this.db._createInternalFilter(this.owner, this.opts).model(true);
  }
});

test('create filter', function(assert) {
  let filter = this.filter();
  assert.ok(filter);
  assert.equal(filter.get('values.length'), 0);
  assert.equal(filter.get('value'), undefined);
  run(() => filter.destroy());
});

test('create filter with existing matched values', function(assert) {
  let duck = this.db.doc({ id: 'duck:yellow', type: 'duck' });
  this.db.doc({ id: 'house:big', type: 'house' });
  this.owner.set('type', 'duck');
  let filter = this.filter();
  assert.equal(filter.get('values.length'), 1);
  assert.equal(filter.get('value'), duck);
  run(() => filter.destroy());
});

test('updated doc is removed from values', function(assert) {
  let duck = this.db.doc({ id: 'duck:yellow', type: 'duck' });
  this.owner.set('type', 'duck');
  let filter = this.filter();
  assert.equal(filter.get('values.length'), 1);
  assert.equal(filter.get('value'), duck);
  duck.set('type', 'ducky');
  assert.equal(filter.get('values.length'), 0);
  assert.equal(filter.get('value'), undefined);
  run(() => filter.destroy());
});

test('added doc is added to values', function(assert) {
  this.owner.set('type', 'duck');
  let filter = this.filter();
  assert.equal(filter.get('value'), undefined);
  let duck = this.db.doc({ id: 'duck:yellow', type: 'duck' });
  assert.equal(filter.get('value'), duck);
  run(() => filter.destroy());
});

test('destroy stops observing', function(assert) {
  let duck = this.db.doc({ id: 'duck:yellow', type: 'duck' });

  let events = [];
  let wrap = (name, func, obj) => {
    let fn = obj[func];
    obj[func] = function(...args) {
      events.push({ name, func });
      return fn.call(obj, ...args);
    }
  };

  wrap('owner', 'removeObserver', this.owner);
  wrap('duck', 'removeObserver', duck);
  wrap('documentsIdentity', 'removeEnumerableObserver', this.db.get('documentsIdentity'));

  this.owner.set('type', 'duck');
  let filter = this.filter();
  assert.equal(filter.get('value'), duck);

  run(() => filter.destroy());

  assert.deepEqual(events, [
    {
      "func": "removeObserver",
      "name": "owner"
    },
    {
      "func": "removeEnumerableObserver",
      "name": "documentsIdentity"
    },
    {
      "func": "removeObserver",
      "name": "duck"
    }
  ]);
});

test('destroyed new doc is removed', function(assert) {
  let duck = this.db.doc({ id: 'duck:yellow', type: 'duck' });
  this.owner.set('type', 'duck');

  let filter = this.filter();

  assert.equal(filter.get('values.length'), 1);
  assert.equal(filter.get('value'), duck);

  run(() => duck.destroy());

  assert.equal(filter.get('values.length'), 0);
  assert.equal(filter.get('value'), undefined);

  run(() => filter.destroy());
});
