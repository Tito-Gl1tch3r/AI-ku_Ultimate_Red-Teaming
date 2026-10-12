using System;
using Google.Apis.Auth.OAuth2;
using Google.Cloud.Firestore;
using Rebus.Config.Converters;
using Rebus.Firestore.Sagas;
using Rebus.Firestore.Sagas.Serialization;
using Rebus.Logging;
using Rebus.Sagas;

namespace Rebus.Config
{
    //
    // Summary:
    //     Configuration extensions for sagas
    public static class FirestoreSagaConfigurationExtensions
    {
        //
        // Summary:
        //     Configures Rebus to use Firestore to store sagas, using the tables specified
        //     to store data and indexed properties respectively.
        public static void StoreInFirestore(this StandardConfigurer<ISagaStorage> configurer, string projectId, string dataCollectionName)
        {
            if (configurer == null)
            {
                throw new ArgumentNullException(nameof(configurer));
            }

            if (projectId == null)
            {
                throw new ArgumentNullException(nameof(projectId));
            }

            if (dataCollectionName == null)
            {
                throw new ArgumentNullException(nameof(dataCollectionName));
            }

            configurer.Register(c =>
            {
                var rebusLoggerFactory = c.Get<IRebusLoggerFactory>();
                var serializer = c.Has<ISagaSerializer>(false) ? c.Get<ISagaSerializer>() : new DefaultSagaSerializer();

                var db = new FirestoreDbBuilder
                {
                    ProjectId = projectId,
                    ConverterRegistry = new ConverterRegistry { new FirestoreGuidConverter() }
                }.Build();

                return new FirestoreSagaStorage(db, dataCollectionName, serializer, rebusLoggerFactory);
            });
        }

        public static void StoreInFirestore(this StandardConfigurer<ISagaStorage> configurer, string projectId, ICredential credential, string dataCollectionName)
        {
            if (configurer == null)
            {
                throw new ArgumentNullException(nameof(configurer));
            }

            if (projectId == null)
            {
                throw new ArgumentNullException(nameof(projectId));
            }

            if (credential == null)
            {
                throw new ArgumentNullException(nameof(credential));
            }

            if (dataCollectionName == null)
            {
                throw new ArgumentNullException(nameof(dataCollectionName));
            }

            configurer.Register(c =>
            {
                var rebusLoggerFactory = c.Get<IRebusLoggerFactory>();
                var serializer = c.Has<ISagaSerializer>(false) ? c.Get<ISagaSerializer>() : new DefaultSagaSerializer();

                var db = new FirestoreDbBuilder
                {
                    ProjectId = projectId,
                    Credential = credential,
                    ConverterRegistry = new ConverterRegistry { new FirestoreGuidConverter() }
                }.Build();

                return new FirestoreSagaStorage(db, dataCollectionName, serializer, rebusLoggerFactory);
            });
        }

        public static void StoreInFirestore(this StandardConfigurer<ISagaStorage> configurer, string projectId, string keyPath, string dataCollectionName)
        {
            if (configurer == null)
            {
                throw new ArgumentNullException(nameof(configurer));
            }

            if (projectId == null)
            {
                throw new ArgumentNullException(nameof(projectId));
            }

            if (keyPath == null)
            {
                throw new ArgumentNullException(nameof(keyPath));
            }

            if (dataCollectionName == null)
            {
                throw new ArgumentNullException(nameof(dataCollectionName));
            }

            configurer.Register(c =>
            {
                var rebusLoggerFactory = c.Get<IRebusLoggerFactory>();
                var serializer = c.Has<ISagaSerializer>(false) ? c.Get<ISagaSerializer>() : new DefaultSagaSerializer();
                
                var db = new FirestoreDbBuilder
                {
                    ProjectId = projectId,
                    Credential = GoogleCredential.FromFile(keyPath),
                    ConverterRegistry = new ConverterRegistry { new FirestoreGuidConverter() }
                }.Build();

                return new FirestoreSagaStorage(db, dataCollectionName, serializer, rebusLoggerFactory);
            });
        }
    }
}
