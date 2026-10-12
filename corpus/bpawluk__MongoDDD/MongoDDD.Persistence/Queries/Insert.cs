using MongoDB.Driver;
using MongoDDD.Core.Exceptions;
using MongoDDD.Persistence.Data;
using System.Threading;
using System.Threading.Tasks;

namespace MongoDDD.Persistence.Queries
{
    public partial class DatabaseQuery<TData> : DatabaseQuery<TData, None>
    {
        protected Task InsertOne(string id, TData data, CancellationToken token) => InsertOne(id, data, None.Value, token);
    }

    public partial class DatabaseQuery<TData, TExternalData>
    {
        protected async Task InsertOne(string id, TData data, TExternalData additionalData, CancellationToken token)
        {
            var document = new DatabaseDocument<TData, TExternalData>(id, data, additionalData);
            try
            {
                await _collection.InsertOneAsync(document, cancellationToken: token);
            }
            catch (MongoWriteException mongoWriteException)
            {
                if (mongoWriteException.WriteError.Category == ServerErrorCategory.DuplicateKey)
                {
                    throw new AlreadyExistsException($"{typeof(TData).Name} with ID {id} already exists.");
                }
                throw;
            }
        }
    }
}
