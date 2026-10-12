using Google.Cloud.Firestore;
using Moq;
using Rebus.Firestore.Sagas;
using Rebus.Firestore.Sagas.Serialization;
using Rebus.Logging;
using Rebus.Sagas;
using Rebus.Tests.Contracts.Sagas;

namespace Rebus.Firestore.Tests.Sagas;

public class FirestoreSagaStorageFactory : ISagaStorageFactory
{
    private const string CollectionName = "SagaData";

    public ISagaStorage GetSagaStorage()
    {
        var db = Mock.Of<FirestoreDb>();
        var serializer = new DefaultSagaSerializer();
        var consoleLoggerFactory = new ConsoleLoggerFactory(true);
        var storage = new FirestoreSagaStorage(db, CollectionName, serializer, consoleLoggerFactory);
        return storage;
    }

    public void CleanUp()
    { }
}