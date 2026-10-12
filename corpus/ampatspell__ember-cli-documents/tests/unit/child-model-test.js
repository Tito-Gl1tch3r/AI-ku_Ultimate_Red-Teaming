import { run } from '@ember/runloop';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import { Model, model } from 'documents';

const State = Model.extend({

  props: null,

  duck: model({
    create(owner) {
      return {
        type: 'duck',
        props: owner.get('props')
      };
    }
  })

});

const Duck = Model.extend();

module('child-model', {
  beforeEach() {
    this.register('model:state', State);
    this.register('model:duck', Duck);
  }
});

test('create child model has parent, doesnt inherit database or store', function(assert) {
  let state = this.db.model('state');
  assert.ok(state.get('store') === this.store);
  assert.ok(state.get('database') === this.db);
  let duck = state.get('duck');
  assert.ok(duck);
  assert.ok(!duck.get('store'));
  assert.ok(!duck.get('database'));
  assert.ok(duck._internal.parent === state._internal);
});

test('create child model with props', function(assert) {
  let state = this.db.model('state');
  assert.ok(state.get('store') === this.store);
  assert.ok(state.get('database') === this.db);
  state.set('props', { store: this.store, database: this.db });
  let duck = state.get('duck');
  assert.ok(duck);
  assert.ok(duck.get('store') == this.store);
  assert.ok(duck.get('database') === this.db);
  assert.ok(duck._internal.parent === state._internal);
});

test('destroy parent model destroys childs', function(assert) {
  let state = this.db.model('state');
  let duck = state.get('duck');
  run(() => state.destroy());
  assert.ok(duck.isDestroying);
});

test('destroy child remove it from parent', function(assert) {
  let state = this.db.model('state');
  let duck = state.get('duck');
  assert.ok(state._internal.models()[0] === duck._internal);
  run(() => duck.destroy());
  assert.ok(state._internal.models()[0] === undefined);
});
