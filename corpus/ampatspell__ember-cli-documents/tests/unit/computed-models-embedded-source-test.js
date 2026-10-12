import EmberObject from '@ember/object';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import { Models, Model, models, find } from 'documents';

const Ducks = Models.extend({

  source: find({
    query() {
    },
    matches() {
      return true;
    }
  }),

  model: {
    observe: [],
    create(doc) {
      return {
        type: 'duck',
        props: {
          doc
        }
      }
    }
  }

});

const Duck = Model.extend();

module('computed-models-embedded-source', {
  beforeEach() {
    this.register('model:ducks', Ducks);
    this.register('model:duck', Duck);
    this.create = () => {
      let Subject = EmberObject.extend({
        prop: models({
          create(owner) {
            let database = owner.get('database');
            return {
              type: 'ducks',
              props: { database }
            };
          }
        })
      });
      return Subject.create({ database: this.db }, this.ownerInjection);
    };
  }
});

test('create succeeds, source is observed', function(assert) {
  this.db.doc({ id: 'one' });
  let subject = this.create();
  let models = subject.get('prop');
  assert.ok(models);
  assert.equal(models.get('length'), 1);
  assert.deepEqual(models.mapBy('doc.id'), [ 'one' ]);
  this.db.doc({ id: 'two' });
  assert.deepEqual(models.mapBy('doc.id'), [ 'one', 'two' ]);
});

// TODO: models are observing just an array, there is no intermediate `models.source` observer.
// test('source recreate', function(assert) {
//   this.db.doc({ id: 'main:one' });
//   let subject = this.create();
//   let models = subject.get('prop');
//   assert.ok(models);
//   assert.deepEqual(models.mapBy('doc.id'), [ 'main:one' ]);
//   let second = this.store.database('second');
//   second.doc({ id: 'second:one' });
//   models.set('database', second);
//   assert.deepEqual(models.mapBy('doc.id'), [ 'second:one' ]);
// });
