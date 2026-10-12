import configurations from '../helpers/configurations';
import { test } from '../helpers/qunit';

configurations(module => {

  let security;

  module('database-security', {
    async beforeEach() {
      await this.logout();
      security = this.db.get('security');
    }
  });

  test('exists', assert => {
    assert.ok(security);
  });

  test('load succeeds', async function(assert) {
    assert.deepEqual({
      "error": null,
      "isDirty": false,
      "isError": false,
      "isLoaded": false,
      "isLoading": false,
      "isSaving": false
    }, security.get('state'));

    let res = await security.load()

    assert.deepEqual({
      "error": null,
      "isDirty": false,
      "isError": false,
      "isLoaded": true,
      "isLoading": false,
      "isSaving": false
    }, security.get('state'));

    assert.ok(res === security);
  });

  test('save fails', async function(assert) {
    try {
      await security.save();
      assert.ok(false, 'should reject');
    } catch(err) {

      assert.deepEqual({
        "error": err,
        "isDirty": false,
        "isError": true,
        "isLoaded": false,
        "isLoading": false,
        "isSaving": false
      }, security.get('state'));

      if(err.reason === 'no_majority') {
        assert.deepEqual({
          "error": "error",
          "reason": "no_majority",
          "status": 500
        }, err.toJSON());
      } else {
        assert.deepEqual({
          "error": "unauthorized",
          "reason": "You are not a db or server admin.",
          "status": 401
        }, err.toJSON());
      }
    }
  });

  test('serialize empty', function(assert) {
    assert.deepEqual({
      "admins": {
        "names": [],
        "roles": []
      },
      "members": {
        "names": [],
        "roles": []
      }
    }, security.serialize());
  });

  test('serialize modified', function(assert) {
    security.get('admins.names').pushObject('ampatspell');
    security.get('members.roles').pushObject('guest');

    assert.deepEqual({
      "admins": {
        "names": ['ampatspell'],
        "roles": []
      },
      "members": {
        "names": [],
        "roles": ['guest']
      }
    }, security.serialize());
  });

  test('modify users and roles marks model dirty', function(assert) {
    assert.ok(security.get('isDirty') === false);
    security.get('admins.names').pushObject('admin');
    assert.ok(security.get('isDirty') === true);
  });

  test('save unsets isDirty', async function(assert) {
    await this.admin();
    security.onDirty();

    security = await security.save();
    assert.ok(security.get('isDirty') === false);
  });

  test('save serializes, load deserializes', async function(assert) {
    await this.admin();
    security.get('admins.roles').pushObject('random');

    assert.ok(security.get('isDirty') === true);
    assert.ok(security.get('isLoaded') === false);

    security = await security.save();
    assert.ok(security.get('isDirty') === false);
    assert.ok(security.get('isLoaded') === true);

    security = await security.load();

    assert.ok(security.get('isDirty') === false);
    assert.ok(security.get('isLoaded') === true);

    assert.deepEqual({
      "admins": {
        "names": [],
        "roles": [ "random" ]
      },
      "members": {
        "names": [],
        "roles": []
      }
    }, security.serialize());

    security.clear();

    assert.ok(security.get('isDirty') === true);
    assert.ok(security.get('isLoaded') === true);

    await security.save();
  });

  test('data clear', function(assert) {
    security.get('members.names').pushObject('zeeba');
    security.get('admins.names').pushObject('admin');

    security.get('state').isDirty = false;
    security.notifyPropertyChange('isDirty');

    security.get('admins').clear();

    assert.ok(security.get('isDirty') === true);
    assert.deepEqual({
      "admins": {
        "names": [],
        "roles": []
      },
      "members": {
        "names": [
          "zeeba"
        ],
        "roles": []
      }
    }, security.serialize());
  });

  test('save fails', async function(assert) {
    security.get('members.names').pushObject('zeeba');
    security.get('admins.names').pushObject('admin');
    try {
      await security.save();
      assert.ok(false, 'should reject');
    } catch(err) {
      assert.deepEqual({
        "error": err,
        "isDirty": true,
        "isError": true,
        "isLoaded": false,
        "isLoading": false,
        "isSaving": false
      }, security.get('state'));

      if(err.reason === 'no_majority') {
        assert.deepEqual({
          "error": "error",
          "reason": "no_majority",
          "status": 500
        }, err.toJSON());
      } else {
        assert.deepEqual({
          "error": "unauthorized",
          "reason": "You are not a db or server admin.",
          "status": 401
        }, err.toJSON());
      }
    }
  });

});
