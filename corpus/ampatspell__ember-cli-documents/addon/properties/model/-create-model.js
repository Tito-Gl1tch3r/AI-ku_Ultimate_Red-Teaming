import { A } from '@ember/array';
import { merge } from '@ember/polyfills';
import { getOwner } from '@ember/application';
import destroyable from '../-destroyable';
import InternalModel from '../../document/internal/model';
import { withDefinition } from '../-meta';
import { assert, isString, isArray, isFunction, isObject } from '../../util/assert';

const toInternalModel = owner => {
  let internal = owner._internal;
  if(internal instanceof InternalModel) {
    return internal;
  }
  return null;
}

const invokeCreate = (owner, opts) => {
  isFunction('create', opts.create);
  let result = opts.create(owner);

  if(result === null) {
    return { type: null };
  }

  if(!result) {
    return {};
  }

  if(typeof result === 'string') {
    return { type: result };
  } else {
    isObject('create function result', result);
  }

  let { type, props } = result;

  if(type) {
    isString('type in create function result', type);
  }
  if(props) {
    isObject('props in create function result', props);
  }

  return result;
}

export default factory => opts => {
  opts = merge({ store: 'store', database: 'database', owner: [], document: [] }, opts);
  isArray('owner', opts.owner);
  let owner = A(opts.owner).compact();
  return withDefinition(destroyable(...owner, {
    create() {
      let owner = getOwner(this);
      assert(`owner injection is required for ${this}`, !!owner);

      let stores = owner.lookup('documents:stores');

      let parent = toInternalModel(this);
      let definition = invokeCreate(this, opts);

      return factory.create(stores, opts, definition, parent);
    }
  }), opts).readOnly();
};
