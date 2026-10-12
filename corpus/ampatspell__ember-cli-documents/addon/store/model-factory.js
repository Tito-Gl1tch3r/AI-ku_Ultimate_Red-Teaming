import Mixin from '@ember/object/mixin';

export default Mixin.create({

  _documentsModelFactory(factoryName) {
    return this._factoryFor(`documents:${factoryName}`);
  },

  _createDocumentModel(_internal) {
    return this._documentsModelFactory('document').create({ _internal });
  },

  _createAttachmentsModel(_internal) {
    return this._documentsModelFactory('attachments').create({ _internal });
  },

  _createAttachmentContentModel(type, _internal) {
    return this._documentsModelFactory(`attachment/${type}`).create({ _internal });
  },

  _createAttachmentModel(_internal) {
    let content = _internal.content.model(true);
    return this._documentsModelFactory('attachment').create({ _internal, content });
  },

  _createObjectModel(_internal) {
    return this._documentsModelFactory('object').create({ _internal });
  },

  _createArrayModel(_internal) {
    let content = _internal.values;
    return this._documentsModelFactory('array').create({ _internal, content });
  },

  _changesModelFactory(name) {
    return this._documentsModelFactory(`changes/${name}`);
  },

  _createDatabaseChangesModel(_internal) {
    return this._changesModelFactory('database').create({ _internal });
  },

  _createStoreChangesModel(_internal) {
    return this._changesModelFactory('store').create({ _internal });
  },

  _createDocumentProxy(_internal) {
    return this._documentsModelFactory('proxy/document').create({ _internal });
  },

  _createArrayProxy(_internal) {
    let content = _internal.values;
    return this._documentsModelFactory('proxy/array').create({ _internal, content });
  },

  _createPaginatedProxy(_internal) {
    let all = _internal.all;
    let content = _internal.values;
    return this._documentsModelFactory('proxy/paginated').create({ _internal, all, content });
  },

  _createFilter(_internal) {
    return this._documentsModelFactory('filter').create({ _internal });
  },

  _createQueryLoader(_internal) {
    return this._documentsModelFactory('query-loader').create({ _internal });
  },

  _createPaginatedLoader(_internal) {
    return this._documentsModelFactory('paginated-loader').create({ _internal });
  }

});
