import { assign } from '@ember/polyfills';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import { Model } from 'documents';

const Duck = Model.extend();

module('internal-model', {
  beforeEach() {
    this.register('model:duck', Duck);
    this.defaults = {
      type: 'duck',
      props:  { ok: true, database: this.db },
      _parent: null,
      _ref: null
    };
    this.create = opts => this.store._createInternalModel(assign({}, this.defaults, opts));
  }
});

test('create succeeds', function(assert) {
  let internal = this.create();
  assert.ok(internal);

  let model = internal.model(true);
  assert.ok(Duck.detectInstance(model));
  assert.equal(model.get('ok'), true);
  assert.equal(model.get('store'), this.store);
  assert.equal(model.get('database'), this.db);
});

test('create with parent', function(assert) {
  assert.expect(2);
  let _parent = {
    _registerChildModel() {
      assert.ok(true);
    }
  };
  let internal = this.create({ _parent });
  assert.ok(internal.parent === _parent);
});

test('create with ref', function(assert) {
  let _ref = {};
  let internal = this.create({ _ref });
  assert.ok(internal._ref === _ref);
});
