using MongoDB.Driver;
using MongoDDD.Persistence.Data;
using System.Threading.Tasks;

namespace MongoDDD.Persistence.Configuration
{
    public abstract class DatabaseConfig<TData> : DatabaseConfig<TData, None>
    {
        protected DatabaseConfig(MongoClient client, DatabaseSettings settings) : base(client, settings) { }
    }

    public abstract class DatabaseConfig<TData, TExternalData>
    {
        private readonly MongoClient _client;
        private readonly DatabaseSettings _settings;

        protected static IndexKeysDefinitionBuilder<DatabaseDocument<TData, TExternalData>> Index =>
            Builders<DatabaseDocument<TData, TExternalData>>.IndexKeys;

        public DatabaseConfig(MongoClient client, DatabaseSettings settings)
        {
            _client = client;
            _settings = settings;
        }

        public abstract Task Configure();

        protected async Task DefineIndex(IndexKeysDefinition<DatabaseDocument<TData, TExternalData>> index, CreateIndexOptions? options = null)
        {
            var database = _client.GetDatabase(_settings.Database);
            var collection = database.GetCollection<DatabaseDocument<TData, TExternalData>>(_settings.Collection);
            var indexModel = new CreateIndexModel<DatabaseDocument<TData, TExternalData>>(index, options);
            await collection.Indexes.CreateOneAsync(indexModel);
        }
    }
}
