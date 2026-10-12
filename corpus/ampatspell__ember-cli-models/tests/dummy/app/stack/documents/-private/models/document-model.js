import Model from 'ember-cli-models/model/backed';
import StateMixin from './-state-mixin';
import { readOnly } from '@ember/object/computed';
import { database } from 'ember-cli-models/computed';
import { attr } from './computed';

const forward = key => function() {
  let storage = this.get('storage');
  return storage[key].call(storage, ...arguments);
}

const reads = key => readOnly(`storage.${key}`);

export default Model.extend(StateMixin, {

  id:  attr('id'),
  rev: attr('rev'),

  database: database(),

  state: reads('state'),

  serialized: reads('serialized'),

  load:   forward('load'),
  reload: forward('reload'),
  delete: forward('delete'),

  willCreate() {
  },

  willSave() {
  },

  async save() {
    if(this.get('isNew')) {
      await this.willCreate();
    } else {
      await this.willSave();
    }
    return await this.get('storage').save();
  },

  _documentId: readOnly('storage.id'),

}).reopenClass({

  debugColumns: [ '_documentId' ],

  toString() {
    return 'document-model';
  }

});
