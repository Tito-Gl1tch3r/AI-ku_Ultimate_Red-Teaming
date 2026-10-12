using MongoDB.Driver;
using MongoDDD.Persistence.Configuration;
using MongoDDD.Persistence.Data;
using System;

namespace MongoDDD.Persistence.Queries
{
    public partial class DatabaseQuery<TData> : DatabaseQuery<TData, None>
    {
        public DatabaseQuery(MongoClient client, DatabaseSettings settings) : base(client, settings) { }
    }

    public partial class DatabaseQuery<TData, TExternalData>
    {
        protected readonly MongoClient _client;

        protected readonly IMongoCollection<DatabaseDocument<TData, TExternalData>> _collection;

        protected static FilterDefinitionBuilder<DatabaseDocument<TData, TExternalData>> Filter =>
        Builders<DatabaseDocument<TData, TExternalData>>.Filter;

        protected static SortDefinitionBuilder<DatabaseDocument<TData, TExternalData>> Sort =>
            Builders<DatabaseDocument<TData, TExternalData>>.Sort;

        protected static UpdateDefinitionBuilder<DatabaseDocument<TData, TExternalData>> SilentUpdate =>
            Builders<DatabaseDocument<TData, TExternalData>>.Update;

        protected static UpdateDefinition<DatabaseDocument<TData, TExternalData>> Update =>
            Builders<DatabaseDocument<TData, TExternalData>>.Update
                .Set(document => document.Modified, DateTime.UtcNow)
                .Inc(document => document.Version, 1);

        protected static FilterDefinition<DatabaseDocument<TData, TExternalData>> NotDeleted =>
            Filter.Eq(document => document.Deleted, null);

        public DatabaseQuery(MongoClient client, DatabaseSettings settings)
        {
            _client = client;
            _collection = _client
                .GetDatabase(settings.Database)
                .GetCollection<DatabaseDocument<TData, TExternalData>>(settings.Collection);
        }

        protected static FilterDefinition<DatabaseDocument<TData, TExternalData>> WithId(string id) =>
            Filter.Eq(document => document.Id, id);
    }
}
