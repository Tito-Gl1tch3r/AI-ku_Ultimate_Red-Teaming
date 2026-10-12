import { isObject, isArray, isFunction, assert } from '../../util/assert';
import ObjectObserver from '../../util/object-observer';
import { call as delegateCall } from '../../util/function-call';

export default class StorageObserver {

  constructor({ context, storage, delegate }) {
    this._context = context;
    this._storage = storage;
    this._delegate = delegate;
    this._definition = this._lookupDefinition();
    this.modelInfo = this._lookupModelInfo();
    this._observer = new ObjectObserver({
      object: storage,
      observe: this._definition.observe,
      delegate: {
        target: this,
        updated(object, key) {
          this._storageValueForKeyDidChange(key);
        }
      }
    });
  }

  _notifyDelegate(name) {
    let delegate = this._delegate;
    delegateCall(delegate.target, delegate[name]);
  }

  _lookupDefinition() {
    let definition = this._context.adapter.modelDefinitionForStorage(this._storage);
    isObject('definition', definition);
    isArray('definition.observe', definition.observe);
    isFunction('definition.type', definition.type);
    return definition;
  }

  _lookupModelInfo() {
    let modelType = this._definition.type(this._storage);
    assert(`definition.type must return type`, !!modelType);
    let modelName = this._context.internalModelManager.modelNameForType(modelType);
    if(!modelName) {
      return;
    }
    return {
      modelType,
      modelName
    };
  }

  _storageValueForKeyDidChange() {
    let info = this._lookupModelInfo();
    let curr = this.modelInfo;
    if(info === curr) {
      return;
    }
    if(info && curr && info.modelName === curr.modelName) {
      return;
    }
    this.modelInfo = info;
    this._notifyDelegate('modelInfoDidChange');
  }

  destroy() {
    this._observer && this._observer.destroy();
  }

}
