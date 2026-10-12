import { A } from '@ember/array';
import { maybe as maybeCall } from './function-call';
import { startObservingObjects, stopObservingObjects } from './object-observer';

export default class ArrayObserver {

  // array: Enumerable
  // observe: [ 'id', 'type' ]
  // delegate: { target: null, removed(array), added(array), updated(object, key) }
  constructor({ array, observe, delegate }) {
    this._array = array;
    this._observe = observe;
    this._delegate = delegate;
    this.isDestroyed = false;
    this._startObserving();
  }

  _notifyDelegate(name, ...args) {
    let delegate = this._delegate;
    maybeCall(delegate.target, delegate[name], ...args);
  }

  //

  _startObservingObjects(objects) {
    startObservingObjects(objects, this._observe, this, this._objectDidChange);
  }

  _stopObservingObjects(objects) {
    stopObservingObjects(objects, this._observe, this, this._objectDidChange);
  }

  _objectDidChange(object, key) {
    this._notifyDelegate('updated', object, key);
  }

  //

  get _arrayObserverOptions() {
    return {
      willChange: this._arrayWillChange,
      didChange: this._arrayDidChange
    };
  }

  _startObserving() {
    let array = this._array;
    array.addEnumerableObserver(this, this._arrayObserverOptions);
    this._startObservingObjects(array);
  }

  _stopObserving() {
    let array = this._array;
    array.removeEnumerableObserver(this, this._arrayObserverOptions);
    this._stopObservingObjects(array);
  }

  _arrayWillChange(array, removing) {
    this._notifyDelegate('removed', A(removing));
    this._stopObservingObjects(removing);
  }

  _arrayDidChange(array, removeCount, adding) {
    this._notifyDelegate('added', A(adding));
    this._startObservingObjects(adding);
  }

  destroy() {
    if(this.isDestroyed) {
      return;
    }
    this.isDestroyed = true;
    this._stopObserving();
  }

}
