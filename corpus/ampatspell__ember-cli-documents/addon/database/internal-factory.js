import Mixin from '@ember/object/mixin';
import { A } from '@ember/array';
import { assign } from '@ember/polyfills';

export default Mixin.create({

  __createInternalDocument(values, state, type) {
    let internal = this.get('store')._createInternalDocument(this);
    return internal.withPropertyChanges(changed => {
      internal.deserialize(values, type, changed);
      internal.state.set(state, changed);
      return internal;
    }, false);
  },

  _createNewInternalDocument(values, type) {
    let internal = this.__createInternalDocument(values, { isNew: true, isDirty: false }, type);
    this._storeNewInternalDocument(internal);
    return internal;
  },

  __createExistingInternalDocument(id) {
    let values = { _id: id };
    let internal = this.__createInternalDocument(values, { isNew: false, isDirty: false }, 'document');
    return internal;
  },

  _existingInternalDocument(id, opts) {
    let { create, deleted } = assign({ create: false, deleted: false }, opts);
    let internal = this._internalDocumentWithId(id, deleted);
    let created = false;
    if(!internal && create) {
      if(!deleted) {
        internal = this._internalDocumentWithId(id, true);
      }
      if(!internal) {
        internal = this.__createExistingInternalDocument(id);
        created = true;
      }
    }
    return {
      internal,
      created
    };
  },

  _existingInternalDocuments(ids, opts) {
    return A(ids).map(id => {
      let { internal, created } = this._existingInternalDocument(id, opts);
      return { id, internal, created };
    });
  },

  _createInternalArray(values, type) {
    let internal = this.get('store')._createInternalArray(null);
    internal.withPropertyChanges(changed => internal.deserialize(values, type, changed), false);
    return internal;
  },

  _createInternalObject(values, type) {
    let internal = this.get('store')._createInternalObject(null);
    internal.withPropertyChanges(changed => internal.deserialize(values, type, changed), false);
    return internal;
  },

  _createInternalAttachment(props) {
    return this.get('store')._createInternalAttachment(null, props);
  },

  _createInternalDocumentProxy(owner, opts) {
    return this.get('store')._createInternalDocumentProxy(this, owner, opts);
  },

  _createInternalArrayProxy(owner, opts) {
    return this.get('store')._createInternalArrayProxy(this, owner, opts);
  },

  _createInternalPaginatedProxy(owner, opts) {
    return this.get('store')._createInternalPaginatedProxy(this, owner, opts);
  },

  _createInternalFilter(owner, opts) {
    return this.get('store')._createInternalFilter(this, owner, opts);
  },

  _createInternalQueryLoader(parent, owner, opts, type) {
    return this.get('store')._createInternalQueryLoader(parent, this, owner, opts, type);
  },

  _createInternalPaginatedLoader(parent, owner, opts) {
    return this.get('store')._createInternalPaginatedLoader(parent, this, owner, opts);
  }

});
