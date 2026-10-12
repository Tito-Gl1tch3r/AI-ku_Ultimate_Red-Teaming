using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Google.Cloud.Firestore;
using Rebus.Firestore.Sagas.Serialization;
using Rebus.Logging;
using Rebus.Sagas;

namespace Rebus.Firestore.Sagas
{
    public class FirestoreSagaStorage : ISagaStorage
    {
        private readonly CollectionReference collectionReference;
        private readonly ISagaSerializer sagaSerializer;
        private readonly ILog log;

        public FirestoreSagaStorage(FirestoreDb db, string collectionName, ISagaSerializer sagaSerializer, IRebusLoggerFactory rebusLoggerFactory)
        {
            if (db == null) throw new ArgumentNullException(nameof(db));
            if (collectionName == null) throw new ArgumentNullException(nameof(collectionName));
            if (rebusLoggerFactory == null) throw new ArgumentNullException(nameof(rebusLoggerFactory));

            this.sagaSerializer = sagaSerializer ?? throw new ArgumentNullException(nameof(sagaSerializer));
            collectionReference = db.Collection(collectionName);
            log = rebusLoggerFactory.GetLogger<FirestoreSagaStorage>();
        }

        public async Task<ISagaData> Find(Type sagaDataType, string propertyName, object propertyValue)
        {
            if (sagaDataType == null) throw new ArgumentNullException(nameof(sagaDataType));
            if (propertyName == null) throw new ArgumentNullException(nameof(propertyName));
            if (propertyValue == null) throw new ArgumentNullException(nameof(propertyValue));

            DocumentSnapshot documentSnapshot;
            if (propertyName == nameof(ISagaData.Id))
            {
                var document = collectionReference.Document(propertyValue.ToString());
                documentSnapshot = await document.GetSnapshotAsync();
            }
            else
            {
                var query = collectionReference.WhereEqualTo(propertyName, propertyValue);
                var querySnapshot = await query.GetSnapshotAsync().ConfigureAwait(false);
                documentSnapshot = querySnapshot.FirstOrDefault();
            }

            if (documentSnapshot is null || !documentSnapshot.Exists) return null;
            documentSnapshot.TryGetValue("data", out string data);

            return sagaSerializer.DeserializeFromString(sagaDataType, data);
        }

        public async Task Insert(ISagaData sagaData, IEnumerable<ISagaCorrelationProperty> correlationProperties)
        {
            if (sagaData.Id == Guid.Empty)
            {
                throw new InvalidOperationException($"Attempted to insert saga data {sagaData.GetType()} without an ID");
            }

            if (sagaData.Revision != 0)
            {
                throw new InvalidOperationException($"Attempted to insert saga data with ID {sagaData.Id} and revision {sagaData.Revision}, but revision must be 0 on first insert!");
            }

            var data = sagaSerializer.SerializeToString(sagaData);
            var document = new Dictionary<string, object>
            {
                { nameof(ISagaData.Revision), sagaData.Revision },
                { "data", data }
            };

            if (correlationProperties != null)
            {
                var sagaDataType = sagaData.GetType();
                foreach (var sagaCorrelationProperty in correlationProperties)
                {
                    var propertyInfo = sagaDataType.GetProperty(sagaCorrelationProperty.PropertyName);
                    if (propertyInfo == null) continue;
                    var value = propertyInfo.GetValue(sagaData);
                    document.Add(sagaCorrelationProperty.PropertyName, value);
                }
            }

            await collectionReference.Document(sagaData.Id.ToString()).CreateAsync(document).ConfigureAwait(false);

        }

        public async Task Update(ISagaData sagaData, IEnumerable<ISagaCorrelationProperty> correlationProperties)
        {
            var query = collectionReference
                .WhereEqualTo(FieldPath.DocumentId, $"{sagaData.Id}")
                .WhereEqualTo(nameof(ISagaData.Revision), sagaData.Revision);
            var querySnapshot = await query.GetSnapshotAsync().ConfigureAwait(false);
            var documentSnapshot = querySnapshot.FirstOrDefault();
            if (documentSnapshot is null || !documentSnapshot.Exists)
            {
                return;
            }

            sagaData.Revision++;
            var result = await documentSnapshot.Reference.UpdateAsync("Revision", sagaData.Revision);
            Console.WriteLine($"Update time: {result.UpdateTime}");
        }

        public async Task Delete(ISagaData sagaData)
        {
            var document = collectionReference.Document($"{sagaData.Id}");
            await document.DeleteAsync();
            sagaData.Revision++;
        }
    }
}
