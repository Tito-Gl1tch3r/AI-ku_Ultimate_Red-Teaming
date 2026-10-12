using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Google.Cloud.Firestore;
using Rebus.Auditing.Sagas;
using Rebus.Firestore.Sagas.Serialization;
using Rebus.Logging;
using Rebus.Sagas;

namespace Rebus.Firestore.Sagas
{
    public class FirestoreSagaSnapshotStorage : ISagaSnapshotStorage
    {
        private readonly CollectionReference collectionReference;
        private readonly ISagaSerializer sagaSerializer;
        private readonly ILog log;

        public FirestoreSagaSnapshotStorage(FirestoreDb db, string collectionName, ISagaSerializer sagaSerializer, IRebusLoggerFactory rebusLoggerFactory)
        {
            if (db == null) throw new ArgumentNullException(nameof(db));
            if (collectionName == null) throw new ArgumentNullException(nameof(collectionName));
            if (rebusLoggerFactory == null) throw new ArgumentNullException(nameof(rebusLoggerFactory));

            this.sagaSerializer = sagaSerializer?? throw new ArgumentNullException(nameof(sagaSerializer));
            collectionReference = db.Collection(collectionName);
            log = rebusLoggerFactory.GetLogger<FirestoreSagaSnapshotStorage>();
        }

        public async Task Save(ISagaData sagaData, Dictionary<string, string> sagaAuditMetadata)
        {
            var data = sagaSerializer.SerializeToString(sagaData);
            var document = new Dictionary<string, object>
            {
                { nameof(ISagaData.Id), sagaData.Id },
                { nameof(ISagaData.Revision), sagaData.Revision },
                { "Data", data},
                { "MetaData", sagaAuditMetadata }
            };
            await collectionReference.AddAsync(document).ConfigureAwait(false);
        }
    }
}
