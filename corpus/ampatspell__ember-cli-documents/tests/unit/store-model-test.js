import { get } from '@ember/object';
import { run } from '@ember/runloop';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import Model from 'documents/document/model';

const Duck = Model.extend();

module('store-model');

test('model can be created', function(assert) {
  this.register('model:duck', Duck);
  let model = this.store.model('duck');
  assert.ok(model);
  assert.ok(Duck.detectInstance(model));
  assert.ok(model.get('store') === this.store);
});

test('model not registered', function(assert) {
  try {
    this.store.model('duck');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "model for name 'duck' is not registered"
    });
  }
});

test('name must be string', function(assert) {
  try {
    this.store.model({});
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "model name must be string"
    });
  }
});

test('name must not be blank', function(assert) {
  try {
    this.store.model('');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "model name must not be blank"
    });
  }
});

test('modelName', function(assert) {
  this.register('model:duck', Duck);
  let model = this.store.model('duck');
  assert.equal(get(model.constructor, 'modelName'), 'duck');
  assert.equal(get(Duck, 'modelName'), undefined);
});

test('opts are applied on model create', function(assert) {
  this.register('model:duck', Duck);
  let model = this.store.model({ type: 'duck', props: { id: 'yellow' } });
  assert.equal(model.get('id'), 'yellow');
  let internal = model._internal;
  run(() => model.destroy());
  model = internal.model(true);
  assert.equal(model.get('id'), 'yellow');
});
