import Ember from 'ember';
import { Promise } from 'rsvp';

export default {
  name: 'dummy:dev',
  initialize(app) {
    window.Promise = Promise;

    let stores = app.lookup('documents:stores');
    let state = stores.model('state');

    app.register('service:state', state, { instantiate: false });

    [ 'route', 'component' ].forEach(name => app.inject(name, 'state', 'service:state'));

    app.inject('component', 'router', 'router:main');

    if(Ember.testing) {
      return;
    }

    let props = state.getProperties('stores', 'store', 'database');
    for(let key in props) {
      window[key] = props[key];
    }
  }
};
