import EmberObject from '@ember/object';
import { run } from '@ember/runloop';
import module from '../helpers/module-for-stores';
import { test } from '../helpers/qunit';
import Transient from 'ember-cli-models/model/transient';
import Backed from 'ember-cli-models/model/backed';

const Duck = Transient.extend();
const Person = Backed.extend();
const Hamster = Backed.extend();

module('database-identity', {
  beforeEach() {
    this.register('model:duck', Duck);
    this.register('model:person', Person);
    this.register('model:hamster', Hamster);
  }
});

test('it exists', function(assert) {
  assert.ok(this.database.get('identity'));
});

test('new models are added', function(assert) {
  let model = this.database.model('duck');
  assert.ok(this.database.get('identity').includes(model));
});

test('destroyed models are removed', function(assert) {
  let identity = this.database.get('identity');
  let model = this.database.model('duck');
  assert.ok(identity.includes(model));
  run(() => model.destroy());
  assert.ok(!identity.includes(model));
});

test('pushed models are added', function(assert) {
  let adapter = this.database.get('adapter');
  let storage = EmberObject.create({ type: 'person' });
  let model = adapter.push([ storage ])[0].model;
  let internal = model._internal;
  assert.ok(model);

  let identity = this.database.get('identity');
  assert.ok(identity.includes(model));

  adapter.delete([ storage ]);
  assert.ok(!identity.includes(model));
  assert.ok(internal.model() === model);
});

test('recreated models are removed and added', function(assert) {
  let identity = this.database.get('identity');
  let adapter = this.database.get('adapter');
  let storage = EmberObject.create({ type: 'person' });

  let person = adapter.push([ storage ])[0].model;
  let internal = person._internal;

  assert.ok(person);
  assert.ok(identity.includes(person));

  run(() => person.set('storage.type', 'hamster'));

  assert.ok(!identity.includes(person));

  let hamster = internal.model(true);
  assert.ok(identity.includes(hamster));

  run(() => hamster.set('storage.type', 'person'));

  assert.ok(!identity.includes(person));
  assert.ok(identity.get('length'), 1);
  person = identity.objectAt(0);
  assert.ok(person._internal === internal);
});
