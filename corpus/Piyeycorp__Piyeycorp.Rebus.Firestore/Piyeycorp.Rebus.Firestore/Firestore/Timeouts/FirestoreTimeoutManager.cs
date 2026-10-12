using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Google.Cloud.Firestore;
using Rebus.Logging;
using Rebus.Time;
using Rebus.Timeouts;

namespace Rebus.Firestore.Timeouts
{
    public class FirestoreTimeoutManager : ITimeoutManager
    {
        private readonly CollectionReference collectionReference;
        private readonly IRebusTime rebusTime;
        private readonly ILog log;

        public FirestoreTimeoutManager(IRebusTime rebusTime, FirestoreDb db, string collectionName, IRebusLoggerFactory rebusLoggerFactory)
        {
            if (db == null) throw new ArgumentNullException(nameof(db));
            if (collectionName == null) throw new ArgumentNullException(nameof(collectionName));
            if (rebusLoggerFactory == null) throw new ArgumentNullException(nameof(rebusLoggerFactory));

            this.rebusTime = rebusTime ?? throw new ArgumentNullException(nameof(rebusTime));
            collectionReference = db.Collection(collectionName);
            log = rebusLoggerFactory.GetLogger<FirestoreTimeoutManager>();
        }

        /// <inheritdoc />
        public async Task Defer(DateTimeOffset approximateDueTime, Dictionary<string, string> headers, byte[] body)
        {
            var document = new Dictionary<string, object>
            {
                { "DueTimeUtc", approximateDueTime.UtcDateTime },
                { "Headers", headers },
                { "Body", body },
            };

            await collectionReference.AddAsync(document).ConfigureAwait(false);
        }

        /// <inheritdoc />
        public async Task<DueMessagesResult> GetDueMessages()
        {
            const int maxDueTimeouts = 1000;
            var query = collectionReference
                .WhereLessThanOrEqualTo(new FieldPath("DueTimeUtc"), rebusTime.Now.UtcDateTime)
                .OrderBy(new FieldPath("DueTimeUtc")).Limit(maxDueTimeouts);
            var querySnapshot = await query.GetSnapshotAsync().ConfigureAwait(false);
            var documentSnapshots = querySnapshot.ToList();
            var dueMessages = documentSnapshots.Select(snapshot =>
            {
                var headers = snapshot.GetValue<Dictionary<string, string>>(new FieldPath("Headers"));
                var body = snapshot.GetValue<byte[]>(new FieldPath("Body"));

                return new DueMessage(headers, body, async () =>
                {
                    await snapshot.Reference.DeleteAsync().ConfigureAwait(false);
                });
            });

            return new DueMessagesResult(dueMessages);
        }
    }
}
