import { assign } from '@ember/polyfills';
import { typeOf } from '@ember/utils';
import { prop, find, first } from 'documents';
import { isBlank } from 'documents/util/string';

export const firstById = opts => {
  opts = assign({ database: 'database', owner: [], document: [], id: prop('id') }, opts);

  let _id = prop.wrap(opts.id);
  let _matches = opts.matches;

  return first(assign(opts, {
    owner: [ ...opts.owner, _id.key() ],
    document: [ ...opts.document, 'id' ],
    query(owner) {
      let id = _id.value(owner);
      if(isBlank(id)) {
        return;
      }
      return { id };
    },
    matches(doc, owner) {
      if(_matches && !_matches(doc, owner)) {
        return;
      }
      let id = _id.value(owner);
      if(!id) {
        return;
      }
      return doc.get('id') === id;
    }
  }));
};

export const findByIds = opts => {
  opts = assign({ owner: [], document:  [], ids: prop('ids') }, opts);

  let _ids = prop.wrap(opts.ids);
  let _matches = opts.matches;

  let _owner;
  let key = _ids.key();
  if(key) {
    _owner = `${key}.[]`;
  }

  const _getIds = owner => {
    let ids = opts.ids.value(owner);
    if(!ids || ids.length === 0) {
      return;
    }
    return ids;
  };

  return find(assign(opts, {
    owner: [ ...opts.owner, _owner ],
    document: [ ...opts.document, 'id' ],
    query(owner) {
      let keys = _getIds(owner);
      if(!keys) {
        return;
      }
      return { all: true, keys };
    },
    matches(doc, owner) {
      if(_matches && !_matches(doc, owner)) {
        return;
      }
      let ids = _getIds(owner);
      if(!ids) {
        return;
      }
      let id = doc.get('id');
      return ids.includes(id);
    }
  }));
};

export const isNewMixin = opts => {
  opts = assign({ owner: [], document: [] }, opts);

  let _new = prop.wrap(opts.new);
  let _matches = opts.matches;

  return assign(opts, {
    owner: [ ...opts.owner, _new.key() ],
    document: [ ...opts.document, 'isNew' ],
    matches(doc, owner) {
      if(_matches && !_matches(doc, owner)) {
        return;
      }
      let value = _new.value(owner);
      let type = typeOf(value);
      if(type === 'null' || type === 'undefined') {
        return true;
      }
      return doc.get('isNew') === !!value;
    }
  });
};
