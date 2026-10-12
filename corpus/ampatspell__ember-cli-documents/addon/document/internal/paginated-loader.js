import { A } from '@ember/array';
import Loader from './-loader';
import PaginatedLoaderState from './-paginated-loader-state';
import { isObject } from 'documents/util/assert';

export default class PaginatedLoaderInternal extends Loader {

  /*
    opts: {
      autoload: true,
      owner: [ 'id' ],
      query(owner, state) {
        let id = owner.get('id');
        id(!id) {
          return;
        }
        if(state) {
          let foo = state.foo;
          ..
        }
        return { ddoc, view, start_key, start_docid, end_key };
      },
      loaded(docs) {
        let isMore = true;
        let state = { foo };
        return { isMore, state };
      }
    }
  */
  constructor(store, parent, database, owner, opts) {
    super(store, parent, database, owner, opts, 'find');
    this._invalidateQueryDependentKeys.push('isMore');
  }

  get _isMore() {
    let query = this._query(false);
    if(query) {
      return query.isMore;
    }
    return false;
  }


  _createLoaderState() {
    return new PaginatedLoaderState(this);
  }

  _createModel() {
    return this.store._createPaginatedLoader(this);
  }

  _createQuery(previous) {
    let state = null;
    let isMore = false;
    if(previous) {
      state = previous.state || null;
      isMore = previous.isMore;
    }
    let query = this.opts.query(this.owner, state);
    return { query, isMore, state };
  }

  //

  _operationDidResolve({ result }) {
    let query = this._query(false);
    if(!query) {
      return;
    }

    let docs = A(result.map(internal => internal.model(true)));

    let loaded = this.opts.loaded(query.state, docs);
    isObject('loaded function result', loaded);

    let { state, isMore } = loaded;

    query.isMore = !!isMore;
    query.state = state;

    this._withState((state, changed) => changed('isMore'));
    this._notifyQueryStateDidChange();
  }

  _willScheduleReloadOperation() {
    this._invalidateQuery();
  }

  //

  loadMore() {
    return this._withRejectNotLoadable(() => this._scheduleLoadMore().promise);
  }

  //

  _scheduleLoadMore() {
    let { isLoaded, isMore } = this.state;

    if(!isLoaded) {
      return this._scheduleLoad();
    } else if(!isMore) {
      return this._resolveOperation();
    }

    let operation = this._existingOperation(() => true);

    if(operation) {
      return operation;
    }

    let query = this._recreateQuery();
    return this._scheduleOperation('more', query);
  }

}
