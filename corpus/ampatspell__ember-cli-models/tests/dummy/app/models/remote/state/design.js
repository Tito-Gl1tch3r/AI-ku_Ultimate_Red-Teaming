import { all } from 'rsvp';
import { readOnly } from '@ember/object/computed';
import Model from 'ember-cli-models/model/transient';
import { database } from 'ember-cli-models/computed';

/* global emit */
const ddocs = {
  author: {
    views: {
      'by-id': {
        map(doc) {
          if(doc.type !== 'author') {
            return;
          }
          emit(doc._id);
        }
      },
      'by-id-with-blogs': {
        map(doc) {
          if(doc.type === 'author') {
            emit(doc._id);
          } else if(doc.type === 'blog') {
            if(doc.editors && doc.editors.length) {
              for(var i = 0; i < doc.editors.length; i++) {
                emit(doc.editors[i], { _id: doc._id });
              }
            }
          }
        }
      }
    }
  }
};

const docs = [
  { _id: 'author:ampatspell',    type: 'author', name: 'ampatspell' },
  { _id: 'author:zeeba',         type: 'author', name: 'zeeba' },
  { _id: 'blog:amateurinmotion', type: 'blog',   name: 'amateurinmotion', editors: [ 'author:ampatspell', 'author:zeeba' ] },
  { _id: 'blog:ducks',           type: 'blog',   name: 'ducks',           editors: [ 'author:zeeba' ] },
];

export default Model.extend({

  database: database(),

  documents: readOnly('database.documents'),
  design: readOnly('documents.design'),

  async insertDesignDocument(key) {
    let ddoc = ddocs[key];
    let design = this.get('design');
    return await design.save(key, ddoc);
  },

  async insertDesignDocuments() {
    return await all(Object.keys(ddocs).map(key => this.insertDesignDocument(key)));
  },

  async deleteDocuments() {
    return await this.get('documents.database').recreate();
  },

  async insertDocuments() {
    let documents = this.get('documents');
    return await all(docs.map(doc => documents.save(doc)));
  },

  async recreate() {
    let deletes = await this.deleteDocuments();

    let [
      design,
      inserts
    ] = await all([
      this.insertDesignDocuments(),
      this.insertDocuments()
    ]);

    return { deletes, design, inserts };
  }

});
