import DataAdapter from '@ember/debug/data-adapter';
import { getOwner } from '@ember/application';
import { get, set, computed } from '@ember/object';
import { addObserver, removeObserver } from '@ember/object/observers';
import { typeOf } from '@ember/utils';
import { A } from '@ember/array';
import { capitalize, dasherize } from '@ember/string';
import Model from './document/model';
import Models from './document/models';

const __documents_data_adapter_name = '__documents_data_adapter_name';

const keyToColumDescription = key => {
  key = key.replace(/^(_)*/, '');
  return capitalize(dasherize(key)).replace(/-/g, ' ');
};

export default DataAdapter.extend({

  stores: computed(function() {
    return getOwner(this).lookup('documents:stores');
  }),

  _nameToClass(name) {
    let result = this._super(...arguments);
    if(typeOf(result) === 'class') {
      set(result, __documents_data_adapter_name, name);
    }
    return result;
  },

  detect(typeClass) {
    if(typeClass === Model) {
      return;
    }
    if(typeClass === Models) {
      return;
    }
    if(!Model.detect(typeClass) && !Models.detect(typeClass)) {
      return;
    }
    let name = get(typeClass, __documents_data_adapter_name);
    if(name) {
      let components = name.split('/');
      if(components[components.length - 1].indexOf('-') === 0) {
        return;
      }
    }
    return true;
  },

  getRecords(modelClass) {
    return this.get('stores.modelsIdentity').modelsByClass(modelClass);
  },

  columnsForType(typeClass) {
    let debug = A(get(typeClass, 'debugColumns') || []);
    return debug.map(key => ({ name: key, desc: keyToColumDescription(key) }));
  },

  getRecordColumnValues(model) {
    let columns = this.columnsForType(model.constructor);
    let values = {};
    columns.forEach(col => {
      values[col.name] = model.get(col.name);
    });
    return values;
  },

  observeRecord(model, recordUpdated) {
    let release = A();
    let keys = A(this.columnsForType(model.constructor).map(col => col.name));
    keys.forEach(key => {
      let handler = () => recordUpdated(this.wrapRecord(model));
      addObserver(model, key, handler);
      release.push(() => removeObserver(model, key, handler));
    });
    return () => release.forEach(fn => fn());
  }

});
