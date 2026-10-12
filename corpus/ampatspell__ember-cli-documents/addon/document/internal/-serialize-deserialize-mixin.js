import { typeOf } from '@ember/utils';

import {
  toInternal,
  isInternal,
  isInternalObject,
  isInternalArray
} from 'documents/util/internal';

import { empty } from './-base';

const createDeserializeMixin = Class => class DeserializeMixin extends Class {

  _createInternalObject(parent, type) {
    return this.store._createInternalObject(parent, type);
  }

  _createInternalArray(parent, type) {
    return this.store._createInternalArray(parent, type);
  }

  _deserializeObjectValue(value, current, type) {
    let internal;
    let update;
    if(isInternalObject(current)) {
      internal = current;
      internal.withPropertyChanges(changed => internal.deserialize(value, type, changed), true);
      update = false;
    } else {
      this._detachInternal(current);
      internal = this._createInternalObject(this);
      internal.withPropertyChanges(changed => internal.deserialize(value, type, changed), false);
      update = true;
    }
    return { update, internal };
  }

  _deserializeArrayValue(value, current, type) {
    let internal;
    let update;
    if(isInternalArray(current)) {
      internal = current;
      internal.withPropertyChanges(changed => internal.deserialize(value, type, changed), true);
      update = false;
    } else {
      this._detachInternal(current);
      internal = this._createInternalArray(this);
      internal.withPropertyChanges(changed => internal.deserialize(value, type, changed), false);
      update = true;
    }
    return { update, internal };
  }

  _deserializeInternalArrayValue(value, current) {
    this._detachInternal(current);
    this._attachInternal(value);
    return { update: true, internal: value };
  }

  _deserializeInternalObjectValue(value, current) {
    this._detachInternal(current);
    this._attachInternal(value);
    return { update: true, internal: value };
  }

  _deserializePrimitiveValue(value, current) {
    this._detachInternal(current);
    return { update: true, internal: value };
  }

  _deserializeValue(value, current, type) {
    value = toInternal(value);

    if(current === value) {
      return {
        update: false,
        internal: value
      };
    }

    if(current === empty) {
      current = undefined;
    }

    if(isInternal(value)) {
      if(value.isDetached()) {
        if(isInternalObject(value)) {
          return this._deserializeInternalObjectValue(value, current);
        } else if(isInternalArray(value)) {
          return this._deserializeInternalArrayValue(value, current);
        }
      }
      value = value.serialize('model');
    }

    let valueType = typeOf(value);

    if(valueType === 'object') {
      return this._deserializeObjectValue(value, current, type);
    } else if(valueType === 'array') {
      return this._deserializeArrayValue(value, current, type);
    }

    return this._deserializePrimitiveValue(value, current, type);
  }

}

const createSerializeMixin = Class => class SerializeMixin extends Class {

  _serializeValue(value, type) {
    if(isInternal(value)) {
      value = value.serialize(type);
    }
    return value;
  }

}

export default Class => createSerializeMixin(createDeserializeMixin(Class));
