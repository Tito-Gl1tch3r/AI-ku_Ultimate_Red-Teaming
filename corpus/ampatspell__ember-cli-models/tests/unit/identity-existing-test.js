import module from '../helpers/module-for-stores';
import { test } from '../helpers/qunit';
import Model from 'ember-cli-models/model/transient';

const Duck = Model.extend();
const Hamster = Model.extend();

module('identity-existing', {
  beforeEach() {
    this.register('model:duck', Duck);
    this.register('model:hamster', Hamster);
    this.database.model('duck', { id: 'yellow' });
    this.database.model('duck', { id: 'green' });
    this.database.model('hamster', { id: 'funny' });
  }
});

test('existing returns first model by fn', function(assert) {
  let model = this.database.existing('first', model => model.get('modelType') === 'duck');
  assert.equal(model.get('id'), 'yellow');
});

test('existing returns last model by fn', function(assert) {
  let model = this.database.existing('last', model => model.get('modelType') === 'duck');
  assert.equal(model.get('id'), 'green');
});

test('existing returns all models by fn', function(assert) {
  let models = this.database.existing('all', model => model.get('modelType') === 'duck');
  assert.deepEqual(models.mapBy('id'), [ 'yellow', 'green' ]);
});

test('existing returns first model by key value', function(assert) {
  let model = this.database.existing('first', { modelType: 'duck' });
  assert.equal(model.get('id'), 'yellow');
});

test('existing returns last model by key value', function(assert) {
  let model = this.database.existing('last', { modelType: 'duck' });
  assert.equal(model.get('id'), 'green');
});

test('existing returns all models by key value', function(assert) {
  let models = this.database.existing('all', { modelType: 'duck' });
  assert.deepEqual(models.mapBy('id'), [ 'yellow', 'green' ]);
});

test('existing returns first model by multiple key value', function(assert) {
  let model = this.database.existing('first', { modelType: 'duck', id: 'green' });
  assert.equal(model.get('id'), 'green');
});

test('existing returns last model by multiple key value', function(assert) {
  let model = this.database.existing('last', { modelType: 'duck', id: 'yellow' });
  assert.equal(model.get('id'), 'yellow');
});

test('existing returns all models by multiple key value', function(assert) {
  let models = this.database.existing('all', { modelType: 'duck', id: 'yellow' });
  assert.deepEqual(models.mapBy('id'), [ 'yellow' ]);
});

test('existing for store', function(assert) {
  let model = this.store.existing('first', model => model.get('modelType') === 'duck');
  assert.equal(model.get('id'), 'yellow');
});

test('existing for stores', function(assert) {
  let model = this.stores.existing('first', model => model.get('modelType') === 'duck');
  assert.equal(model.get('id'), 'yellow');
});
