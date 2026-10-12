import { assert } from '@ember/debug';
import ModelMixin from './-model-mixin';
import { isInternal } from 'documents/util/internal';

const types = [ 'document', 'model', 'shoebox' ];

export const empty = {};

export default ModelMixin(class InternalBase {

  constructor(store, parent) {
    this.store = store;
    this.parent = parent;
  }

  get isDocument() {
    return false;
  }

  _document() {
    let target = this;
    while(target) {
      if(target.isDocument) {
        return target;
      }
      target = target.parent;
    }
  }

  //

  _assertType(type) {
    assert(`type must be one of the following [${types.join(', ')}] not '${type}'`, types.includes(type));
  }

  _assertChanged(changed) {
    assert(`changed must be function not ${changed}`, typeof changed === 'function');
  }

  //

  _invokeOnParents(cb) {
    let target = this.parent;
    while(target) {
      cb(target);
      target = target.parent;
    }
  }

  _willEndPropertyChanges(changed) {
    changed('serialized');
  }

  _didEndPropertyChanges() {
    this._invokeOnParents(parent => parent.withPropertyChanges(changed => changed('serialized'), true));
  }

  withPropertyChanges(cb, notify, except) {
    assert(`withPropertyChanges notify argument must be boolean`, typeof notify === 'boolean');

    let model;

    if(notify) {
      model = this.model(false);
    }

    if(model && notify) {
      model.beginPropertyChanges();
    }

    let changes = [];

    let changed = key => {
      if(model && notify && (!except || !except.includes(key))) {
        model.notifyPropertyChange(key);
      }
      if(!changes.includes(key)) {
        changes.push(key);
      }
    }

    let result = cb(changed);

    if(notify && changes.length) {
      this._willEndPropertyChanges(changed);
    }

    if(model && notify) {
      model.endPropertyChanges();
    }

    if(notify && changes.length) {
      this._didEndPropertyChanges();
    }

    return result;
  }

  //

  isDetached() {
    return !this.parent;
  }

  _detach() {
    this.parent = null;
  }

  _attach(parent) {
    if(this.parent === parent) {
      return;
    }
    assert(`internal is already attached`, !this.parent);
    this.parent = parent;
  }

  _detachInternal(value) {
    if(isInternal(value)) {
      value._detach();
    }
  }

  _attachInternal(value) {
    if(isInternal(value)) {
      value._attach(this);
    }
  }

  //

  _dirty(changed) {
    if(this.isDocument) {
      this.state.onDirty(changed);
    } else {
      let document = this._document();
      if(document) {
        document.withPropertyChanges(changed => document.state.onDirty(changed), true);
      }
    }
  }

  //

  shouldSerialize() {
    return true;
  }

  serialize(type) {
    this._assertType(type);
    if(!this.shouldSerialize(type)) {
      return;
    }
    return this._serialize(type);
  }

  deserialize(values, type, changed) {
    this._assertType(type);
    this._assertChanged(changed);
    this._deserialize(values, type, changed);
    return this;
  }

});
