using Microsoft.Extensions.DependencyInjection;
using MongoDDD.Core.Queries;
using MongoDDD.Tests.SUT.Contract.Delete;
using MongoDDD.Tests.SUT.Persistence.Data;
using MongoDDD.Tests.SUT.Persistence.Queries;

namespace MongoDDD.Tests.QueriesTests;

public class DeleteTests(TestsFixture fixture) : TestsBase(fixture)
{
    [Fact]
    public async Task DeletingSingleDocuments()
    {
        // Arrange
        var productId = NextId;
        var productData = new ProductData("White bread", 2.99M);
        var externalData = new ExternalData(4.5f);
        await Insert(productId, productData, externalData);

        // Act
        var query = _sut.GetRequiredService<IWriteQuery<DeleteProduct>>();
        await query.Write(new(productId), CancellationToken);

        // Assert
        await Exists(productId, productData, externalData, deleted: true);
    }

    [Fact]
    public async Task DeletingAndRetrievingSingleDocuments()
    {
        // Arrange
        var productId = NextId;
        var productData = new ProductData("White bread", 2.99M);
        var externalData = new ExternalData(4.5f);
        await Insert(productId, productData, externalData);

        // Act
        var query = _sut.GetRequiredService<IWriteQuery<DeleteAndRetrieveProduct, DeleteAndRetrieveProduct.Result>>();
        var result = await query.Write(new(productId), CancellationToken);

        // Assert
        Assert.Equal(productId, result.Product.Id);
        Assert.Equal(productData.Name, result.Product.Name);
        Assert.Equal(productData.Price, result.Product.Price);
        await Exists(productId, productData, externalData, deleted: true);
    }

    [Fact]
    public async Task DeletingMultipleDocuments()
    {
        // Arrange
        string[] productIds = [NextId, NextId, NextId];
        ProductData[] productData = [new("White bread", 2.99M), new("Rye bread", 3.99M), new("Bread roll", 0.49M)];
        ExternalData[] externalData = [new(4.5f), new(4.7f), new(4.2f)];

        for (int i = 0; i < productIds.Length; i++)
        {
            await Insert(productIds[i], productData[i], externalData[i]);
        }

        // Act
        var query = _sut.GetRequiredService<IWriteQuery<DeleteProducts>>();
        await query.Write(new(productIds), CancellationToken);

        // Assert
        for (int i = 0; i < productIds.Length; i++)
        {
            await Exists(productIds[i], productData[i], externalData[i], deleted: true);
        }
    }

    protected override void RegisterServices(IServiceCollection services)
    {
        services.AddTransient<IWriteQuery<DeleteAndRetrieveProduct, DeleteAndRetrieveProduct.Result>, DeleteProductQuery>();
        services.AddTransient<IWriteQuery<DeleteProduct>, DeleteProductQuery>();
        services.AddTransient<IWriteQuery<DeleteProducts>, DeleteProductsQuery>();
    }
}
