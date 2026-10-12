import EmberObject from '@ember/object';
import { assign } from '@ember/polyfills';
import module from '../helpers/module-for-stores';
import { test } from '../helpers/qunit';
import Model from 'ember-cli-models/model/backed';
import StoreAdapter from 'ember-cli-models/adapter/store';
import DatabaseAdapter from 'ember-cli-models/adapter/database';

const Duck = Model.extend();

const MockStoreAdapter = StoreAdapter.extend();

const MockDatabaseAdapter = DatabaseAdapter.extend({

  modelDefinitionForStorage() {
    return {
      observe: [ 'type' ],
      type: storage => storage.get('type')
    };
  },

  _storage(modelName, data) {
    return EmberObject.create(assign({}, data, { type: modelName }));
  },

  async find(opts) {
    if(opts.all === true) {
      return [ this._storage('duck', { id: 'duck:yellow' }) ];
    } else if(opts.id) {
      return this._storage('duck', { id: opts.id });
    }
    throw new Error('unsupported query');
  },

  async first(opts) {
    if(opts.id) {
      return this._storage('duck', { id: opts.id });
    }
    throw new Error('unsupported query');
  }

});

module('database-find', {
  beforeEach() {
    this.register('model:duck', Duck);
    this.registerAdapters('mock', MockStoreAdapter, MockDatabaseAdapter);
    this.adapter = 'mock';
  }
});

test('find', async function(assert) {
  let models = await this.database.find({ all: true });
  assert.ok(models);
  assert.ok(models.get('length') === 1);
  let duck = models.objectAt(0);
  assert.equal(duck.get('storage.id'), 'duck:yellow');
  assert.ok(this.database.get('identity.length'), 1);
});

test('first', async function(assert) {
  let duck = await this.database.first({ id: 'duck:yellow' });
  assert.ok(duck);
  assert.equal(duck.get('storage.id'), 'duck:yellow');
  assert.ok(this.database.get('identity.length'), 1);
});

test('find one', async function(assert) {
  let duck = await this.database.find({ id: 'duck:yellow' });
  assert.ok(duck);
  assert.equal(duck.get('storage.id'), 'duck:yellow');
  assert.ok(this.database.get('identity.length'), 1);
});
