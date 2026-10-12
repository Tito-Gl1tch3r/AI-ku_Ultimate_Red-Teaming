import Mixin from '@ember/object/mixin';
import DocumentsError from '../util/error';

export default Mixin.create({

  _documentsInternalFactory() {
    return this.get('stores')._documentsInternalFactory(...arguments);
  },

  _createInternalDocument(database) {
    let InternalDocument = this._documentsInternalFactory('document');
    return new InternalDocument(this, database);
  },

  _createInternalAttachments(internal) {
    let InternalAttachments = this._documentsInternalFactory('attachments');
    return new InternalAttachments(this, internal);
  },

  _createInternalAttachmentContent(props) {
    const create = (type, ...args) => {
      let InternalAttachmentContent = this._documentsInternalFactory(`attachment/${type}`);
      return new InternalAttachmentContent(this, ...args);
    };

    if(props.stub === true) {
      return create('stub', props);
    }

    let contentType = props.type || props.contentType || props['content-type'];
    let data = props.data;

    if(typeof data === 'string') {
      contentType = contentType || 'text/plain';
      return create('string', data, contentType);
    }

    if(data instanceof Blob) {
      return create('file', data);
    }

    throw new DocumentsError({
      error: 'invalid_attachment',
      reason: `unsupported attachment object.data '${data}'. data may be String, File or Blob`
    });
  },

  _createInternalAttachment(parent, props) {
    let InternalAttachment = this._documentsInternalFactory('attachment');
    let content = this._createInternalAttachmentContent(props);
    return new InternalAttachment(this, parent, content);
  },

  _createInternalObject(parent) {
    let InternalObject = this._documentsInternalFactory('object');
    return new InternalObject(this, parent);
  },

  _createInternalArray(parent) {
    let InternalArray = this._documentsInternalFactory('array');
    return new InternalArray(this, parent);
  },

  _internalChangesFactory(type) {
    return this._documentsInternalFactory(`changes/${type}`);
  },

  _createInternalDatabaseChanges(database, opts) {
    let InternalDatabaseChanges = this._internalChangesFactory('database');
    return new InternalDatabaseChanges(this, database, opts);
  },

  _createInternalStoreChanges(opts) {
    let InternalStoreChanges = this._internalChangesFactory('store');
    return new InternalStoreChanges(this, opts);
  },

  _createInternalDocumentProxy(database, owner, opts) {
    let InternalDocumentProxy = this._documentsInternalFactory('proxy/document');
    return new InternalDocumentProxy(this, database, owner, opts);
  },

  _createInternalArrayProxy(database, owner, opts) {
    let InternalArrayProxy = this._documentsInternalFactory('proxy/array');
    return new InternalArrayProxy(this, database, owner, opts);
  },

  _createInternalPaginatedProxy(database, owner, opts) {
    let InternalPaginatedProxy = this._documentsInternalFactory('proxy/paginated');
    return new InternalPaginatedProxy(this, database, owner, opts);
  },

  _createInternalFilter(database, owner, opts) {
    let InternalFilter = this._documentsInternalFactory('filter');
    return new InternalFilter(this, database, owner, opts);
  },

  _createInternalQueryLoader(parent, database, owner, opts, type) {
    let InternalQueryLoader = this._documentsInternalFactory('query-loader');
    return new InternalQueryLoader(this, parent, database, owner, opts, type);
  },

  _createInternalPaginatedLoader(parent, database, owner, opts) {
    let InternalPaginatedLoader = this._documentsInternalFactory('paginated-loader');
    return new InternalPaginatedLoader(this, parent, database, owner, opts);
  }

});
