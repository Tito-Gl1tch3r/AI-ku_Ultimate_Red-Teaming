import { A } from '@ember/array';
import Mixin from '@ember/object/mixin';
import { get } from '@ember/object';
import { merge } from '@ember/polyfills';

export default opts => {
  opts = merge({ content: 'content' }, opts);
  opts.root = merge({ array: 'arrays', key: null }, opts.root);
  return Mixin.create({

    __contentKey: '__content',

    init() {
      this._prepare();
      this._super(...arguments);
    },

    _prepare() {
      this.__content = A();

      this._addRootObserver();

      this.__contentKey = opts.content;
      this.set(opts.content, this.__content);
      delete this.__content;
    },

    _lookupContent() {
      return get(this, this.__contentKey);
    },

    _rootObserverOptions() {
      return {
        willChange: this._rootArrayWillChange,
        didChange:  this._rootArrayDidChange
      };
    },

    _nestedObserverOptions() {
      return {
        willChange: this._nestedArrayWillChange,
        didChange:  this._nestedArrayDidChange
      };
    },

    _nestedArrayWillChange(array, removing) {
      this._lookupContent().removeObjects(removing);
    },

    _nestedArrayDidChange(array, removeCount, adding) {
      this._lookupContent().pushObjects(adding);
    },

    _addNestedObserver(array) {
      array.addEnumerableObserver(this, this._nestedObserverOptions());
      this._lookupContent().pushObjects(array);
    },

    _removeNestedObserver(array) {
      array.removeEnumerableObserver(this, this._nestedObserverOptions());
      this._lookupContent().removeObjects(array);
    },

    _rootArrayWillChange(array, removing) {
      removing.forEach(item => this._removeNestedObserver(this._lookupRootArrayItem(item)));
    },

    _rootArrayDidChange(array, removeCount, adding) {
      adding.forEach(item => this._addNestedObserver(this._lookupRootArrayItem(item)));
    },

    _lookupRootArray() {
      let root = opts.root;
      return get(this, root.array);
    },

    _lookupRootArrayItem(item) {
      let root = opts.root;
      if(root.key) {
        return get(item, root.key);
      }
      return item;
    },

    _addRootObserver() {
      let array = this._lookupRootArray();
      if(!array) {
        return;
      }
      array.addEnumerableObserver(this, this._rootObserverOptions());
      array.forEach(item => this._addNestedObserver(this._lookupRootArrayItem(item)));
    },

    _removeRootObserver() {
      let array = this._lookupRootArray();
      array.forEach(item => this._removeNestedObserver(this._lookupRootArrayItem(item)));
      array.removeEnumerableObserver(this, this._rootObserverOptions());
    },

    willDestroy() {
      this._removeRootObserver();
      this._super();
    }

  });
};
