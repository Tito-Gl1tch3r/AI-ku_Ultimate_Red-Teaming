import Stores from '../stores';
import StoresDocumentsIdentity from 'documents/stores/-documents-identity';
import StoresModelsIdentity from 'documents/stores/-models-identity';
import StoresId from 'documents/stores/-id';

import Store from 'documents/store';
import StoreDocumentsIdentity from 'documents/store/-documents-identity';
import StoreId from 'documents/store/-id';
import Session from 'documents/session';

import Database from 'documents/database';
import DatabaseDocumentsIdentity from 'documents/database/-documents-identity';
import DatabaseSecurity from 'documents/security';
import DatabaseSecurityPair from 'documents/security-pair';

import Document from 'documents/document/document';
import InternalDocument from 'documents/document/internal/document';
import DocumentObject from 'documents/document/object';
import InternalObject from 'documents/document/internal/object';
import DocumentArray from 'documents/document/array';
import InternalArray from 'documents/document/internal/array';

import DocumentAttachments from 'documents/document/attachments/attachments';
import InternalDocumentAttachments from 'documents/document/attachments/internal/attachments';
import DocumentAttachment from 'documents/document/attachments/attachment';
import InternalDocumentAttachment from 'documents/document/attachments/internal/attachment';
import AttachmentString from 'documents/document/attachments/attachment/string';
import InternalAttachmentString from 'documents/document/attachments/attachment/internal/string';
import AttachmentStub from 'documents/document/attachments/attachment/stub';
import InternalAttachmentStub from 'documents/document/attachments/attachment/internal/stub';
import AttachmentFile from 'documents/document/attachments/attachment/file';
import InternalAttachmentFile from 'documents/document/attachments/attachment/internal/file';

import InternalDatabaseChanges from 'documents/changes/database/internal';
import DatabaseChanges from 'documents/changes/database/changes';
import InternalStoreChanges from 'documents/changes/store/internal';
import StoreChanges from 'documents/changes/store/changes';

import AdapterCouchStore from 'documents/adapter/couch/store';
import AdapterCouchDatabase from 'documents/adapter/couch/database';

import DocumentProxy from 'documents/document/document-proxy';
import InternalDocumentProxy from 'documents/document/internal/document-proxy';

import ArrayProxy from 'documents/document/array-proxy';
import InternalArrayProxy from 'documents/document/internal/array-proxy';

import PaginatedProxy from 'documents/document/paginated-proxy';
import InternalPaginatedProxy from 'documents/document/internal/paginated-proxy';

import Filter from 'documents/document/filter';
import InternalFilter from 'documents/document/internal/filter';
import QueryLoader from 'documents/document/query-loader';
import InternalQueryLoader from 'documents/document/internal/query-loader';

import PaginatedLoader from 'documents/document/paginated-loader';
import InternalPaginatedLoader from 'documents/document/internal/paginated-loader';

import InternalModel from 'documents/document/internal/model';
import InternalModels from 'documents/document/internal/models';

import Models from 'documents/document/models';

export default {
  name: 'documents:internal',
  initialize(container) {
    container.register('documents:stores', Stores);
    container.register('documents:stores/id', StoresId);

    container.register('documents:store', Store);
    container.register('documents:store/id', StoreId);
    container.register('documents:session', Session);
    container.register('documents:database', Database);

    container.register('documents:database/security', DatabaseSecurity);
    container.register('documents:database/security/pair', DatabaseSecurityPair);

    container.register('documents:document', Document);
    container.register('documents:object', DocumentObject);
    container.register('documents:array', DocumentArray);

    container.register('documents:attachments', DocumentAttachments);
    container.register('documents:attachment', DocumentAttachment);
    container.register('documents:attachment/string', AttachmentString);
    container.register('documents:attachment/file', AttachmentFile);
    container.register('documents:attachment/stub', AttachmentStub);

    container.register('documents:internal/document', InternalDocument);
    container.register('documents:internal/object', InternalObject);
    container.register('documents:internal/array', InternalArray);

    container.register('documents:internal/attachments', InternalDocumentAttachments);
    container.register('documents:internal/attachment', InternalDocumentAttachment);
    container.register('documents:internal/attachment/string', InternalAttachmentString);
    container.register('documents:internal/attachment/file', InternalAttachmentFile);
    container.register('documents:internal/attachment/stub', InternalAttachmentStub);

    container.register('documents:adapter/couch/store', AdapterCouchStore);
    container.register('documents:adapter/couch/database', AdapterCouchDatabase);

    container.register('documents:changes/database', DatabaseChanges);
    container.register('documents:changes/store', StoreChanges);

    container.register('documents:internal/changes/database', InternalDatabaseChanges);
    container.register('documents:internal/changes/store', InternalStoreChanges);

    container.register('documents:stores/documents-identity', StoresDocumentsIdentity);
    container.register('documents:store/documents-identity', StoreDocumentsIdentity);
    container.register('documents:database/documents-identity', DatabaseDocumentsIdentity);

    container.register('documents:stores/models-identity', StoresModelsIdentity);

    container.register('documents:proxy/document', DocumentProxy);
    container.register('documents:internal/proxy/document', InternalDocumentProxy);
    container.register('documents:proxy/array', ArrayProxy);
    container.register('documents:internal/proxy/array', InternalArrayProxy);
    container.register('documents:proxy/paginated', PaginatedProxy);
    container.register('documents:internal/proxy/paginated', InternalPaginatedProxy);

    container.register('documents:filter', Filter);
    container.register('documents:internal/filter', InternalFilter);

    container.register('documents:query-loader', QueryLoader);
    container.register('documents:internal/query-loader', InternalQueryLoader);

    container.register('documents:paginated-loader', PaginatedLoader);
    container.register('documents:internal/paginated-loader', InternalPaginatedLoader);

    container.register('documents:internal/model', InternalModel);
    container.register('documents:internal/models', InternalModels);

    container.register('documents:models', Models);
  }
};
