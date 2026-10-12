import DataAdapter from '@ember/debug/data-adapter';
import { getStores } from './util/get-stores';
import { get, set, computed } from '@ember/object';
import { typeOf } from '@ember/utils';
import { A } from '@ember/array';
import { capitalize, dasherize } from '@ember/string';
import { addObserver, removeObserver } from '@ember/object/observers';
import TransientModel from './model/transient-model';
import BackedModel from './model/backed-model';

const __models_data_adapter_name = '__models_data_adapter_name';

const keyToColumDescription = key => {
  key = key.replace(/^(_)*/, '');
  return capitalize(dasherize(key)).replace(/-/g, ' ');
};

const stores = () => computed(function() {
  return getStores(this);
}).readOnly();

export default DataAdapter.extend({

  attributeLimit: 100,

  stores: stores(),

  _nameToClass(name) {
    let result = this._super(...arguments);
    if(typeOf(result) === 'class') {
      set(result, __models_data_adapter_name, name);
    }
    return result;
  },

  detect(typeClass) {
    if(typeClass === TransientModel || typeClass === BackedModel) {
      return;
    }

    if(!TransientModel.detect(typeClass) && !BackedModel.detect(typeClass)) {
      return;
    }

    let name = get(typeClass, __models_data_adapter_name);

    if(name) {
      let components = name.split('/');
      if(components.find(component => component.startsWith('-'))) {
        return;
      }
    }

    return true;
  },

  getRecords(modelClass) {
    return this.get('stores._context').identityByClass.get(modelClass);
  },

  columnsForType(typeClass) {
    let debug = A();
    while(typeClass) {
      let columns = get(typeClass, 'debugColumns') || [];
      debug.push(...columns.filter(column => !debug.includes(column)));
      typeClass = typeClass && typeClass.superclass;
    }
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
