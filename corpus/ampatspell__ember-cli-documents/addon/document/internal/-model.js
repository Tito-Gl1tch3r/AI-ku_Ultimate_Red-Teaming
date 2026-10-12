import { A } from '@ember/array';
import { assign } from '@ember/polyfills';
import Base from './-base';
import normalizeModelOpts from '../../util/normalize-model-opts';

export default class InternalModelBase extends Base {

  constructor(stores, parent, factory, opts, _ref) {
    super(null, parent);
    this.stores = stores;
    this.factory = factory;
    this.opts = opts;
    this._models = null;
    this._ref = _ref;
    if(parent) {
      parent._registerChildModel(this);
    }
  }

  models(create) {
    let models = this._models;
    if(!models && create) {
      models = A();
      this._models = models;
    }
    return models;
  }

  _registerChildModel(internal) {
    this.models(true).push(internal);
  }

  _createInternalModel(...args) {
    let opts = assign({ _parent: this }, normalizeModelOpts(...args));
    return this.stores._createInternalModel(opts);
  }

  _childModelDidDestroy(internal) {
    this.models().removeObject(internal);
  }

  get _modelWillDestroyUnsetsModel() {
    return false;
  }

  _didDestroyModel() {
    let parent = this.parent;
    if(parent) {
      parent._childModelDidDestroy(this);
    }
    let models = this.models(false);
    if(models) {
      models.forEach(model => model.destroy());
    }
  }

  destroy() {
    let model = this.model(false);
    if(model) {
      model.destroy();
    }
  }

}
