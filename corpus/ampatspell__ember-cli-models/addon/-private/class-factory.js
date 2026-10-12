import EmberObject from '@ember/object';
import { getOwner } from '@ember/application';
import normalizeIdentifier from './util/normalize-identifier';
import { assert } from './util/assert';
import factoryFor from './util/factory-for';

export default EmberObject.extend({

  _classes: null,

  init() {
    this._super(...arguments);
    this._classes = Object.create(null);
  },

  _lookupFactory(name) {
    let classes = this._classes;
    let factory = classes[name];
    if(!factory) {
      factory = factoryFor(this, name);
      if(factory) {
        classes[name] = factory;
      }
    }
    return factory;
  },

  _registerFactory(name, factory) {
    getOwner(this).register(name, factory);
  },

  _preparedBase({ fullName, normalizedName, registeredName, prepare }) {
    let factory = this._lookupFactory(registeredName);
    if(!factory) {
      let Base = this._lookupFactory(fullName);
      assert(`class for name '${fullName}' is not registered`, !!Base);
      let BaseClass = Base.class;
      if(prepare) {
        BaseClass = prepare(BaseClass, normalizedName);
      }
      this._registerFactory(registeredName, BaseClass);
      factory = this._lookupFactory(registeredName);
    }
    return factory;
  },

  _preparedVariant(base, { normalizedName, registeredName, prepare }) {
    let factory = this._lookupFactory(registeredName);
    if(!factory) {
      let Base = this._preparedBase(base);
      let BaseClass = Base.class;
      if(prepare) {
        BaseClass = prepare(BaseClass, base.normalizedName, normalizedName);
      }
      this._registerFactory(registeredName, BaseClass);
      factory = this._lookupFactory(registeredName);
    }
    return factory;
  },

  lookup({ prefix, name, prepare, variant }) {
    let normalizedName = normalizeIdentifier(name);
    let fullName = `${prefix}:${normalizedName}`;

    let base = {
      fullName,
      normalizedName,
      registeredName: `models:${prefix}/${normalizedName}`,
      prepare
    };

    let normalizedVariantName;
    if(variant && variant.name) {
      normalizedVariantName = normalizeIdentifier(variant.name);
    }

    let factory;

    if(normalizedVariantName) {
      factory = this._preparedVariant(base, {
        normalizedName: normalizedVariantName,
        registeredName: `models:${prefix}/${normalizedVariantName}/${normalizedName}`,
        prepare: variant.prepare
      });
    } else {
      factory = this._preparedBase(base);
    }

    return { normalizedName, normalizedVariantName, factory };
  }

});
