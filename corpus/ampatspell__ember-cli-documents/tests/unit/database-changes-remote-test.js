import configurations from '../helpers/configurations';
import { later } from '../helpers/run';
import { test } from '../helpers/qunit';

configurations(module => {

  module('database-changes-remote', {
    beforeEach() {
      return this.recreate();
    }
  });

  test('start, suspend, stop changes', async function(assert) {
    let changes = this.db.changes({ feed: this.config.feed });

    changes.start();

    assert.deepEqual(changes.get('state'), {
      "error": null,
      "isError": false,
      "isStarted": true,
      "isSuspended": false
    });

    changes.suspend();

    assert.deepEqual(changes.get('state'), {
      "error": null,
      "isError": false,
      "isStarted": true,
      "isSuspended": true
    });

    changes.stop();

    assert.deepEqual(changes.get('state'), {
      "error": null,
      "isError": false,
      "isStarted": false,
      "isSuspended": true
    });

    await this.docs.save({ _id: 'foof' });
  });

  test('changes are pushed to db', async function(assert) {
    let events = [];
    let changes = this.db.changes({ feed: this.config.feed });

    changes.on('error', err => {
      throw err;
    });

    changes.on('change', push => {
      events.push({
        id: push.id,
        deleted: push.isDeleted,
        exists: !!push.get({ deleted: true })
      });
    });

    changes.start();

    await later(300);

    let json = await this.docs.save({ _id: 'one', type: 'duck' });

    await later(500);

    await this.docs.delete('one', json.rev);

    await later(500);

    assert.deepEqual(events, [
      {
        "deleted": false,
        "exists": true,
        "id": "one"
      },
      {
        "deleted": true,
        "exists": true,
        "id": "one"
      }
    ]);

    changes.stop();

    let doc = this.db.existing('one', { deleted: true });
    assert.deepEqual_(doc.serialize('document'), {
      "_id": "one",
      "_rev": "ignored",
      "type": "duck"
    });

    await this.docs.save({ _id: 'foof' });
  });

  test('save suspends changes', async function(assert) {
    let doc = this.db.doc({ _id: 'hey' });

    let events = [];
    let changes = this.db.changes({ feed: this.config.feed });

    changes.on('error', err => {
      throw err;
    });

    changes.on('change', push => {
      events.push({
        id: push.id,
        deleted: push.isDeleted,
        exists: !!push.get({ deleted: true })
      });
    });

    changes.start();

    await later(300);

    let promise = doc.save();

    await later();

    assert.ok(changes.get('isSuspended'));

    await promise;

    assert.ok(!changes.get('isSuspended'));

    await this.docs.save({ _id: 'foof' });
  });

});
