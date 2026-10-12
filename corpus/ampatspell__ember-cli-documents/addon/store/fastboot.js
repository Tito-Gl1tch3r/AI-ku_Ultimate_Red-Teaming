import Mixin from '@ember/object/mixin';
import { get } from '@ember/object';
import { getOwner } from '@ember/application';
import { allSettled } from 'rsvp';

export default Mixin.create({

  __fastbootDefer() {
    return allSettled([
      this.settle()
    ]);
  },

  __enableFastBoot() {
    let fastboot = getOwner(this).lookup('service:fastboot');
    if(!fastboot) {
      return;
    }

    let shoebox = fastboot.get('shoebox');
    if(!shoebox) {
      return;
    }

    let identifier = this.get('identifier');
    let store = this;

    if(fastboot.get('isFastBoot')) {
      fastboot.deferRendering(store.__fastbootDefer());
      shoebox.put(identifier, {
        get payload() {
          return store._serializeShoebox();
        }
      });
    } else {
      let object = shoebox.retrieve(identifier);
      if(!object) {
        return;
      }
      let payload = object.payload;
      if(!payload) {
        return;
      }
      store._deserializeShoebox(payload);
    }
  },

  _didInitialize() {
    let enabled = get(this, '_opts.fastboot');
    if(enabled) {
      this.__enableFastBoot();
    }
  }

});
