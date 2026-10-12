import ArrayProxy from '@ember/array/proxy';
import { A } from '@ember/array';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import createArratUnifyMixin from 'documents/util/create-array-unify-mixin';

const Mixin = createArratUnifyMixin({ root: { array: '_root' }, content: '_unifiedContent' });
const Proxy = ArrayProxy.extend(Mixin);

let create = root => Proxy.create({ _root: root, _unifiedContent: A() });

module('create-array-unify-mixin');

test('setup', function(assert) {
  let root = A();
  let proxy = create(root);
  assert.ok(proxy);
  assert.ok(proxy.get('_root') === root);
});

test('array in root array is observed', function(assert) {
  let events = [];

  let root = A();
  create(root);

  let item = [];

  item.addEnumerableObserver = () => {
    events.push('add');
  };

  item.removeEnumerableObserver = () => {
    events.push('remove');
  }

  root.pushObject(item);

  assert.deepEqual(events, [ 'add' ]);

  root.removeObject(item);

  assert.deepEqual(events, [ 'add', 'remove' ]);
});

test('nested array initial state, add, remove', function(assert) {
  let one = A([ 'one-one' ]);
  let two = A([ 'two-one' ]);

  let root = A([ one ]);
  let proxy = create(root);

  assert.deepEqual(proxy.get('_unifiedContent'), [ 'one-one' ]);

  one.pushObject('one-two');

  assert.deepEqual(proxy.get('_unifiedContent'), [ 'one-one', 'one-two' ]);

  root.pushObject(two);

  assert.deepEqual(proxy.get('_unifiedContent'), [ 'one-one', 'one-two', 'two-one' ]);

  two.pushObject('two-two');

  assert.deepEqual(proxy.get('_unifiedContent'), [ 'one-one', 'one-two', 'two-one', 'two-two' ]);

  root.removeObject(one);

  assert.deepEqual(proxy.get('_unifiedContent'), [ 'two-one', 'two-two' ]);
});
