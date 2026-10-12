import { Model } from 'documents';
import LifecycleMixin from '../-lifecycle-mixin';
import { all, hash } from 'rsvp';

/* global emit */
const ddocs = {
  main: {
    version: 1,
    views: {
      'by-type': {
        map(doc) {
          emit(doc.type);
        }
      }
    }
  },
  blog: {
    views: {
      'by-owner': {
        map(doc) {
          if(doc.type !== 'blog') {
            return;
          }
          emit(doc.owner);
        }
      }
    }
  },
  author: {
    views: {
      'by-id-with-owned-blogs': {
        map(doc) {
          if(doc.type === 'author') {
            emit(doc._id);
          } else if(doc.type === 'blog') {
            if(doc.owner) {
              emit(doc.owner, { _id: doc._id });
            }
          }
        }
      }
    }
  }
};

const docs = [
  { _id: 'author:ampatspell',    type: 'author', name: 'ampatspell', email: 'ampatspell@gmail.com' },
  { _id: 'author:zeeba',         type: 'author', name: 'zeeba', email: 'zeeba@gmail.com' },
  { _id: 'author:larry',         type: 'author', name: 'larry', email: 'larry@gmail.com' },
  { _id: 'author:duck',          type: 'author', name: 'duck', email: 'duck@gmail.com' },

  { _id: 'blog:amateurinmotion', type: 'blog',   name: 'amateurinmotion', owner: 'author:ampatspell' },
  { _id: 'blog:yellow-ducks',    type: 'blog',   name: 'Yellow Ducks', owner: 'author:duck' },
];

export default Model.extend(LifecycleMixin, {

  async _recreateDatabase() {
    return await this.get('database.documents.database').recreate();
  },

  async _insertDesignDocuments() {
    let design = this.get('database.documents.design');
    let promises = [];
    for(let key in ddocs) {
      let value = ddocs[key];
      promises.push(design.save(key, value));
    }
    return await all(promises);
  },

  async _insertDocuments() {
    let database = this.get('database.documents');
    return all(docs.map(doc => database.save(doc)));
  },

  async perform() {
    let recreate = await this._recreateDatabase();
    let { design, docs } = await hash({
      design: this._insertDesignDocuments(),
      docs: this._insertDocuments()
    });
    return { recreate, design, docs };
  },

  async validate() {
    let doc = await this.get('database.documents.design').load('main', { optional: true });
    if(!doc || doc.version !== ddocs.main.version) {
      return { ok: false, needed: true };
    }
    return { ok: true };
  }

});
