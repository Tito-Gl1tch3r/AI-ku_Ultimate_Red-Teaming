import { A } from '@ember/array';
import Base from './-base';
import ObserveOwner from './-observe-owner';

export default class FilterInternal extends ObserveOwner(Base) {

  /*
    opts: {
      owner: [ 'id' ],
      document: [ 'id' ],
      matches(doc, owner) {
        return doc.get('id') === owner.get('id');
      }
    }
  */
  constructor(store, database, owner, opts) {
    super();
    this.store = store;
    this.database = database;
    this.owner = owner;
    this.opts = opts;
    this._values = null;
  }

  _createModel() {
    return this.store._createFilter(this);
  }

  get documents() {
    return this.database.get('documentsIdentity');
  }

  __matches() {
    let owner = this.owner;
    return doc => !!this.opts.matches(doc, owner);
  }

  _matches(doc) {
    let matches = this.__matches();
    return matches(doc);
  }

  _match(docs) {
    let matches = this.__matches();
    return docs.filter(doc => matches(doc));
  }

  _rematch() {
    let matches = this.__matches();

    let docs = this.documents;
    let remove = docs.map(doc => doc);
    let add = [];

    docs.forEach(doc => {
      if(matches(doc)) {
        add.push(doc);
        remove.removeObject(doc);
      }
    });

    this._remove(remove);
    this._push(add);
  }

  _push(docs) {
    this.values.addObjects(docs);
  }

  _remove(docs) {
    this.values.removeObjects(docs);
  }

  //

  _ownerValueForKeyDidChange() {
    this._rematch();
  }

  //

  _documentValueForKeyDidChange(doc) {
    if(this._matches(doc)) {
      this._push([ doc ]);
    } else {
      this._remove([ doc ]);
    }
  }

  _withDocumentObserving(docs, cb) {
    if(docs.length === 0) {
      return;
    }
    let keys = this.opts.document;
    if(!keys || keys.length === 0) {
      return;
    }
    keys.forEach(key => docs.forEach(doc => cb(doc, key)));
  }

  _startObservingDocuments(docs) {
    this._withDocumentObserving(docs, (doc, key) => {
      doc.addObserver(key, this, this._documentValueForKeyDidChange);
    });
  }

  _stopObservingDocuments(docs) {
    this._withDocumentObserving(docs, (doc, key) => {
      doc.removeObserver(key, this, this._documentValueForKeyDidChange);
    });
  }

  _documentsWillChange(documents, removing) {
    this._stopObservingDocuments(removing);
    this._remove(removing);
  }

  _documentsDidChange(documents, removeCount, adding) {
    this._startObservingDocuments(adding);
    let matched = this._match(adding);
    this._push(matched);
  }

  get _documentsObserverOptions() {
    return {
      willChange: this._documentsWillChange,
      didChange: this._documentsDidChange
    };
  }

  _startObservingDocumentArray() {
    let documents = this.documents;
    documents.addEnumerableObserver(this, this._documentsObserverOptions);
    this._startObservingDocuments(documents);
  }

  _stopObservingDocumentArray() {
    let documents = this.documents;
    documents.removeEnumerableObserver(this, this._documentsObserverOptions);
    this._stopObservingDocuments(documents);
  }

  //

  _startObserving() {
    this._startObservingOwner();
    this._startObservingDocumentArray();
  }

  _stopObserving() {
    this._stopObservingOwner();
    this._stopObservingDocumentArray();
  }

  get values() {
    let values = this._values;
    if(!values) {
      values = A();
      this._values = values;
      this._startObserving();
      this._rematch();
    }
    return values;
  }

  //

  get _modelWillDestroyUnsetsModel() {
    return false;
  }

  _didDestroyModel() {
    super._didDestroyModel();
    this._stopObserving();
  }

  destroy() {
    this._stopObserving();
    let model = this.model();
    if(model) {
      model.destroy();
    }
  }

}
