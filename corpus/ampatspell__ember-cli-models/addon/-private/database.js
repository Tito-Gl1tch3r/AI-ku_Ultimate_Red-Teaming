import EmberObject from '@ember/object';
import { Context, makeContextMixin, adapter, identity } from './util/make-context-mixin';
import ExistingMixin from './existing-mixin';

class DatabaseContext extends Context {
  constructor(owner) {
    super(owner, owner.store._context);
    this.adapter = null;
    this.internalModelManager = this.create('models:internal-model-manager');
    this.internalModelIdentity = this.create('models:internal-model-identity');
    this.internalModelFactory = this.parent.internalModelFactory;
    this.modelClassFactory = this.parent.modelClassFactory;
    this.modelFactory = this.parent.modelFactory;
  }
  get identity() {
    let identity = this._identity;
    if(!identity) {
      identity = this.create('models:database-identity', { content: this.internalModelIdentity._identity.all });
      this._identity = identity;
    }
    return identity;
  }
  start() {
    this.adapter.start();
  }
  destroy() {
    this.adapter.destroy();
  }
}

const DatabaseContextMixin = makeContextMixin(DatabaseContext);

export default EmberObject.extend(DatabaseContextMixin, ExistingMixin, {

  store: null,
  identifier: null,

  adapter: adapter(),
  identity: identity(),

  model() {
    return this._context.internalModelManager.model(...arguments);
  },

  find() {
    return this._context.internalModelManager.find(...arguments);
  },

  first() {
    return this._context.internalModelManager.first(...arguments);
  },

  compact() {
    return this._context.internalModelManager.compact();
  },

  modelNameForType(type) {
    return this.get('adapter').modelNameForType(type);
  },

  toStringExtension() {
    let store = this.get('store.identifier');
    let identifier = this.get('identifier');
    return `${store}/${identifier}`;
  }

});
