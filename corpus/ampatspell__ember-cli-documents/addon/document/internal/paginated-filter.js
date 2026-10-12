import { A } from '@ember/array';
import { copy } from '@ember/object/internals';

export default class PaginatedFilter {

  constructor(array, opts, state) {
    this._array = array;
    this._state = state;
    this._values = null;
    this.opts = opts;
  }

  get values() {
    let values = this._values;
    if(!values) {
      values = A();
      this._values = values;
      this._startObserving();
    }
    return values;
  }

  set state(value) {
    if(this._state === value) {
      return;
    }
    this._state = value;
    this._rematch();
  }

  _remove(docs) {
    let values = this._values;
    values.removeObjects(docs);
  }

  _push(docs) {
    let values = this._values;
    values.addObjects(docs);
  }

  __matches() {
    let state = this._state;
    if(!state) {
      return () => false;
    }
    return doc => !!this.opts.matches(doc, null, state);
  }

  _match(docs) {
    let matches = this.__matches();
    let matched = docs.filter(doc => matches(doc));
    this._push(matched);
  }

  _rematch() {
    let matches = this.__matches();

    let docs = this._array;
    let remove = A(copy(docs));
    let add = [];

    docs.forEach(doc => {
      if(matches(doc)) {
        add.push(doc);
        remove.removeObject(doc);
      }
    });

    this._remove(remove);
    this._push(add);
  }

  get _arrayObserverOptions() {
    return {
      willChange: this._arrayWillChange,
      didChange: this._arrayDidChange
    };
  }

  _arrayWillChange(array, removing) {
    this._remove(removing);
  }

  _arrayDidChange(array, removeCount, adding) {
    this._match(adding);
  }

  _startObserving() {
    let array = this._array;
    array.addEnumerableObserver(this, this._arrayObserverOptions);
  }

  _stopObserving() {
    let array = this._array;
    array.removeEnumerableObserver(this, this._arrayObserverOptions);
  }

  destroy() {
    this._stopObserving();
  }

}
