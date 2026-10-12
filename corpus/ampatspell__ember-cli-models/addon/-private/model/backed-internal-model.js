import InternalModel from './internal-model';
import BackedModel from './backed-model';
import StorageObserver from './internal/storage-observer';
import State from './internal/state';
import withPropertyChanges from './internal/with-property-changes';

export default class BackedInternalModel extends InternalModel {

  constructor(context, storage, props) {
    super(context, { props });
    this.state = new State();
    this.storage = storage;
  }

  _withState(notify, cb) {
    withPropertyChanges(this, notify, changed => {
      cb(this.state, changed);
    });
  }

  onCreated(notify) {
    this._withState(notify, (state, changed) => state.onCreated(changed));
  }

  onDeleted(notify) {
    this._withState(notify, (state, changed) => state.onDeleted(changed));
  }

  observer(create) {
    if(this.isDestroyed) {
      return;
    }
    let observer = this._observer;
    if(!observer && create) {
      observer = new StorageObserver({
        context: this.context,
        storage: this.storage,
        delegate: {
          target: this,
          modelInfoDidChange: this._modelInfoDidChange
        }
      });
      this._observer = observer;
    }
    return observer;
  }

  _modelInfoDidChange() {
    this.recreateModel();
  }

  modelInfo(create) {
    let observer = this.observer(create);
    return observer && observer.modelInfo;
  }

  get modelType() {
    let info = this.modelInfo();
    return info && info.modelType;
  }

  _createModel() {
    let info = this.modelInfo(true);
    if(!info) {
      return;
    }
    let props = this.opts.props;
    return this.__createModel(BackedModel, info.modelName, props);
  }

  destroy() {
    this._observer && this._observer.destroy();
    this.storage.destroy();
    super.destroy();
  }

}
