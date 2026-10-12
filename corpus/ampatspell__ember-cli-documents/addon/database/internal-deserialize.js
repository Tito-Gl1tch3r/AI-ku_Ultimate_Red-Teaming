import Mixin from '@ember/object/mixin';
import { A } from '@ember/array';
import { assert } from '@ember/debug';
import { reject } from 'rsvp';

export default Mixin.create({

  __deserializeInternalOnError(internal, err) {
    internal.withPropertyChanges(changed => {
      internal.state.onError(err, changed);
    }, true);
    return reject(err);
  },

  _deserializeInternalAttachments(internal, doc) {
    internal.withPropertyChanges(changed => {
      internal.deserializeAttachments(doc, changed);
    }, true);
  },

  _deserializeInternalSave(internal, json) {
    internal.withPropertyChanges(changed => {
      internal.deserializeSaved(json, changed);
      internal.state.onSaved(changed);
    }, true);
    this._storeSavedInternalDocument(internal);
    return internal;
  },

  _deserializeInternalSaveDidFail(internal, err) {
    return this.__deserializeInternalOnError(internal, err);
  },

  //

  __isNotFoundDeleted(err) {
    return err.error === 'not_found' && err.reason === 'deleted';
  },

  __isNotFoundMissing(err) {
    return err.error === 'not_found' && err.reason === 'missing';
  },

  __isNotFoundMissingOrDeleted(err) {
    return this.__isNotFoundMissing(err) || this.__isNotFoundDeleted(err);
  },

  _deserializeInternalDelete(internal, json) {
    internal.withPropertyChanges(changed => {
      if(json) {
        internal.deserializeDeleted(json, changed);
      }
      internal.state.onDeleted(changed);
    }, true);
    this._storeDeletedInternalDocument(internal);
    return internal;
  },

  __deserializeInternalOnErrorOrDelete(internal, err) {
    if(!this.__isNotFoundMissingOrDeleted(err)) {
      return this._deserializeInternalOnError(internal, err);
    }
    this._deserializeInternalDelete(internal, null);
    return reject(err);
  },

  //

  __deserializeInternalDeleteDidFail(internal, err) {
    return this.__deserializeInternalOnErrorOrDelete(internal, err);
  },

  //

  __deserializeInternalLoadDeleted(internal, doc) {
    let { _id: id, _rev: rev } = doc;
    return this._deserializeInternalDelete(internal, { id, rev });
  },

  __deserializeInternalLoadDocument(internal, doc, type) {
    internal.withPropertyChanges(changed => {
      internal.deserialize(doc, type, changed);
      internal.state.onLoaded(changed);
    }, true);
    this._storeLoadedInternalDocument(internal);
    return internal;
  },

  __parseRevToNumber(rev) {
    if(!rev) {
      return;
    }
    let parsed = parseInt(rev);
    if(isNaN(parsed)) {
      return;
    }
    return parsed;
  },

  _shouldDeserializeInternalLoad(existing, doc) {
    let docRev = doc._rev;
    if(!docRev) {
      return true;
    }

    let existingRev = existing.getRev();
    if(!existingRev) {
      return true;
    }

    let docRevNumber = this.__parseRevToNumber(docRev);
    if(docRevNumber) {
      let existingRevNumber = this.__parseRevToNumber(existingRev);
      if(existingRevNumber) {
        return docRevNumber > existingRevNumber;
      }
    }

    return existingRev !== docRev;
  },

  _deserializeInternalLoad(internal, doc, type, force) {
    if(!force && !this._shouldDeserializeInternalLoad(internal, doc)) {
      internal.setState('onLoaded');
      return internal;
    }

    if(doc._deleted) {
      return this.__deserializeInternalLoadDeleted(internal, doc);
    } else {
      return this.__deserializeInternalLoadDocument(internal, doc, type);
    }
  },

  _deserializeInternalLoadDidFail(internal, err) {
    return this.__deserializeInternalOnErrorOrDelete(internal, err);
  },

  //

  _deserializeDocument(doc, type) {
    assert(`doc must be object`, typeof doc === 'object');
    assert(`doc._id must be string`, typeof doc._id === 'string');

    let id = doc._id;
    let { internal } = this._existingInternalDocument(id, { deleted: true, create: true });

    return this._deserializeInternalLoad(internal, doc, type);
  },

  _deserializeDocuments(array, type) {
    return A(array).reduce((result, doc) => {
      // on high load it is possible that view returns row with already deleted document's key, value but w/o doc
      // see: https://issues.apache.org/jira/browse/COUCHDB-1797
      if(doc) {
        result.push(this._deserializeDocument(doc, type));
      }
      return result;
    }, A());
  }

});
