import { reject, resolve } from 'rsvp';
import { getOwner } from '@ember/application';
import EmberObject, { computed } from '@ember/object';
import { reads } from '@ember/object/computed';
import createStateMixin from './util/basic-state-mixin';

const State = createStateMixin();

const pair = key => computed(function() {
  let security = this;
  return getOwner(this).factoryFor('documents:database/security/pair').create({ key, security });
}).readOnly();

export default EmberObject.extend(State, {

  database: null,
  documents: reads('database.documents.security').readOnly(),

  admins:  pair('admins'),
  members: pair('members'),

  load() {
    this.onLoading();
    return this.get('documents').load().then((data) => {
      this.onLoaded(data);
      return this;
    }, (err) => {
      this.onError(err);
      return reject(err);
    });
  },

  save() {
    if(!this.get('isDirty') && this.get('isLoaded')) {
      return resolve(this);
    }

    this.onSaving();

    let data = this.serialize();
    return this.get('documents').save(data).then(() => {
      this.onSaved();
      return this;
    }, (err) => {
      this.onError(err);
      return reject(err);
    });
  },

  onLoaded(data) {
    this.deserialize(data);
    this._super();
  },

  deserialize(data) {
    data = data || {};
    this.get("admins").deserialize(data.admins);
    this.get("members").deserialize(data.members);
  },

  serialize() {
    return {
      admins: this.get("admins").serialize(),
      members: this.get("members").serialize()
    };
  },

  clear() {
    this.deserialize();
  }

});
