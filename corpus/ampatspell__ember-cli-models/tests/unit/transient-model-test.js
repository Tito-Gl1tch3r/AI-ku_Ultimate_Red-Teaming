import { run } from '@ember/runloop';
import module from '../helpers/module-for-stores';
import { test } from '../helpers/qunit';
import Model from 'ember-cli-models/model/transient';

const Duck = Model.extend();

module('transient-model', {
  beforeEach() {
    this.register('model:duck', Duck);
  }
});

test('model is created with internal model', function(assert) {
  let model = this.database.model('duck');
  assert.ok(model);
  assert.ok(model._internal);
  assert.ok(model._internal._model === model);
  assert.ok(this.identity.all.includes(model._internal));
  assert.ok(!this.identity.deleted.includes(model._internal));
});

test('model destroy unsets internalModel._model', function(assert) {
  let model = this.database.model('duck');
  let internal = model._internal;
  assert.ok(internal._model === model);
  assert.ok(this.identity.all.includes(model._internal));
  run(() => model.destroy());
  assert.ok(internal._model === null);
  assert.ok(!this.identity.all.includes(model._internal));
  assert.ok(!this.identity.deleted.includes(model._internal));
});

test('storage is not set', function(assert) {
  let model = this.database.model('duck');
  assert.ok(!model._internal.storage);
  assert.ok(!model.get('storage'));
});

test('model is created with props', function(assert) {
  let model = this.database.model('duck', { id: 'duck:yellow' });
  let internal = model._internal;
  assert.ok(model);
  assert.ok(internal);
  assert.equal(model.get('id'), 'duck:yellow');
});
