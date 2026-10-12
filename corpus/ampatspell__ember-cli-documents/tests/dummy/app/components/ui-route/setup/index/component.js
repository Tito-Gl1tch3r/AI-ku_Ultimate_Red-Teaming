import Component from '@ember/component';
import { readOnly } from '@ember/object/computed';
import layout from './template';

export default Component.extend({
  classNameBindings: [ ':ui-route', ':setup-index' ],
  layout,

  session: readOnly('state.session'),
  setup: readOnly('state.setup'),
  isAuthenticated: readOnly('session.isAuthenticated'),

  isBusy: false,
  isError: false,
  error: null,
  result: null,

  actions: {
    async setup() {
      if(this.get('isBusy')) {
        return;
      }
      this.setProperties({ isBusy: true, isError: false, error: null, result: null });
      try {
        if(this.get('session.isDirty')) {
          await this.get('session').save();
        }
        let result = await this.get('setup').perform();
        this.setProperties({ isBusy: false, result });
      } catch(error) {
        this.setProperties({ isBusy: false, isError: true, error });
      }
    }
  }

});
