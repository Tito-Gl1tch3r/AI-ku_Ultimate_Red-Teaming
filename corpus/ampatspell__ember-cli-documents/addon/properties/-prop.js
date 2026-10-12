import EmberObject, { get } from '@ember/object';
import { guidFor } from '@ember/object/internals';
import { capitalize } from '@ember/string';
import Ember from 'ember';

const {
  Copyable
} = Ember;

const Base = EmberObject.extend(Copyable, {

  copy() {
    return this;
  },

  toString() {
    let type = capitalize(this.get('type'));
    let guid = guidFor(this);
    let value = this.get('_value');
    return `<${type}:${guid}:${value}>`;
  }

});

const Property = Base.extend({

  type: 'property',

  key() {
    return this.get('_value');
  },

  value(arg) {
    return get(arg, this.get('_value'));
  }

});

const Static = Base.extend({

  type: 'static',

  key() {
  },

  value() {
    return this.get('_value');
  }

});

const builder = fn => value => {
  if(Base.detectInstance(value)) {
    return value;
  }
  return fn(value);
}

export const prop = builder(_value => Property.create({ _value }));
export const wrap = builder(_value => Static.create({ _value }));

prop.wrap = wrap;

/*

const byId = first.extend(opts => {
  opts = merge({ id: prop('id') }, opts);
  let id_ = prop.wrap(opts.id);
  return {
    owner: [ id_.key() ],
    query(owner) {
      let id = id_.value(owner);
      ...
    },
    ...
  };
});

*/
