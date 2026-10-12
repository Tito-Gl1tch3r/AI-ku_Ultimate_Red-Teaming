import destroyable from '../util/destroyable-computed';
import { getStores } from '../util/get-stores';
import { isFunction, isObject, isArray, isArrayArrayProxyOrHasIdentity } from '../util/assert';
import { A } from '@ember/array';

const invoke = (owner, fn, stores) => fn.call(owner, owner, stores);

// {
//   source: <database|store|stores|...>,
//   owner: [ 'type' ],
//   model: [ 'type' ],
//   matches(model, owner) {
//     return model.get('type') === owner.get('type');
//   }
// }
//
// to
//
// {
//   source: { object, observe, matches }
//   owner: { object, observe }
// }

const dependencies = (object, keys) => object.getProperties(keys);

const validate = (object, key, result, keys) => {
  isObject('result', result);

  let { source, owner, model, matches } = result;

  isArrayArrayProxyOrHasIdentity('result.source', source);
  isArray('result.owner', owner);
  isArray('result.model', model);
  isFunction('result.matches', matches);

  owner = A(owner).compact();
  model = A(model).compact();

  return {
    source: {
      object:  source,
      observe: model,
      matches: matches
    },
    owner: {
      key: key,
      object: object,
      observe: owner
    },
    deps: dependencies(object, keys)
  };
};

const reusable = (prev, curr) => {
  for(let key in prev) {
    if(prev[key] !== curr[key]) {
      return false;
    }
  }
  return true;
}

const destroy = internal => internal.destroy();

const base = (args, { create, get }) => {
  let fn = args.pop();
  isFunction('last argument', fn);
  return destroyable(...args, {
    reusable(internal) {
      let prev = internal.opts.deps;
      let curr = dependencies(this, args);
      return reusable(prev, curr);
    },
    create(key) {
      let stores = getStores(this);
      let result = invoke(this, fn, stores);
      if(!result) {
        return;
      }
      let opts = validate(this, key, result, args);
      let manager = stores._context.internalFilterManager;
      return create(manager, opts);
    },
    get,
    destroy
  });
};

export const find = (...args) => base(args, {
  create: (manager, args) => manager.internalFirst(args),
  get: internal => internal.content(true)
});

export const filter = (...args) => base(args, {
  create: (manager, args) => manager.internalFind(args),
  get: internal => internal.model(true)
});
