using MongoDB.Driver;

namespace MongoDDD.Persistence.Configuration
{
    public class DatabaseSettings
    {
        public string Connection { get; set; } = string.Empty;

        public string Database { get; set; } = string.Empty;

        public string Collection { get; set; } = string.Empty;

        public MongoClient CreateClient() => new MongoClient(Connection);
    }
}
