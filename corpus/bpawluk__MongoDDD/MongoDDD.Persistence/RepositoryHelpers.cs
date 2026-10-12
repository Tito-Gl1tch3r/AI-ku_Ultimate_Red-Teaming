using MongoDB.Driver;
using MongoDDD.Core;
using MongoDDD.Core.Exceptions;
using System.Threading;
using System.Threading.Tasks;

namespace MongoDDD.Persistence
{
    public abstract partial class Repository<TAggregateRoot, TAggregateState, TAggregateRootData, TExternalData> : IRepository<TAggregateRoot, TAggregateState>
        where TAggregateRoot : AggregateRoot<TAggregateState>
    {
        private static FilterDefinitionBuilder<DatabaseDocument<TAggregateRootData, TExternalData>> Filter =>
            Builders<DatabaseDocument<TAggregateRootData, TExternalData>>.Filter;

        private static UpdateDefinitionBuilder<DatabaseDocument<TAggregateRootData, TExternalData>> Update =>
            Builders<DatabaseDocument<TAggregateRootData, TExternalData>>.Update;

        private static FilterDefinition<DatabaseDocument<TAggregateRootData, TExternalData>> NotDeleted =>
            Filter.Eq(document => document.Deleted, null);

        private static FilterDefinition<DatabaseDocument<TAggregateRootData, TExternalData>> WithId(string id) =>
            Filter.Eq(document => document.Id, id);

        private static FilterDefinition<DatabaseDocument<TAggregateRootData, TExternalData>> WithVersion(int version) =>
            Filter.Eq(document => document.Version, version);

        private async Task<DatabaseDocument<TAggregateRootData, TExternalData>> GetDocument(string id, CancellationToken token)
        {
            var filter = WithId(id) & NotDeleted;
            var document = await _collection.Find(filter).Limit(1).SingleOrDefaultAsync(token);
            return document ?? throw new DoesNotExistException($"{typeof(TAggregateRoot).Name} with ID {id} does not exist.");
        }
    }
}
