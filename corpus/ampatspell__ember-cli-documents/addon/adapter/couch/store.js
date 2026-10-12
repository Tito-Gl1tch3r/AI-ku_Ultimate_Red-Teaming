import { getOwner } from '@ember/application';
import { reads } from '@ember/object/computed';
import { get, computed } from '@ember/object';
import Adapter from '../store';

const couch = () => computed('url', function() {
  let couches = getOwner(this).lookup('couch:couches');
  let opts = this.getProperties('url');
  return couches.couch(opts);
}).readOnly();

export default Adapter.extend({

  couch: couch(),

  url: reads('opts.url').readOnly(),

  storeDocuments() {
    return this.get('couch');
  },

  changesListener(opts) {
    let couch = this.get('couch');
    return couch.createChanges(opts);
  }

}).reopenClass({

  identifierFor(opts) {
    let url = get(opts, 'url');
    return `couch-${url}`;
  }

});
