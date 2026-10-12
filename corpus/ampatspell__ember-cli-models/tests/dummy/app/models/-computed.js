import { assign } from '@ember/polyfills';
import { find as _find, filter as _filter, model as _model } from 'ember-cli-models/computed';
import { prop, getKey, getValue } from 'ember-cli-models/prop';

// opts: { store, database }
const sourceFromOptions = (owner, stores, opts) => {
  let { store, database } = opts;
  return stores.database(store, database);
}

// opts: { store, database, type }
export const findByType = opts => {
  return _find(function(owner, stores) {
    return {
      source: sourceFromOptions(owner, stores, opts),
      model: [ 'modelType' ],
      owner: [ getKey(opts.type) ],
      matches(model, owner) {
        let type = getValue(opts.type, owner);
        return model.get('modelType') === type;
      }
    };
  });
}

// opts: { store, database, type, new }
export const filterByType = opts => {
  return _filter(function(owner, stores) {
    return {
      source: sourceFromOptions(owner, stores, opts),
      owner: [ getKey(opts.type), getKey(opts.new) ],
      model: [ 'modelType', 'isNew' ],
      matches(model, owner) {
        let isNew = getValue(opts.new, owner);
        if(isNew !== undefined && model.get('isNew') !== isNew) {
          return;
        }
        let type = getValue(opts.type, owner);
        return model.get('modelType') === type;
      }
    };
  });
}

// opts: { store, database }
// fn: { name, props }
export const model = (opts, fn) => {
  return _model(function(owner, stores) {
    let hash = fn.call(this, ...arguments);
    if(!hash) {
      return;
    }
    let database = sourceFromOptions(owner, stores, opts);
    return assign({ database }, hash);
  });
}

// Lookups models by ids which are included in `storage.{key}` array
// opts: { store, database, key, type }
export const hasManyPersisted = opts => {
  return _filter(function(owner, stores) {
    return {
      source: sourceFromOptions(owner, stores, opts),
      owner: [ `storage.${getKey(opts.key)}.[]`, getKey(opts.type) ],
      model: [ 'storage.id' ],
      matches(model, owner) {
        if(model.get('modelType') !== getValue(opts.type, owner)) {
          return;
        }
        let array = owner.get(`storage.${getValue(opts.key, owner)}`);
        if(!array) {
          return;
        }
        return array.includes(model.get('storage.id'));
      }
    };
  });
}

// Lookups models which has owner included in `opts.key` array
// opts: { store, database, key, type }
export const manyToManyInverse = opts => {
  return _filter(function(owner, stores) {
    return {
      source: sourceFromOptions(owner, stores, opts),
      owner: [ getKey(opts.type) ],
      model: [ 'modelType', `${getKey(opts.key)}.[]` ],
      matches(model, owner) {
        if(model.get('modelType') !== getValue(opts.type, owner)) {
          return;
        }
        let array = model.get(getValue(opts.key, owner));
        return array.includes(owner);
      }
    }
  });
}

// database: { store, database }
export const withDatabase = database => {
  const mergeDatabase = opts => assign({}, database, opts);
  return {
    prop,
    findByType:        opts => findByType(mergeDatabase(opts)),
    filterByType:      opts => filterByType(mergeDatabase(opts)),
    model:             fn   => model(mergeDatabase(), fn),
    hasManyPersisted:  opts => hasManyPersisted(mergeDatabase(opts)),
    manyToManyInverse: opts => manyToManyInverse(mergeDatabase(opts))
  };
}
