using MongoDB.Driver;
using MongoDDD.Core.Queries;
using MongoDDD.Persistence.Queries;
using MongoDDD.Persistence.Queries.Pagination;
using MongoDDD.Tests.SUT.Contract;
using MongoDDD.Tests.SUT.Contract.Read;
using MongoDDD.Tests.SUT.Persistence.Configuration;
using MongoDDD.Tests.SUT.Persistence.Data;

namespace MongoDDD.Tests.SUT.Persistence.Queries;

internal class FindProductsQuery(MongoClient client, ProductsDatabaseSettings settings)
    : DatabaseQuery<ProductData, ExternalData>(client, settings)
    , IReadQuery<GetProducts, GetProducts.Result>
    , IReadQuery<GetProductsPage, GetProductsPage.Result>
{
    public async Task<GetProducts.Result> Read(GetProducts queryData, CancellationToken token)
    {
        var filter = Filter.Gte(document => document.ExternalData.ReviewScore, queryData.MinimumScore);
        var result = await FindMany(filter, token);
        return new(result.Select(document => new ProductDto(
            document.Id, 
            document.Data.Name, 
            document.Data.Price, 
            document.ExternalData.ReviewScore)));
    }

    public async Task<GetProductsPage.Result> Read(GetProductsPage queryData, CancellationToken token)
    {
        var filter = Filter.Empty;
        var sort = Sort.Ascending(document => document.Data.Price);
        var pageInfo = new PageInfo(queryData.PageNumber, queryData.PageSize);
        var page = await FindMany(filter, sort, pageInfo, token);
        return new(
            page.Number, 
            page.OutOf, 
            page.Documents.Select(document => new ProductDto(
                document.Id, 
                document.Data.Name, 
                document.Data.Price, 
                document.ExternalData.ReviewScore)));
    }
}
