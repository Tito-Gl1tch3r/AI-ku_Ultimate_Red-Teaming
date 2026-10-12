import { assign } from '@ember/polyfills';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import { Stores } from 'documents';

module('store-database-name-mapping', {
  beforeEach() {
    let opts = assign({}, this.config.store, {
      databaseNameForIdentifier(identifier) {
        if(identifier === 'main') {
          return 'ember-cli-documents';
        }
      }
    });
    this.registerStores(Stores.extend({
      storeOptionsForIdentifier(identifier) {
        if(identifier === 'default') {
          return opts;
        }
      }
    }));
  }
});

test('lookup by identifier', function(assert) {
  let db = this.store.database('main');
  assert.equal(db.get('identifier'), 'main');
  assert.equal(db.get('name'), 'ember-cli-documents');
  assert.equal(db.get('documents.name'), 'ember-cli-documents');
});

test('invalid identifier', function(assert) {
  try {
    this.store.database('foof');
    assert.ok(false, 'should throw');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "database name must be string"
    });
  }
});
