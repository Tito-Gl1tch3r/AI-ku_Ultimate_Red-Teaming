import { run } from '@ember/runloop';
import module from '../helpers/module-for-stores';
import { test } from '../helpers/qunit';
import Model from 'ember-cli-models/model/transient';
import { database, filter } from 'ember-cli-models/computed';
import FilterFind from 'ember-cli-models/-private/model/filter-find';

const Duck = Model.extend({
  type: 'duck'
});

const Hamster = Model.extend({
  type: 'hamster'
});

module('computed-filter', {
  beforeEach() {
    this.register('model:duck', Duck);
    this.register('model:hamster', Hamster);
    this.subject = () => {

      let config = function() {
        return  {
          source: this.get('database'),
          owner: [ 'modelType' ],
          model: [ 'type' ],
          matches(model, owner) {
            return model.get('type') === owner.get('modelType');
          }
        };
      };

      this.register('model:state', Model.extend({
        database: database(),
        modelType: 'duck',
        ducks: filter('database', config),
      }));

      return this.database.model('state');
    };
  }
});

test('state exists', function(assert) {
  let state = this.subject();
  assert.ok(state);
  assert.ok(state.get('database'));
  let one = this.database.model('duck', { id: 'one' });
  let identity = this.database.get('identity');
  assert.ok(identity.includes(one));
});

test('filter exists', function(assert) {
  let state = this.subject();
  let ducks = state.get('ducks');
  assert.ok(ducks);
  assert.ok(FilterFind.detectInstance(ducks));

  let internal = ducks._internal;
  assert.ok(internal);
  assert.ok(internal._model === ducks);

  run(() => ducks.destroy());

  assert.ok(internal.isDestroyed);
  assert.ok(!internal._model);
});

test('filter contains pre-existing models', function(assert) {
  this.database.model('duck', { id: 'yellow' });
  this.database.model('duck', { id: 'green' });
  this.database.model('hamster', { id: 'cute' });
  assert.deepEqual(this.database.get('identity').mapBy('id'), [ 'yellow', 'green', 'cute' ]);

  let state = this.subject();
  let ducks = state.get('ducks');
  assert.deepEqual(ducks.mapBy('id'), [ 'yellow', 'green' ]);
});

test('filter adds newly created models', function(assert) {
  let state = this.subject();
  let ducks = state.get('ducks');
  assert.deepEqual(ducks.mapBy('id'), []);

  this.database.model('duck', { id: 'yellow' });
  assert.deepEqual(ducks.mapBy('id'), [ 'yellow' ]);

  this.database.model('hamster', { id: 'cute' });
  assert.deepEqual(ducks.mapBy('id'), [ 'yellow' ]);

  this.database.model('duck', { id: 'green' });
  assert.deepEqual(ducks.mapBy('id'), [ 'yellow', 'green' ]);
});

test('filter removes destroyed models', function(assert) {
  let state = this.subject();
  let ducks = state.get('ducks');
  assert.deepEqual(ducks.mapBy('id'), []);

  let yellow = this.database.model('duck', { id: 'yellow' });
  assert.deepEqual(ducks.mapBy('id'), [ 'yellow' ]);

  run(() => yellow.destroy());

  assert.deepEqual(ducks.mapBy('id'), []);
});

test('filter removes updated models', function(assert) {
  let state = this.subject();
  let ducks = state.get('ducks');
  assert.deepEqual(ducks.mapBy('id'), []);

  let yellow = this.database.model('duck', { id: 'yellow' });
  assert.deepEqual(ducks.mapBy('id'), [ 'yellow' ]);

  yellow.set('type', 'foof');

  assert.deepEqual(ducks.mapBy('id'), []);
});

test('filter is remached on owner prop change', function(assert) {
  this.database.model('duck', { id: 'yellow' });
  this.database.model('duck', { id: 'green' });
  this.database.model('hamster', { id: 'cute' });

  let state = this.subject();
  let ducks = state.get('ducks');

  assert.deepEqual(ducks.mapBy('id'), [ 'yellow', 'green' ]);

  state.set('modelType', 'hamster');

  assert.deepEqual(ducks.mapBy('id'), [ 'cute' ]);
});
