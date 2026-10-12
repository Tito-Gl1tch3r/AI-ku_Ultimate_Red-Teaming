import { computed } from '@ember/object';
import { isModel } from '../util/is-instance';
import { getStores, getStore, getDatabase } from '../util/get-stores';
import { assert } from '../util/assert';

const modelToInternal = model => {
  if(!isModel(model)) {
    return { isModel: false };
  }
  let internal = model._internal;
  return { isModel: true, internal };
};

export const stores = () => computed(function() {
  let { isModel, internal } = modelToInternal(this);
  if(isModel) {
    if(internal) {
      return internal.stores;
    }
  } else {
    return getStores(this);
  }
});

export const store = (...args) => computed(function() {
  let { isModel, internal } = modelToInternal(this);
  if(isModel) {
    if(internal) {
      if(args.length === 1) {
        let [ storeIdentifier ] = args;
        return internal.stores.store(storeIdentifier);
      } else {
        return internal.store;
      }
    }
  } else {
    if(args.length === 1) {
      let [ storeIdentifier ] = args;
      return getStore(this, storeIdentifier);
    } else {
      assert(`store identifier is required`, false);
    }
  }
});

export const database = (...args) => computed(function() {
  let { isModel, internal } = modelToInternal(this);
  if(isModel) {
    if(internal) {
      if(args.length === 2) {
        let [ storeIdentifier, databaseIdentifier ] = args;
        return internal.stores.database(storeIdentifier, databaseIdentifier);
      } else if(args.length === 1) {
        let [ databaseIdentifier ] = args;
        return internal.store.database(databaseIdentifier);
      } else {
        return internal.database;
      }
    }
  } else {
    if(args.length === 2) {
      let [ storeIdentifier, databaseIdentifier ] = args;
      return getDatabase(this, storeIdentifier, databaseIdentifier);
    } else {
      assert(`store and database identifiers are required`, false);
    }
  }
});
