using MongoDB.Driver;
using MongoDDD.Core.Queries;
using MongoDDD.Persistence.Queries;
using MongoDDD.Tests.SUT.Contract.Update;
using MongoDDD.Tests.SUT.Persistence.Configuration;
using MongoDDD.Tests.SUT.Persistence.Data;

namespace MongoDDD.Tests.SUT.Persistence.Queries;

internal class UpdateProductQuery(MongoClient client, ProductsDatabaseSettings settings)
    : DatabaseQuery<ProductData, ExternalData>(client, settings)
    , IWriteQuery<UpdateAndRetrieveProduct, UpdateAndRetrieveProduct.Result>
    , IWriteQuery<UpdateProduct>
{
    public async Task<UpdateAndRetrieveProduct.Result> Write(UpdateAndRetrieveProduct queryData, CancellationToken token)
    {
        var filter = WithId(queryData.Id);
        var update = Update
            .Set(document => document.Data.Name, queryData.Name)
            .Set(document => document.Data.Price, queryData.Price);
        var document = await FindOneAndUpdate(filter, update, token);
        return new(new(document.Id, document.Data.Name, document.Data.Price, document.ExternalData.ReviewScore));
    }

    public async Task Write(UpdateProduct queryData, CancellationToken token)
    {
        var filter = WithId(queryData.Id);
        var update = Update
            .Set(document => document.Data.Name, queryData.Name)
            .Set(document => document.Data.Price, queryData.Price);
        await UpdateOne(filter, update, token);
    }
}