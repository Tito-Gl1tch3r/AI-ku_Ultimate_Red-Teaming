using MongoDB.Driver;
using MongoDDD.Core.Exceptions;
using System.Threading;
using System.Threading.Tasks;

namespace MongoDDD.Persistence.Queries
{
    public partial class DatabaseQuery<TData, TExternalData>
    {
        protected async Task<DatabaseDocument<TData, TExternalData>> FindOneAndUpdate(
            FilterDefinition<DatabaseDocument<TData, TExternalData>> filter,
            UpdateDefinition<DatabaseDocument<TData, TExternalData>> update,
            CancellationToken token,
            bool isUpsert = false)
        {
            filter = filter & NotDeleted;
            var options = new FindOneAndUpdateOptions<DatabaseDocument<TData, TExternalData>>
            {
                ReturnDocument = ReturnDocument.After,
                IsUpsert = isUpsert
            };
            var document = await _collection.FindOneAndUpdateAsync(filter, update, options, token);

            if (document is null)
            {
                throw new DoesNotExistException($"{typeof(TData).Name} that matches the requested query does not exist.");
            }

            return document;
        }

        protected async Task<UpdateResult> UpdateOne(
            FilterDefinition<DatabaseDocument<TData, TExternalData>> filter,
            UpdateDefinition<DatabaseDocument<TData, TExternalData>> update,
            CancellationToken token,
            bool isUpsert = false)
        {
            filter = filter & NotDeleted;
            var options = new UpdateOptions
            {
                IsUpsert = isUpsert
            };
            return await _collection.UpdateOneAsync(filter, update, options, token);
        }

        protected async Task<UpdateResult> UpdateMany(
            FilterDefinition<DatabaseDocument<TData, TExternalData>> filter,
            UpdateDefinition<DatabaseDocument<TData, TExternalData>> update,
            CancellationToken token,
            bool isUpsert = false)
        {
            filter = filter & NotDeleted;
            var options = new UpdateOptions
            {
                IsUpsert = isUpsert
            };
            return await _collection.UpdateManyAsync(filter, update, options, token);
        }
    }
}
