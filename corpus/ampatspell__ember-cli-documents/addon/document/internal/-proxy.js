import { merge } from '@ember/polyfills';
import { A } from '@ember/array';
import Base from './-base';
import { isFunction, isArray, isBoolean } from 'documents/util/assert';

export default class BaseProxyInternal extends Base {

  constructor(store, database, owner, opts) {
    super();
    this.store = store;
    this.database = database;
    this.owner = owner;
    this.opts = this._normalizeOptions(opts);
    this._filter = null;
    this._loader = null;
  }

  _normalizeOptions(opts) {
    opts = merge({ autoload: true, owner: [], document: [] }, opts);
    let { autoload, query, matches, owner, document } = opts;
    isBoolean('autoload', autoload);
    isFunction('query', query);
    isFunction('matches', matches);
    isArray('owner', owner);
    isArray('document', document);
    owner = A(owner).compact();
    document = A(document).compact();
    return { autoload, owner, document, matches, query };
  }

  //

  _createFilter() {
    let { owner, document, matches } = this.opts;
    return this.database._createInternalFilter(this.owner, { owner, document, matches });
  }

  filter(create) {
    let filter = this._filter;
    if(!filter && create) {
      filter = this._createFilter();
      this._filter = filter;
    }
    return filter;
  }

  //

  loader(create) {
    let loader = this._loader;
    if(!loader && create) {
      loader = this._createLoader();
      this._loader = loader;
    }
    return loader;
  }

  //

  _didDestroyModel() {
    super._didDestroyModel();

    let filter = this.filter();
    if(filter) {
      filter.destroy();
    }

    let loader = this.loader();
    if(loader) {
      loader.destroy();
    }
  }

  //

  destroy() {
    let model = this.model(false);
    if(model) {
      model.destroy();
    }
  }

}
