import Mixin from '@ember/object/mixin';
import { A } from '@ember/array';
import { assert, isOneOf } from './util/assert';

const matchAllCallback = () => true;

const createSingleKeyValueCallback = (key, value) => model => model.get(key) === value;

const createKeyValuesCallback = object => {
  let keys = Object.keys(object);
  return model => {
    for(let i = 0; i < keys.length; i++) {
      let key = keys[i];
      let value = object[key];
      if(model.get(key) !== value) {
        return false;
      }
    }
    return true;
  };
}

const createCallback = arg => {
  if(typeof arg === 'function') {
    return arg;
  }
  if(typeof arg === 'object') {
    let keys = Object.keys(arg);
    if(keys.length === 1) {
      let key = keys[0];
      let value = arg[keys[0]];
      return createSingleKeyValueCallback(key, value);
    } else if(keys.length === 0) {
      return matchAllCallback;
    } else {
      return createKeyValuesCallback(arg);
    }
  }
  assert(`existing second argument must be filter function or object`, false);
}

export default Mixin.create({

  existing(type, arg) {
    isOneOf('type', type, [ 'first', 'last', 'all' ]);
    let identity = this.get('identity');
    let fn = createCallback(arg);
    if(type === 'first') {
      return identity.find(fn);
    } else {
      let found = A(identity.filter(fn));
      if(type === 'last') {
        return found.get('lastObject');
      }
      return found;
    }
  },

});
