using System;
using Google.Apis.Auth.OAuth2;
using Google.Cloud.Firestore;
using Rebus.Auditing.Sagas;
using Rebus.Config.Converters;
using Rebus.Firestore.Sagas;
using Rebus.Firestore.Sagas.Serialization;
using Rebus.Logging;

namespace Rebus.Config
{
    public static class FirestoreSagaSnapshotsConfigurationExtensions
    {
        public static void StoreInFirestore(this StandardConfigurer<ISagaSnapshotStorage> configurer, string projectId, string keyPath, string collectionName)
        {
            if (configurer == null) throw new ArgumentNullException(nameof(configurer));
            if (projectId == null) throw new ArgumentNullException(nameof(projectId));
            if (keyPath == null) throw new ArgumentNullException(nameof(keyPath));
            if (collectionName == null) throw new ArgumentNullException(nameof(collectionName));

            configurer.Register(c =>
            {
                var serializer = c.Has<ISagaSerializer>(false) ? c.Get<ISagaSerializer>() : new DefaultSagaSerializer();
                var rebusLoggerFactory = c.Get<IRebusLoggerFactory>();
                var db = new FirestoreDbBuilder
                {
                    ProjectId = projectId,
                    Credential = GoogleCredential.FromFile(keyPath),
                    ConverterRegistry = new ConverterRegistry { new FirestoreGuidConverter() }
                }.Build();
                return new FirestoreSagaSnapshotStorage(db, collectionName, serializer, rebusLoggerFactory);
            });
        }
    }
}
