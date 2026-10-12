import { A } from '@ember/array';
import EmberObject, { computed } from '@ember/object';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import { Model, Models } from 'documents';

const Duck = Model.extend();

const Ducks = Models.extend({

  source: computed(function() {
    return A();
  }).readOnly(),

  model: {
    observe: [ 'type' ],
    create(doc) {
      return {
        type: 'duck',
        props: { doc }
      };
    }
  }

});

module('models-embedded-source', {
  beforeEach() {
    this.register('model:ducks', Ducks);
    this.register('model:duck', Duck);
  }
});

test('create succeeds', function(assert) {
  let models = this.store.models({ type: 'ducks', source: null });
  assert.ok(models);
});

test('requires source', function(assert) {
  try {
    this.store.models({ type: '-ducks' });
    assert.ok(false, 'should throw');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "source array must be array or array proxy"
    });
  }
});

test('requires model object', function(assert) {
  try {
    this.store.models({ type: '-ducks', source: A([ EmberObject.create() ]) });
    assert.ok(false, 'should throw');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "model must be object"
    });
  }
});
