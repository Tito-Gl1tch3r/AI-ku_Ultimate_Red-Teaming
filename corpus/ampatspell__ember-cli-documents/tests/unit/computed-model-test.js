import EmberObject from '@ember/object';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import { Model, model } from 'documents';

const Hamster = EmberObject.extend({});

const Duck = Model.extend({});

const docModel = opts => model({
  owner: [ opts.doc ],
  create(owner) {
    let doc = owner.get(opts.doc);
    let { store, database } = owner.getProperties('store', 'database');
    return {
      type: opts.type || 'duck',
      props: {
        doc,
        store,
        database
      }
    };
  }
});

module('computed-model', {
  beforeEach() {
    this.register('model:duck', Duck);
    this.register('model:hamster', Hamster);
    this.create = (opts={}) => {
      let Subject = EmberObject.extend({
        doc: opts.doc,
        prop: docModel({ doc: 'doc', type: opts.type })
      });
      return Subject.create({ store: this.store, database: this.db }, this.ownerInjection);
    };
  }
});

test('it exists', async function(assert) {
  let subject = this.create();
  assert.ok(subject);
});

test('model is created', async function(assert) {
  let subject = this.create();
  let model = subject.get('prop');
  assert.ok(Duck.detectInstance(model));
});

test('model has passed properties', async function(assert) {
  let doc = {};
  let subject = this.create({ doc });
  let model = subject.get('prop');
  assert.equal(model.get('doc'), doc);
  assert.equal(model.get('store'), this.store);
  assert.equal(model.get('database'), this.db);
});

test('requires model type to be model', function(assert) {
  let subject = this.create({ doc: {}, type: 'hamster' });
  try {
    subject.get('prop');
    assert.ok(false, 'should throw');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "model for name 'hamster' must extend Model"
    });
  }
});
