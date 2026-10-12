import { computed } from '@ember/object';
import { A } from '@ember/array';

// usage:
//
// return destroyable('database', {
//   create(key) {
//     return new Thing(key);
//   },
//   get(internal) {
//     return internal.model(true);
//   },
//   destroy(internal) {
//     internal.destroy();
//   }
// });

const __ember_cli_models__ = '__ember_cli_models__';

const _get = owner => {
  return owner.willDestroy[__ember_cli_models__];
}

const _cache = (owner, create) => {
  if(!owner) {
    return;
  }
  if(!owner.willDestroy) {
    return;
  }
  let object = _get(owner);
  if(!object && create) {
    object = Object.create(null);
    let willDestroy = owner.willDestroy;
    owner.willDestroy = function() {
      let object = _get(owner);
      for(let key in object) {
        let { value, destroy } = object[key];
        destroy(value);
      }
      willDestroy.apply(owner, arguments);
    }
    owner.willDestroy[__ember_cli_models__] = object;
  }
  return object;
}

const _cacheFor = (owner, key) => {
  let cache = _cache(owner, false);
  if(!cache) {
    return {};
  }
  let value = cache[key];
  if(!value) {
    value = {};
  }
  return value;
}

const _destroyCached = (owner, key, value, destroy) => {
  let cache = _cache(owner);
  delete cache[key];
  destroy(value);
}

const _store = (owner, key, value, destroy) => {
  let cache = _cache(owner, true);
  cache[key] = { value, destroy };
}

export const cacheFor = (owner, key) => {
  let cache = _cache(owner);
  if(!cache) {
    return;
  }
  let hash = cache[key];
  if(!hash) {
    return;
  }
  return hash.value;
}

// ...deps, { reusable, create, get, destroy }
export default (...args) => {
  let opts = args.pop();
  args = A(args).compact();
  return computed(...args, function(key) {
    let { value, destroy } = _cacheFor(this, key);

    if(value && !opts.reusable.call(this, value)) {
      _destroyCached(this, key, value, destroy);
      value = null;
    }

    if(!value) {
      value = opts.create.call(this, key);
    }

    if(!value) {
      return;
    }

    _store(this, key, value, opts.destroy);

    return opts.get.call(this, value, key);
  });
}
