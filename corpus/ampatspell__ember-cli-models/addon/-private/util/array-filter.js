import { A } from '@ember/array';
import ArrayObserver from './array-observer';
import ObjectObserver from './object-observer';
import { maybe as maybeCall } from './function-call';

export default class ArrayFilter {

  // {
  //   array: { object, observe, matches }
  //   owner: { object, observe }
  //   delegate: { target, ... }
  // }
  constructor(opts) {
    this.opts = opts;
    this._content = null;
  }

  get content() {
    let content = this._content;
    if(!content) {
      content = A(this._rematch());
      this._startObserving();
      this._content = content;
    }
    return content;
  }

  //

  _notifyDelegate(name, ...args) {
    let delegate = this.opts.delegate;
    maybeCall(delegate.target, delegate[name], ...args);
  }

  //

  _matches(model) {
    if(model.isDestroying) {
      return false;
    }
    let { array, owner } = this.opts;
    let object = owner.object;
    return array.matches(model, object);
  }

  _match(models) {
    return models.filter(model => this._matches(model));
  }

  _rematch() {
    return this._match(this.opts.array.object);
  }

  //

  _sourceArrayAdded(models) {
    let matched = this._match(models);
    if(matched.length) {
      let content = this.content;
      let fresh = matched.filter(model => !content.includes(model));
      if(fresh.length) {
        content.pushObjects(fresh);
        this._notifyDelegate('added', fresh);
      }
    }
  }

  _sourceArrayRemoved(models) {
    if(models.length) {
      let content = this.content;
      let fresh = models.filter(model => content.includes(model));
      if(fresh.length) {
        this.content.removeObjects(fresh);
        this._notifyDelegate('removed', fresh);
      }
    }
  }

  _sourceArrayUpdated(model) {
    let content = this.content;
    if(this._matches(model)) {
      if(!content.includes(model)) {
        content.pushObject(model);
        this._notifyDelegate('added', [ model ]);
      }
    } else {
      if(content.includes(model)) {
        content.removeObject(model);
        this._notifyDelegate('removed', [ model ]);
      }
    }
  }

  //

  _ownerUpdated() {
    let models = this._rematch();
    let remove = [];

    let content = this.content;

    content.forEach(model => {
      if(!models.includes(model)) {
        remove.push(model);
      }
      models.removeObject(model);
    });

    content.removeObjects(remove);
    content.pushObjects(models);

    this._notifyDelegate('replaced', remove, models);
  }

  //

  _startObservingSource() {
    if(this._source) {
      return;
    }

    let { object: array, observe } = this.opts.array;

    this._source = new ArrayObserver({
      array,
      observe,
      delegate: {
        target:  this,
        added:   this._sourceArrayAdded,
        removed: this._sourceArrayRemoved,
        updated: this._sourceArrayUpdated
      }
    });
  }

  _stopObservingSource() {
    let source = this._source;
    if(source) {
      source.destroy();
      this._source = null;
    }
  }

  //

  _startObservingOwner() {
    if(this._object) {
      return;
    }

    let { object, observe } = this.opts.owner;

    this._owner = new ObjectObserver({
      object,
      observe,
      delegate: {
        target: this,
        updated: this._ownerUpdated
      }
    });
  }

  _stopObservingOwner() {
    let owner = this._owner;
    if(owner) {
      owner.destroy();
      this._owner = null;
    }
  }

  //

  _startObserving() {
    this._startObservingSource();
    this._startObservingOwner();
  }

  _stopObserving() {
    this._stopObservingSource();
    this._stopObservingOwner();
  }

  destroy() {
    this._stopObserving();
  }

}
