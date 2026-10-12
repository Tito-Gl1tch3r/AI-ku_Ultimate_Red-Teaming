import EmberObject from '@ember/object';
import { assign } from '@ember/polyfills';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import { Models, Model } from 'documents';

const Ponyhof = Models.extend();
const Duck = Model.extend();

module('internal-models', {
  beforeEach() {
    this.register('model:ponyhof', Ponyhof);
    this.register('model:duck', Duck);
    this.source = [
      EmberObject.create({ id: 'yellow' }),
      EmberObject.create({ id: 'green' })
    ];
    this.defaults = {
      type: 'ponyhof',
      source: this.source,
      props:  { ok: true, database: this.db },
      model: {
        observe: [ 'id' ],
        create(doc, models) {
          let { store, database } = models.getProperties('store', 'database');
          return {
            type: 'duck',
            props: { doc, store, database }
          }
        }
      },
      _parent: null
    };
    this.create = opts => this.store._createInternalModels(assign({}, this.defaults, opts));
  }
});

test('create succeeds', function(assert) {
  let internal = this.create();
  assert.ok(internal);

  let model = internal.model(true);
  assert.ok(Ponyhof.detectInstance(model));
  assert.equal(model.get('ok'), true);
  assert.equal(model.get('store'), this.store);
  assert.equal(model.get('database'), this.db);

  assert.equal(model.get('length'), 2);

  let yellow = model.objectAt(0);
  assert.ok(Duck.detectInstance(yellow));
  assert.equal(yellow.get('doc'), this.source.objectAt(0));
  assert.equal(yellow.get('store'), this.store);
  assert.equal(yellow.get('database'), this.db);
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

test('models has ref', function(assert) {
  let internal = this.create();
  let models = internal.model(true);
  assert.ok(models.objectAt(0)._internal._ref === this.source[0]);
});
