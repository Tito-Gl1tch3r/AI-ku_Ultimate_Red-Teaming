import { A } from '@ember/array';
import EmberObject, { computed } from '@ember/object';
import ArrayObserver from '../util/array-observer';
import { isInstance } from '../util/assert';

const storage = fn => function(array) {
  let manager = this.database._context.internalModelManager;
  let func = manager[fn];
  return array.map(storage => func.call(manager, storage));
};

const content = () => computed(function() {
  return A();
});

export default EmberObject.extend({

  store: null,
  adapter: null,
  database: null,

  content: content(),

  _startObservingContent() {
    let array = this.get('content');
    if(!array) {
      return;
    }
    this._contentObserver = new ArrayObserver({
      array,
      delegate: {
        target:  this,
        added:   this.push,
        removed: this.delete
      }
    });
  },

  _stopObservingContent() {
    this._contentObserver && this._contentObserver.destroy();
  },

  start() {
    this._startObservingContent();
  },

  stop() {
    this._stopObservingContent();
  },

  storage() {
  },

  modelNameForType(type) {
    return type;
  },

  build(type, props) {
    let storage = this.storage(type, props);
    isInstance('storage result', storage);
    this.get('content').addObject(storage);
    return storage;
  },

  push:   storage('push'),
  delete: storage('delete'),

  compact() {
    return true;
  },

  willDestroy() {
    this.stop();
    this._super();
  }

});
