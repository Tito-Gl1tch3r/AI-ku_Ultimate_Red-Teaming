import { assign, merge } from '@ember/polyfills';
import { A } from '@ember/array';
import { assert } from '@ember/debug';

export default opts => {
  opts = merge({ defaults: {}, computed: [], extend: null }, opts);
  assert(`opts.extend must be function not ${opts.extend}`, typeof opts.extend === 'function');

  const storedKeys = A(Object.keys(opts.defaults));
  const keys = [ ...opts.computed, ...storedKeys ];

  class BaseState {

    constructor() {
      assign(this, opts.defaults);
    }

    set(props, changed) {
      let any = false;
      for(let key in props) {
        let value = props[key];
        if(this[key] !== value) {
          this[key] = value;
          changed(key);
          any = true;
        }
      }
      if(any) {
        changed('state');
      }
    }

    get() {
      return keys.reduce((obj, key) => {
        obj[key] = this[key];
        return obj;
      }, {});
    }

  }

  const State = opts.extend(BaseState, opts);

  return { keys, State };
};
