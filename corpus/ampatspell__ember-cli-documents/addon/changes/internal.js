import ModelMixin from 'documents/document/internal/-model-mixin';

export default ModelMixin(class Changes {

  constructor(store, opts) {
    this.store = store;
    this.opts = opts;
    this._adapter = null;
    this.state = {
      isError: false,
      error: null
    };
    this._adapterBindings = {
      data: this._onData.bind(this),
      error: this._onError.bind(this)
    };
  }

  _withAdapterBindings(cb) {
    let bindings = this._adapterBindings;
    for(let key in bindings) {
      cb(key, bindings[key]);
    }
  }

  adapter(create=true, notify=true) {
    let adapter = this._adapter;
    if(!adapter && create) {
      adapter = this._createAdapter(this.opts);
      this._adapter = adapter;
      this._withAdapterBindings((key, value) => adapter.on(key, value));
      if(notify) {
        let model = this.model(false);
        if(model) {
          model.notifyPropertyChange('_adapter');
        }
      }
    }
    return adapter;
  }

  _destroyAdapter() {
    let adapter = this.adapter(false, false);
    if(adapter) {
      this._withAdapterBindings((key, value) => adapter.off(key, value));
      adapter.destroy();
      this._adapter = null;
    }
  }

  destroy() {
    this._destroyAdapter();
    this._destroyModel();
  }

  //

  _setState(props) {
    let model = this.model(false);
    if(model) {
      model.beginPropertyChanges();
    }
    let state = this.state;
    for(let key in state) {
      let current = state[key];
      let value = props[key];
      if(current === value) {
        continue;
      }
      state[key] = value;
      if(model) {
        model.notifyPropertyChange(key);
      }
    }
    if(model) {
      model.endPropertyChanges();
    }
  }

  start() {
    this.adapter().start();
  }

  stop() {
    this.adapter().stop();
    this._setState({ isError: false, error: null });
  }

  restart() {
    this.adapter().restart();
  }

  suspend() {
    return this.adapter().suspend();
  }

  //

  _trigger(name, arg) {
    let model = this.model(false);
    if(!model) {
      return;
    }
    model.trigger(name, arg);
  }

  _onData(json) {
    let result = this._processData(json);
    if(!result) {
      return;
    }
    this._setState({ isError: false, error: null });
    this._trigger('change', result);
  }

  _onError(error) {
    this._setState({ isError: true, error });
    this._trigger('error', error);
  }

});
