import module from '../helpers/module-for-stores';
import { test } from '../helpers/qunit';
import Stores from 'ember-cli-models/stores';
import Store from 'ember-cli-models/store';
import Database from 'ember-cli-models/database';
import StoreAdapter from 'ember-cli-models/adapter/store';
import DatabaseAdapter from 'ember-cli-models/adapter/database';

module('adapter-extend', {
  beforeEach() {
    this.create = (adapters) => {
      const StoresImpl = Stores.extend({
        storeOptionsForIdentifier(identifier) {
          return {
            adapter: identifier
          };
        }
      });

      for(let key in adapters) {
        let value = adapters[key];
        this.register(`models:stack/${key}/store`, value.Store);
        this.register(`models:stack/${key}/store/adapter`, value.StoreAdapter);
        this.register(`models:stack/${key}/database`, value.Database);
        this.register(`models:stack/${key}/database/adapter`, value.DatabaseAdapter);
      }

      this.register('models:stores', StoresImpl);
      return this.lookup('models:stores');
    };
  }
});

test('it exists', function(assert) {
  let stores = this.create({
    local: {
      Store: Store.extend({ type: 'local-store' }),
      StoreAdapter: StoreAdapter.extend({ type: 'local-store-adapter' }),
      Database: Database.extend({ type: 'local-database' }),
      DatabaseAdapter: DatabaseAdapter.extend({ type: 'local-database-adapter' })
    },
    remote: {
      Store: Store.extend({ type: 'remote-store' }),
      StoreAdapter: StoreAdapter.extend({ type: 'remote-store-adapter' }),
      Database: Database.extend({ type: 'remote-database' }),
      DatabaseAdapter: DatabaseAdapter.extend({ type: 'remote-database-adapter' })
    }
  });

  let local = stores.store('local');
  assert.equal(local.get('type'), 'local-store');

  let localAdapter = local.get('adapter');
  assert.equal(localAdapter.get('type'), 'local-store-adapter');

  let localMain = local.database('main');
  assert.equal(localMain.get('type'), 'local-database');
  assert.equal(localMain.get('identifier'), 'main');

  let localMainAdapter = localMain.get('adapter');
  assert.equal(localMainAdapter.get('type'), 'local-database-adapter');

  //

  let remote = stores.store('remote');
  assert.equal(remote.get('type'), 'remote-store');

  let remoteAdapter = remote.get('adapter');
  assert.equal(remoteAdapter.get('type'), 'remote-store-adapter');

  let remoteMain = remote.database('main');
  assert.equal(remoteMain.get('type'), 'remote-database');
  assert.equal(remoteMain.get('identifier'), 'main');

  let remoteMainAdapter = remoteMain.get('adapter');
  assert.equal(remoteMainAdapter.get('type'), 'remote-database-adapter');
});
