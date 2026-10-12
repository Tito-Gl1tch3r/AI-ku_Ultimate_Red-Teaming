import { allSettled, defer, reject, resolve } from 'rsvp';
import { A } from '@ember/array';
import { merge } from '@ember/polyfills';
import Base from './-base';
import ObserveOwner from './-observe-owner';
import DocumentsError from 'documents/util/error';
import { isObject_ } from 'documents/util/assert';
import { omit } from 'documents/util/object';

class Operation {

  constructor(loader, opts, fn) {
    this.loader = loader;
    this.opts = opts;
    this.fn = fn;
    this.deferred = defer();
  }

  invoke() {
    let operation = this.fn();
    operation.promise.then(arg => this.deferred.resolve(arg), err => this.deferred.reject(err));
  }

  get promise() {
    return this.deferred.promise;
  }

}

const INVALIDATED = {};

export default class Loader extends ObserveOwner(Base) {

  constructor(store, parent, database, owner, opts, type) {
    super(store, parent);
    this.database = database;
    this.owner = owner;
    this.opts = merge({ autoload: true }, opts);
    this.type = type;
    this.operations = A();
    this._state = null;
    this.__query = INVALIDATED;
    this._needsReload = false;
    this._invalidateQueryDependentKeys = [ 'state', 'isLoadable', 'isLoading', 'isLoaded' ];
  }

  //

  _ownerValueForKeyDidChange() {
    this._invalidateQuery();
  }

  _startObserving() {
    this._startObservingOwner();
  }

  _stopObserving() {
    this._stopObservingOwner();
  }

  //

  _didCreateModel() {
    super._didCreateModel();
    this._startObserving();
  }

  //

  get _queryState() {
    let query = this._query(false);
    return query && query.state || null;
  }

  _notifyQueryStateDidChange() {
    let parent = this.parent;
    parent._loaderQueryStateDidChange && parent._loaderQueryStateDidChange(this);
  }

  __createQuery(opts) {
    let hash = this._createQuery(opts);
    if(!hash) {
      return;
    }
    if(!hash.query) {
      return;
    }
    isObject_('query function result must be object or falsy', hash.query);
    return hash;
  }

  _query(create, opts) {
    let query = this.__query;
    if(query === INVALIDATED || (create && opts)) {
      if(create) {
        query = this.__createQuery(opts);
        this.__query = query;
        this._notifyQueryStateDidChange();
      } else {
        query = undefined;
      }
    }
    return query;
  }

  _recreateQuery() {
    let query = this.__query;
    if(query === INVALIDATED) {
      query = null;
    }
    return this._query(true, omit(query || {}, [ 'query' ]));
  }

  _invalidateQuery() {
    this.__query = INVALIDATED;
    this._needsReload = true;
    this.withPropertyChanges(changed => this._invalidateQueryDependentKeys.forEach(key => changed(key)), true);
  }

  //

  get _isLoadable() {
    return !!this._query(true);
  }

  get state() {
    let state = this._state;
    if(!state) {
      state = this._createLoaderState();
      this._state = state;
    }
    return state;
  }

  _getStateProperty(key) {
    if(key !== 'isLoadable') {
      this._scheduleAutoload([ key ]);
    }
    return this.state[key];
  }

  _withState(cb, except) {
    return this.withPropertyChanges(changed => cb(this.state, changed), true, except);
  }

  //

  settle() {
    return allSettled(this.operations.map(op => op.promise));
  }

  _withRejectNotLoadable(cb) {
    if(!this._isLoadable) {
      return reject(new DocumentsError({ error: 'loader', reason: 'not_loadable' }));
    }
    return cb();
  }

  load() {
    return this._withRejectNotLoadable(() => this._scheduleLoad().promise);
  }

  reload() {
    return this._withRejectNotLoadable(() => this._scheduleReload().promise);
  }

  //

  __scheduleDocumentOperation(query, before, resolve, reject) {
    let database = this.database;
    return database._scheduleDocumentOperation(query, this.type, before, resolve, reject);
  }

  __createOperation(opts, fn) {
    let operations = this.operations;
    let operation = new Operation(this, opts, fn);
    operation.promise.catch(() => {}).finally(() => operations.removeObject(operation));
    operations.pushObject(operation);
    return operation;
  }

  __isLastOperation() {
    return this.operations.length === 1;
  }

  _existingOperation(match) {
    let operation = this.operations.get('lastObject');
    if(!operation || !match(operation.opts)) {
      return;
    }
    return operation;
  }

  _operationDidResolve() {
  }

  __operationDidResolve(results) {
    this._withState((state, changed) => state.set({ isLoaded: true }, changed));
    this._operationDidResolve(results);
  }

  _scheduleOperation(label, query, query_, except) {
    const before  = () => {
      if(!this.__isLastOperation()) {
        return;
      }
      this._withState((state, changed) => state.onLoading(changed));
    };

    const resolve = info => {
      this.__operationDidResolve(info);
      if(!this.__isLastOperation()) {
        return;
      }
      this._withState((state, changed) => state.onLoaded(changed));
    };

    const reject  = err => {
      if(!this.__isLastOperation()) {
        return;
      }
      this._withState((state, changed) => state.onError(err, changed));
    };

    const fn = () => this.__scheduleDocumentOperation(merge(query_ || {}, query.query), before, resolve, reject);
    let operation = this.__createOperation({ label, query }, fn);

    this._withState((state, changed) => {
      if(label === 'reload') {
        state.onReloadScheduled(changed);
      } else {
        state.onLoadScheduled(changed);
      }
    }, except);

    operation.invoke();
    return operation;
  }

  _resolveOperation() {
    return { promise: resolve() };
  }

  //

  _needsAutoload() {
    if(this.opts.autoload === false) {
      return false;
    }
    if(!this._isLoadable) {
      return false;
    }
    if(this._needsReload) {
      return true;
    }
    let state = this.state;
    return !state.isLoaded && !state.isLoading && !state.isError;
  }

  _scheduleAutoload(except) {
    if(!this._needsAutoload()) {
      return;
    }
    if(this._needsReload) {
      this._scheduleReload(except);
    } else {
      this._scheduleLoad(except);
    }
    this._needsReload = false;
  }

  _scheduleLoad(except) {
    if(this.state.isLoaded) {
      return this._resolveOperation();
    }

    let query = this._query(true);

    let operation = this._existingOperation(opts => opts.query === query);
    if(operation) {
      return operation;
    }

    return this._scheduleOperation('load', query, null, except);
  }

  _willScheduleReloadOperation() {
  }

  _scheduleReload(except) {
    let query = this._query(true);
    let isLoaded = this.state.isLoaded;

    let operation = this._existingOperation(opts => {
      if(opts.query !== query) {
        return;
      }
      if(isLoaded && opts.label !== 'reload') {
        return false;
      }
      return true;
    });

    if(operation) {
      return operation;
    }

    this._willScheduleReloadOperation();

    this._needsReload = false;
    query = this._query(true);

    return this._scheduleOperation('reload', query, { force: true }, except);
  }

  //

  get _modelWillDestroyUnsetsModel() {
    return false;
  }

  _didDestroyModel() {
    super._didDestroyModel();
    this._stopObserving();
  }

  destroy() {
    this._stopObserving();
    let model = this.model();
    if(model) {
      model.destroy();
    }
  }

}
