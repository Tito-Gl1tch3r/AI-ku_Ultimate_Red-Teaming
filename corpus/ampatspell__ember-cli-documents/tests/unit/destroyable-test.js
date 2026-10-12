import { run } from '@ember/runloop';
import EmberObject from '@ember/object';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import destroyable, { cacheFor } from 'documents/properties/-destroyable';

class Internal {
  constructor(id) {
    this.id = id;
    this.destroyed = false;
  }
  destroy() {
    this.destroyed = true;
  }
}

module('destroyable', {
  beforeEach() {
    this.create = props => {
      return EmberObject.extend({
        id: null,
        property: destroyable('id', {
          create() {
            let id = this.get('id');
            return new Internal(id);
          },
          get(internal) {
            return internal;
          },
          destroy(internal) {
            internal.destroy();
          }
        })
      }).create(props);
    }
  }
});

test('hello', function(assert) {
  let model = this.create();
  assert.ok(model);
  assert.ok(model.get('property'));
});

test('property is cached', function(assert) {
  let model = this.create();
  assert.ok(model.get('property') === model.get('property'));
});

test('property is recreated', function(assert) {
  let model = this.create();
  let first = model.get('property');
  model.set('id', 'another');
  let second = model.get('property')
  assert.equal(second.id, 'another');
  assert.ok(first !== second);
});

test('property is destroyed when model is', function(assert) {
  let model = this.create();
  let prop = model.get('property');
  assert.ok(!prop.destroyed);
  run(() => model.destroy());
  assert.ok(prop.destroyed);
});

test('old property value is destroyed', function(assert) {
  let model = this.create();
  let first = model.get('property');
  model.set('id', 'another');
  let second = model.get('property')
  assert.equal(first.destroyed, true);
  assert.equal(second.destroyed, false);
});

test('cache for', function(assert) {
  let model = this.create();

  let cached = cacheFor(model, 'property');
  assert.ok(!cached);

  let property = model.get('property');
  cached = cacheFor(model, 'property');
  assert.equal(property, cached);

  model.set('id', 'another');

  cached = cacheFor(model, 'property');
  assert.equal(property, cached);

  let next = model.get('property');

  cached = cacheFor(model, 'property');
  assert.equal(next, cached);

  assert.equal(property.destroyed, true);
});
