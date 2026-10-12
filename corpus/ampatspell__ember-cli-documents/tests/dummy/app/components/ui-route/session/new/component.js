import Component from '@ember/component';
import { inject as service } from '@ember/service';
import layout from './template';

export default Component.extend({
  classNameBindings: [ ':ui-route', ':session-new' ],
  layout,

  router: service(),

  actions: {
    didSignIn() {
      this.get('router').transitionTo('index');
    }
  }

});
