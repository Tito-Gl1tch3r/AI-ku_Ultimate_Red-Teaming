using Google.Api.Gax;
using Google.Cloud.Firestore;
using Rebus.Auditing.Sagas;
using Rebus.Firestore.Sagas;
using Rebus.Firestore.Sagas.Serialization;
using Rebus.Logging;
using Rebus.Tests.Contracts.Sagas;

namespace Rebus.Firestore.Tests.Sagas;

public class FirestoreSnapshotStorageFactory : ISagaSnapshotStorageFactory
{
    private const string CollectionName = "SagaSnaps";
    private readonly FirestoreDb db;

    public FirestoreSnapshotStorageFactory()
    {
        Environment.SetEnvironmentVariable("FIRESTORE_EMULATOR_HOST", "localhost:8080");
        db = new FirestoreDbBuilder
        {
            ProjectId = "piyeycorp.rebus.firestore.tests",
            EmulatorDetection = EmulatorDetection.EmulatorOnly
        }.Build();
    }

    public ISagaSnapshotStorage Create()
    {
        var serializer = new DefaultSagaSerializer();
        var consoleLoggerFactory = new ConsoleLoggerFactory(true);
        return new FirestoreSagaSnapshotStorage(db, CollectionName, serializer, consoleLoggerFactory);
    }

    public IEnumerable<SagaDataSnapshot> GetAllSnapshots()
    {
        var ret = db.Collection(CollectionName).GetSnapshotAsync().Result
            .Documents
            .Select(x => x.ConvertTo<SagaDataSnapshot>())
            .ToList();
        return ret;
    }
}