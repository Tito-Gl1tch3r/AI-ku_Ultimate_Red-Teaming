import Ember from 'ember';
import InternalObject from './object';
import DocumentState from './-document-state';
import Queue from './-queue';
import DocumentsError from '../../util/error';

const {
  Logger: { error }
} = Ember;

const prefixedKeys = [ 'id', 'rev', 'attachments' ];
const isKeyUnderscored = key => key && key.indexOf('_') === 0;

export default class InternalDocument extends InternalObject {

  constructor(store, database) {
    super(store, null);
    this.database = database;
    this.state = new DocumentState();
    this.queue = new Queue();
  }

  addOperation(op) {
    return this.queue.add(op);
  }

  get isDocument() {
    return true;
  }

  get isNew() {
    return this.state.isNew;
  }

  get isLoaded() {
    return this.state.isLoaded;
  }

  get isDeleted() {
    return this.state.isDeleted;
  }

  _modelWillDestroy() {
    if(this.isNew) {
      // keep _model so it is not recreated on next `model(true)` call
      this.database._willDestroyModelForNewInternalDocument(this);
    }
    super._modelWillDestroy();
  }

  _createModel() {
    return this.store._createDocumentModel(this);
  }

  getId() {
    return this._getValue('id');
  }

  setId(id) {
    if(!this.isNew && id !== this.getId()) {
      let current = this.getId();
      error(`Document id cannot be changed after document is saved. Attempted to set id '${id}' for document '${current}'`);
      return current;
    }
    return this._setValueNotify('id', id, 'model');
  }

  getRev() {
    return this._getValue('rev');
  }

  getIdRev() {
    return {
      id: this.getId(),
      rev: this.getRev()
    };
  }

  //

  _createAttachments() {
    return this.store._createInternalAttachments(this);
  }

  _attachments(create) {
    let attachments = this._getValue('attachments');
    if(!attachments && create) {
      attachments = this._createAttachments();
      this.values.attachments = attachments;
    }
    return attachments;
  }

  getAttachments() {
    return this._attachments(true).model(true);
  }

  setAttachments(values) {
    let attachments = this._attachments(true);
    attachments.withPropertyChanges(changed => attachments._deserialize(values, 'model', changed), true);
    return attachments.model(true);
  }

  deserializeAttachments(doc, changed) {
    let _attachments = doc._attachments;
    let attachments = this._attachments(false);

    if(!_attachments && !attachments) {
      return;
    }

    _attachments = _attachments || {};
    attachments = attachments || this._attachments(true);

    attachments._deserialize(_attachments, 'document', changed);
  }

  //

  _deserializeDocumentKey(key) {
    if(key.startsWith('_')) {
      let sliced = key.slice(1);
      if(prefixedKeys.includes(sliced)) {
        return sliced;
      }
    }
    return super._deserializeDocumentKey(key);
  }

  _serializeDocumentKey(key) {
    if(prefixedKeys.includes(key)) {
      return `_${key}`;
    }
    return super._serializeDocumentKey(key);
  }

  //

  _setValue(key, ...rest) {
    if(isKeyUnderscored(key)) {
      return;
    }
    if(key === 'attachments') {
      return this._attachments(true)._deserialize(...rest);
    }
    return super._setValue(...arguments);
  }

  _getValue(key) {
    if(isKeyUnderscored(key)) {
      return;
    }
    return super._getValue(...arguments);
  }

  //

  deserializeDeleted(json, changed) {
    let type = 'document';
    let { id, rev } = json;
    this._setValue('id', id, type, changed);
    this._setValue('rev', rev, type, changed);
  }

  deserializeSaved(json, changed) {
    let type = 'document';
    let { id, rev } = json;
    this._setValue('id', id, type, changed);
    this._setValue('rev', rev, type, changed);
  }

  //

  shouldSerialize(type) {
    if(type === 'shoebox') {
      if(this.isNew || !this.isLoaded) {
        return false;
      }
    }
    return super.shouldSerialize(type);
  }

  //

  setState(name, notify=true) {
    this.withPropertyChanges(changed => {
      let state = this.state;
      let fn = state[name];
      fn.call(state, changed);
    }, notify);
  }

  //

  save() {
    return this.database._scheduleInternalSave(this, ...arguments).promise;
  }

  load() {
    return this.database._scheduleInternalLoad(this, ...arguments).promise;
  }

  reload() {
    return this.database._scheduleInternalReload(this, ...arguments).promise;
  }

  delete() {
    return this.database._scheduleInternalDelete(this, ...arguments).promise;
  }

  onError(err, notify) {
    err = err instanceof Error ? err : new DocumentsError(err);
    this.withPropertyChanges(changed => this.state.onError(err, changed), notify);
    return err;
  }

}
