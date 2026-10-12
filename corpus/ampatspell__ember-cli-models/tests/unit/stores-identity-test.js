import module from '../helpers/module-for-stores';
import { test } from '../helpers/qunit';
import { run } from '@ember/runloop';
import Model from 'ember-cli-models/model/transient';

const Duck = Model.extend();

module('stores-identity', {
  beforeEach() {
    this.register('model:duck', Duck);
  }
});

test('it exists', function(assert) {
  let identity = this.stores.get('identity');
  assert.ok(identity);
});

test('models are added', function(assert) {
  let identity = this.stores.get('identity');
  assert.equal(identity.get('length'), 0);
  let model = this.database.model('duck');
  assert.equal(identity.get('length'), 1);
  assert.ok(identity.includes(model));
});

test('models are removed', function(assert) {
  let identity = this.stores.get('identity');
  assert.equal(identity.get('length'), 0);

  let model = this.database.model('duck');

  assert.equal(identity.get('length'), 1);
  assert.ok(identity.includes(model));

  run(() => model.destroy());

  assert.equal(identity.get('length'), 0);
  assert.ok(!identity.includes(model));
});

test('existing models are present on init', function(assert) {
  let model = this.database.model('duck');

  let databaseIdentity = this.database.get('identity');
  assert.equal(databaseIdentity.get('length'), 1);
  assert.ok(databaseIdentity.indexOf(model) === 0);

  let storeIdentity = this.store.get('identity');
  assert.equal(storeIdentity.get('length'), 1);
  assert.ok(storeIdentity.indexOf(model) === 0);

  let storesIdentity = this.stores.get('identity');
  assert.equal(storesIdentity.get('length'), 1);
  assert.ok(storesIdentity.indexOf(model) === 0);
});
