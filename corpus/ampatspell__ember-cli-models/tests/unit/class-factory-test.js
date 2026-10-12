import EmberObject, { get } from '@ember/object';
import module from '../helpers/module-for-stores';
import { test } from '../helpers/qunit';

const Duck = EmberObject.extend();

module('class-factory', {
  beforeEach() {
    this.register('model:duck', Duck);
    this.register('model:yellow-duck', Duck);
    this.factory = this.stores._context.classFactory;
  }
});

test('it exists', function(assert) {
  assert.ok(this.factory);
});

test('lookup', function(assert) {
  let { normalizedName, factory: Model } = this.factory.lookup({
    prefix: 'model',
    name: 'duck',
    prepare: (Model, modelName) => {
      Model = Model.extend({ ok: true });
      Model.reopenClass({ modelName });
      return Model;
    }
  });
  assert.equal(normalizedName, 'duck');
  assert.ok(Model);
  assert.ok(!!Model.class);
  assert.ok(!!Model.create);
  let instance = Model.create();
  assert.equal(get(instance.constructor, 'modelName'), 'duck');
  assert.equal(instance.get('ok'), true);
  assert.ok(instance.toString().startsWith('<dummy@models:model/duck::'));
});

test('lookup returns same extended class', function(assert) {
  let { factory: Duck1 } = this.factory.lookup({
    prefix: 'model',
    name: 'duck',
    prepare: (Model, modelName) => {
      Model = Model.extend({ ok: true });
      Model.reopenClass({ modelName });
      return Model;
    }
  });

  let { factory: Duck2 } = this.factory.lookup({
    prefix: 'model',
    name: 'duck',
    prepare: () => {
      assert.ok(false, 'prepare called');
    }
  })

  assert.ok(Duck1 === Duck2);
});

test('lookup returns normalized name', function(assert) {
  let { normalizedName } = this.factory.lookup({
    prefix: 'model',
    name: 'YellowDuck',
    prepare: Model => Model
  });
  assert.equal(normalizedName, 'yellow-duck');
});

test('lookup with variant', function(assert) {
  let { factory } = this.factory.lookup({
    prefix: 'model',
    name: 'duck',
    prepare(Model) {
      return Model.extend({
        prepared: true
      });
    },
    variant: {
      name: 'nice',
      prepare(Model) {
        return Model.extend({
          variant: 'nice'
        });
      }
    }
  });
  let nice = factory.create();
  assert.equal(nice.get('prepared'), true);
  assert.equal(nice.get('variant'), 'nice');
  assert.ok(nice.toString().startsWith('<dummy@models:model/nice/duck::'));
});

test('variants are isolated', function(assert) {
  let create = key => this.factory.lookup({
    prefix: 'model',
    name: 'duck',
    prepare(Model) {
      return Model.extend({
        prepared: true
      });
    },
    variant: {
      name: key,
      prepare(Model) {
        return Model.extend({
          [key]: true
        });
      }
    }
  }).factory;

  let Yellow = create('yellow');
  let Green = create('green');
  let Base = create();

  let yellow = Yellow.create();
  let green = Green.create();
  let base = Base.create();

  assert.ok(Yellow.class.detectInstance(yellow));
  assert.ok(Base.class.detectInstance(yellow));
  assert.ok(!Green.class.detectInstance(yellow));

  assert.equal(yellow.get('yellow'), true);
  assert.equal(yellow.get('green'), undefined);

  assert.equal(green.get('yellow'), undefined);
  assert.equal(green.get('green'), true);

  assert.equal(base.get('yellow'), undefined);
  assert.equal(base.get('green'), undefined);
});

test('base is cached', function(assert) {
  let create = () => this.factory.lookup({
    prefix: 'model',
    name: 'duck',
    prepare(Model) {
      return Model.extend({
        prepared: true
      });
    }
  }).factory;
  assert.ok(create().class === create().class);
});

test('variant is cached', function(assert) {
  let create = key => this.factory.lookup({
    prefix: 'model',
    name: 'duck',
    prepare(Model) {
      return Model.extend({
        prepared: true
      });
    },
    variant: {
      name: key,
      prepare(Model) {
        return Model.extend({
          [key]: true
        });
      }
    }
  }).factory;

  assert.ok(create('yellow').class === create('yellow').class);
  assert.ok(create('green').class === create('green').class);
  assert.ok(create('yellow').class !== create('green').class);
});
