import EmberObject from '@ember/object';
import { assign } from '@ember/polyfills';
import module from '../helpers/module-for-db';
import { test } from '../helpers/qunit';
import { first } from 'documents';

module('computed-first-asserts', {
  beforeEach() {
    this.defaults = {
      database: 'database',
      autoload: true,
      owner: [],
      document: [],
      query() {
      },
      matches() {
        return true;
      }
    };
    this.create = opts => {
      let Subject = EmberObject.extend({
        prop: first(assign({}, this.defaults, opts))
      });
      return Subject.create({ database: this.db });
    };
  }
});

test('create with defaults succeeds', function(assert) {
  let subject = this.create();
  let prop = subject.get('prop');
  assert.ok(prop);
});

test('database should be string', function(assert) {
  try {
    this.create({ database: false });
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "database must be string"
    });
  }
});

test('autoload must be boolean', function(assert) {
  let subject = this.create({ autoload: {} });
  try {
    subject.get('prop');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "autoload must be boolean"
    });
  }
});

test('owner must be array', function(assert) {
  let subject = this.create({ owner: null });
  try {
    subject.get('prop');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "owner must be array"
    });
  }
});

test('document must be array', function(assert) {
  let subject = this.create({ document: null });
  try {
    subject.get('prop');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "document must be array"
    });
  }
});

test('query must be function', function(assert) {
  let subject = this.create({ query: {} });
  try {
    subject.get('prop');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "query must be function"
    });
  }
});

test('matches must be function', function(assert) {
  let subject = this.create({ matches: {} });
  try {
    subject.get('prop');
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "matches must be function"
    });
  }
});

test('query result must be object or falsy', async function(assert) {
  let subject = this.create({ query: () => 1 });
  let prop = subject.get('prop');

  try {
    await prop.load();
  } catch(err) {
    assert.deepEqual(err.toJSON(), {
      "error": "assertion",
      "reason": "query function result must be object or falsy"
    });
  }
});
