import { A } from '@ember/array';

class ModelsByClass {

  constructor(array, modelClass) {
    this._array = array;
    this._modelClass = modelClass;
    this.values = A(this._match(array));
    this._startObserving();
  }

  _match(array) {
    let modelClass = this._modelClass;
    return A(array).filter(model => modelClass.detectInstance(model));
  }

  get _arrayObserverOptions() {
    return {
      willChange: this._arrayWillChange,
      didChange: this._arrayDidChange
    };
  }

  _startObserving() {
    this._array.addEnumerableObserver(this, this._arrayObserverOptions);
  }

  _stopObserving() {
    this._array.removeEnumerableObserver(this, this._arrayObserverOptions);
  }

  _arrayWillChange(array, removing) {
    this.values.removeObjects(removing);
  }

  _arrayDidChange(array, removeCount, adding) {
    this.values.addObjects(this._match(adding));
  }

  destroy() {
    this._stopObserving();
  }

}

export default class FilterByClass {

  constructor(array) {
    this._array = array;
    this._modelsByClass = A();
  }

  get(modelClass) {
    let hash = this._modelsByClass.findBy('modelClass', modelClass);
    if(!hash) {
      let content = new ModelsByClass(this._array, modelClass);
      hash = { modelClass, content };
      this._modelsByClass.push(hash);
    }
    return hash.content.values;
  }

  destroy() {
    this._modelsByClass.forEach(hash => hash.content.destroy());
  }

}
