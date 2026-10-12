using System;
using Google.Apis.Auth.OAuth2;
using Google.Cloud.Firestore;
using Rebus.Config.Converters;
using Rebus.Firestore.Timeouts;
using Rebus.Logging;
using Rebus.Time;
using Rebus.Timeouts;

namespace Rebus.Config
{
    public static class FirestoreTimeoutsConfigurationExtensions
    {
        public static void StoreInFirestore(this StandardConfigurer<ITimeoutManager> configurer, string projectId, string keyPath, string collectionName)
        {
            if (configurer == null) throw new ArgumentNullException(nameof(configurer));
            if (projectId == null) throw new ArgumentNullException(nameof(projectId));
            if (keyPath == null) throw new ArgumentNullException(nameof(keyPath));
            if (collectionName == null) throw new ArgumentNullException(nameof(collectionName));

            configurer.Register(c =>
            {
                var rebusLoggerFactory = c.Get<IRebusLoggerFactory>();
                var rebusTime = c.Get<IRebusTime>();
                var db = new FirestoreDbBuilder
                {
                    ProjectId = projectId,
                    Credential = GoogleCredential.FromFile(keyPath),
                    ConverterRegistry = new ConverterRegistry { new FirestoreGuidConverter() }
                }.Build();
                return new FirestoreTimeoutManager(rebusTime, db, collectionName, rebusLoggerFactory);  
            });
        }
    }
}
