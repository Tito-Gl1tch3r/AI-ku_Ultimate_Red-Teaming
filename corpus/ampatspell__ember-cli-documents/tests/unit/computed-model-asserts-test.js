import EmberObject from '@ember/object';
import { assign } from '@ember/polyfills';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import { Model, model } from 'documents';

const Foo = Model.extend();

module('computed-model-asserts', {
  beforeEach() {
    this.register('model:foo', Foo);
    this.defaults = {
      owner: [],
      create(owner) {
        return {
          type: 'foo',     // required
          props: { owner } // optional, if provided, must be object
        };
      }
    };
    this.create = opts => {
      let Subject = EmberObject.extend({
        prop: model(assign({}, this.defaults, opts))
      });
      return Subject.create({ store: this.store, database: this.db }, this.ownerInjection);
    };
  }
});

test('create with defaults succeeds', function(assert) {
  let subject = this.create();
  let prop = subject.get('prop');
  assert.ok(prop);
  assert.ok(Foo.detectInstance(prop));
  assert.ok(prop.get('owner') === subject);
});

test('owner must be array', function(assert) {
  try {
    this.create({ owner: null });
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "owner must be array"
    });
  }
});

test('create must be function', function(assert) {
  let subject = this.create({ create: {} });
  try {
    subject.get('prop');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "create must be function"
    });
  }
});

test('create must be function', function(assert) {
  let subject = this.create({ create: null });
  try {
    subject.get('prop');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "create must be function"
    });
  }
});

test('create result must be object', function(assert) {
  let subject = this.create({ create: () => 1  });
  try {
    subject.get('prop');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "create function result must be object"
    });
  }
});

test('create result type must be object', function(assert) {
  let subject = this.create({ create: () => ({ type: {} })  });
  try {
    subject.get('prop');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "type in create function result must be string"
    });
  }
});

test('create result props must be object', function(assert) {
  let subject = this.create({ create: () => ({ type: 'foo', props: 1 })  });
  try {
    subject.get('prop');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "props in create function result must be object"
    });
  }
});

test('props are optional', function(assert) {
  let subject = this.create({ create: () => ({ type: 'foo' })  });
  assert.ok(subject.get('prop'));
});

test('create may return string', function(assert) {
  let subject = this.create({ create: () => 'foo' });
  assert.ok(Foo.detectInstance(subject.get('prop')));
});

test('create may return null', function(assert) {
  let subject = this.create({ create: () => null });
  assert.ok(!subject.get('prop'));
});
