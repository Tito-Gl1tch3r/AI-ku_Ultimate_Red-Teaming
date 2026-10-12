import { run } from '@ember/runloop';
import module from '../helpers/module-for-stores';
import { test } from '../helpers/qunit';
import Model from 'ember-cli-models/model/transient';
import { database, find } from 'ember-cli-models/computed';
import InternalFilterFirst from 'ember-cli-models/-private/model/internal-filter-first';
import { cacheFor } from 'ember-cli-models/-private/util/destroyable-computed';

const Duck = Model.extend({
  type: 'duck'
});

const Hamster = Model.extend({
  type: 'hamster'
});

module('computed-find', {
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
        duck: find('database', config)
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

test('no-proxy: find returns model', function(assert) {
  this.database.model('duck', { id: 'yellow' });
  let state = this.subject();
  let duck = state.get('duck');
  assert.ok(duck);
  assert.ok(Duck.detectInstance(duck));
});

test('no-proxy: find returns undefined', function(assert) {
  let state = this.subject();
  let duck = state.get('duck');
  assert.equal(duck, undefined);
});

test('no-proxy: find returns model later', function(assert) {
  let state = this.subject();
  let duck = state.get('duck');
  assert.equal(duck, undefined);
  this.database.model('duck', { id: 'yellow' });
  duck = state.get('duck');
  assert.ok(duck);
  assert.equal(duck.get('id'), 'yellow');
});

test('no-proxy: find returns undefined later', function(assert) {
  this.database.model('duck', { id: 'yellow' });
  let state = this.subject();
  let duck = state.get('duck');
  assert.ok(duck);
  assert.equal(duck.get('id'), 'yellow');

  run(() => duck.destroy());

  duck = state.get('duck');
  assert.equal(duck, undefined);
});

test('internal find exists', function(assert) {
  let state = this.subject();
  let duck = state.get('duck');
  assert.ok(!duck);

  let internal = cacheFor(state, 'duck');
  assert.ok(internal instanceof InternalFilterFirst);
});

test('find contains pre-existing first model', function(assert) {
  this.database.model('hamster', { id: 'cute' });
  this.database.model('duck', { id: 'yellow' });
  this.database.model('duck', { id: 'green' });

  let state = this.subject();
  let duck = state.get('duck');
  assert.equal(duck.get('id'), 'yellow');
});

test('find keeps first model', function(assert) {
  this.database.model('hamster', { id: 'cute' });
  this.database.model('duck', { id: 'yellow' });

  let state = this.subject();
  let duck = state.get('duck');
  assert.equal(duck.get('id'), 'yellow');

  this.database.model('duck', { id: 'green' });
  assert.equal(duck.get('id'), 'yellow');
});

test('find content is set on new model', function(assert) {
  let state = this.subject();
  let duck;

  duck = state.get('duck');
  assert.ok(!duck);

  this.database.model('hamster', { id: 'cute' });

  duck = state.get('duck');
  assert.ok(!duck);

  this.database.model('duck', { id: 'green' });

  duck = state.get('duck');
  assert.equal(duck.get('id'), 'green');
});

test('find content is unset on model destroy', function(assert) {
  let state = this.subject();
  let duck;

  duck = state.get('duck');
  assert.ok(!duck);

  let model = this.database.model('duck', { id: 'green' });

  duck = state.get('duck');
  assert.equal(duck.get('id'), 'green');

  run(() => model.destroy());

  duck = state.get('duck');
  assert.ok(!duck);
});

test('find content is unset on model prop change', function(assert) {
  let state = this.subject();
  let duck;

  duck = state.get('duck');
  assert.equal(duck, undefined);

  let model = this.database.model('duck', { id: 'green' });

  duck = state.get('duck');
  assert.equal(duck.get('id'), 'green');

  model.set('type', 'hamster');

  duck = state.get('duck');
  assert.equal(duck, undefined);
});

test('find content is replaced with another model on current prop change', function(assert) {
  let state = this.subject();
  let duck;

  duck = state.get('duck');
  assert.equal(duck, undefined);

  let yellow = this.database.model('duck', { id: 'yellow' });
  this.database.model('duck', { id: 'green' });

  duck = state.get('duck');
  assert.equal(duck.get('id'), 'yellow');

  yellow.set('type', 'hamster');

  duck = state.get('duck');
  assert.equal(duck.get('id'), 'green');
});

test('find content is replaced with another model on owner prop change', function(assert) {
  let state = this.subject();
  let duck;

  duck = state.get('duck');
  assert.equal(duck, undefined);

  this.database.model('hamster', { id: 'cute' });
  this.database.model('duck', { id: 'green' });

  duck = state.get('duck');
  assert.equal(duck.get('id'), 'green');

  state.set('modelType', 'hamster');

  duck = state.get('duck');
  assert.equal(duck.get('id'), 'cute');
});

test('find content is removed on owner prop change', function(assert) {
  let state = this.subject();
  let duck;

  duck = state.get('duck');
  assert.equal(duck, undefined);

  this.database.model('hamster', { id: 'cute' });
  this.database.model('duck', { id: 'green' });

  duck = state.get('duck');
  assert.equal(duck.get('id'), 'green');

  state.set('modelType', 'foobar');

  duck = state.get('duck');
  assert.equal(duck, undefined);
});

test('find content is replaced with another model on owner prop change', function(assert) {
  let state = this.subject();
  let prop;

  prop = state.get('duck');
  assert.equal(prop, undefined);

  this.database.model('hamster', { id: 'cute' });
  let duck = this.database.model('duck', { id: 'green' });

  prop = state.get('duck');
  assert.equal(prop.get('id'), 'green');

  state.set('modelType', 'hamster');

  prop = state.get('duck');
  assert.equal(prop.get('id'), 'cute');

  duck.set('type', 'random');

  prop = state.get('duck');
  assert.equal(prop.get('id'), 'cute');

  state.set('modelType', 'random');

  prop = state.get('duck');
  assert.equal(prop.get('id'), 'green');
});

test('find internal is replaced on database change', function(assert) {
  let first = this.store.database('main').model('duck', { id: 'cute' });
  let second = this.store.database('second').model('duck', { id: 'cute' });

  let state = this.subject();
  let duck;

  duck = state.get('duck');
  assert.ok(duck === first);

  state.set('database', this.store.database('second'));

  duck = state.get('duck');
  assert.ok(duck === second);
});
