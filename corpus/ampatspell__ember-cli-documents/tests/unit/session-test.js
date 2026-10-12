import configurations from '../helpers/configurations';
import { test } from '../helpers/qunit';

configurations(module => {

  let session;

  let admin = {
    name: 'admin',
    password: 'hello'
  };

  module('session', {
    async beforeEach() {
      await this.logout();
      session = this.store.get('session');
    }
  });

  test('exists', function(assert) {
    assert.ok(session);
  });

  test('session exists, initial state', function(assert) {
    assert.deepEqual({
      "error": null,
      "isDirty": false,
      "isError": false,
      "isLoaded": false,
      "isLoading": false,
      "isSaving": false
    }, session.get('state'));

    assert.deepEqual(session.get('roles'), []);
    assert.ok(session.get('name') === null);
    assert.ok(session.get('password') === null);
    assert.ok(session.get('isAuthenticated') === false);
  });

  test('session name and password marks dirty', function(assert) {
    assert.ok(session.get('isDirty') === false);

    session.set('name', admin.name);
    session.set('password', admin.password);

    assert.ok(session.get('isDirty') === true);
    assert.ok(session.get('isAuthenticated') === false);
  });

  test('session save succeeds', async function(assert) {
    session.set('name', admin.name);
    session.set('password', admin.password);

    let ret = await session.save();

    assert.ok(ret === session);

    assert.deepEqual({
      "error": null,
      "isDirty": false,
      "isError": false,
      "isLoaded": true,
      "isLoading": false,
      "isSaving": false
    }, session.get('state'));

    assert.ok(session.get('roles').indexOf('_admin') !== -1);
    assert.ok(session.get('password') === null);
    assert.ok(session.get('isAuthenticated') === true);
  });

  test('session save with args succeeds', async function(assert) {
    await session.save(admin.name, admin.password);
    assert.ok(session.get('isAuthenticated') === true);
  });

  test('session delete succeeds', async function(assert) {
    session.set('name', admin.name);
    session.set('password', admin.password);

    await session.save();
    let resp = await session.delete();

    assert.ok(resp === session);

    assert.deepEqual({
      "error": null,
      "isDirty": false,
      "isError": false,
      "isLoaded": false,
      "isLoading": false,
      "isSaving": false
    }, session.get('state'));

    assert.deepEqual(session.get('roles'), []);
    assert.ok(session.get('name') === null);
    assert.ok(session.get('password') === null);
    assert.ok(session.get('isAuthenticated') === false);
  });

  test('load anon', async function(assert) {
    let resp = await session.load();

    assert.ok(resp === session);
    assert.deepEqual({
      "error": null,
      "isDirty": false,
      "isError": false,
      "isLoaded": true,
      "isLoading": false,
      "isSaving": false
    }, session.get('state'));

    assert.deepEqual(session.get('roles'), []);

    assert.ok(session.get('name') === null);
    assert.ok(session.get('password') === null);
    assert.ok(session.get('isAuthenticated') === false);
  });

  test('load logged in', async function(assert) {
    await this.admin()
    await session.load();

    assert.deepEqual({
      "error": null,
      "isDirty": false,
      "isError": false,
      "isLoaded": true,
      "isLoading": false,
      "isSaving": false
    }, session.get('state'));
    assert.ok(session.get('roles').indexOf('_admin') !== -1);
    assert.ok(session.get('name') === admin.name);
    assert.ok(session.get('password') === null);
    assert.ok(session.get('isAuthenticated') === true);
  });

  test('login fails', async function(assert) {
    session.set('name', 'bogus');
    session.set('password', 'nothere');

    try {
      await session.save();
      assert.ok(false, 'should reject');
    } catch(err) {
      assert.deepEqual(err.toJSON(), {
        "error": "unauthorized",
        "reason": "Name or password is incorrect.",
        "status": 401
      });

      assert.deepEqual({
        "error": err,
        "isDirty": false,
        "isError": true,
        "isLoaded": true,
        "isLoading": false,
        "isSaving": false
      }, session.get('state'));

      assert.deepEqual(session.get('roles'), [], 'is ' + session.get('roles'));
      assert.ok(session.get('name') === 'bogus');
      assert.ok(session.get('password') === null);
      assert.ok(session.get('isAuthenticated') === false);
    }
  });

  test('login then second login logs out', async function(assert) {
    session.set('name', admin.name);
    session.set('password', admin.password);

    await session.save();
    assert.ok(session.get('isAuthenticated') === true);
    session.set('name', 'broken');

    try {
      await session.save();
      assert.ok(false, 'should reject');
    } catch(err) {
      assert.deepEqual({
        "error": "unauthorized",
        "reason": "Name or password is incorrect.",
        "status": 401
      }, err.toJSON());

      assert.deepEqual({
        "error": err,
        "isDirty": false,
        "isError": true,
        "isLoaded": true,
        "isLoading": false,
        "isSaving": false
      }, session.get('state'));

      assert.deepEqual(session.get('roles'), []);
      assert.ok(session.get('name') === 'broken');
      assert.ok(session.get('password') === null);
      assert.ok(session.get('isAuthenticated') === false);
    }
  });

  test('login and then load', async function(assert) {
    session.set('name', admin.name);
    session.set('password', admin.password);

    await session.save();
    assert.ok(session.get('isAuthenticated') === true);

    await session.load();

    assert.deepEqual({
      "error": null,
      "isDirty": false,
      "isError": false,
      "isLoaded": true,
      "isLoading": false,
      "isSaving": false
    }, session.get('state'));

    assert.ok(session.get('roles').indexOf('_admin') !== -1);
    assert.ok(session.get('name') === admin.name);
    assert.ok(session.get('password') === null);
    assert.ok(session.get('isAuthenticated') === true);
  });

  test('restore', async function(assert) {
    await this.admin();

    let promise = session.restore();
    assert.ok(promise === session.restore());
    await session.restore();

    assert.deepEqual({
      "error": null,
      "isDirty": false,
      "isError": false,
      "isLoaded": true,
      "isLoading": false,
      "isSaving": false
    }, session.get('state'));
    assert.ok(session.get('roles').indexOf('_admin') !== -1);
    assert.ok(session.get('name') === admin.name);
    assert.ok(session.get('password') === null);
    assert.ok(session.get('isAuthenticated') === true);
  });

  test('roles', async function(assert) {
    await this.admin();
    assert.deepEqual(session.get('roles'), []);

    session = await session.restore();
    assert.ok(session.get('roles').indexOf('_admin') !== -1);

    session = await session.load();
    assert.ok(session.get('roles').indexOf('_admin') !== -1);
  });

});
