using Microsoft.Extensions.DependencyInjection;
using MongoDDD.Core.Queries;
using MongoDDD.Tests.SUT.Contract.Update;
using MongoDDD.Tests.SUT.Persistence.Data;
using MongoDDD.Tests.SUT.Persistence.Queries;

namespace MongoDDD.Tests.QueriesTests;

public class UpdateTests(TestsFixture fixture) : TestsBase(fixture)
{
    [Fact]
    public async Task UpdatingSingleDocuments()
    {
        // Arrange
        var productId = NextId;
        var productName = "White bread";
        var productPrice = 2.99M;
        var externalData = new ExternalData(4.5f);
        await Insert(productId, new("White bred", 1.99M), externalData);

        // Act
        var query = _sut.GetRequiredService<IWriteQuery<UpdateProduct>>();
        await query.Write(new(productId, productName, productPrice), CancellationToken);

        // Assert
        await Exists(productId, new(productName, productPrice), externalData, version: 2, modified: true);
    }

    [Fact]
    public async Task SilentlyUpdatingSingleDocuments()
    {
        // Arrange
        var productId = NextId;
        var productData = new ProductData("White bread", 2.99M);
        var reviewScore = 4.5f;
        await Insert(productId, productData, new ExternalData(4.0f));

        // Act
        var query = _sut.GetRequiredService<IWriteQuery<UpdateReviewScore>>();
        await query.Write(new(productId, reviewScore), CancellationToken);

        // Assert
        await Exists(productId, productData, new ExternalData(reviewScore));
    }

    [Fact]
    public async Task UpdatingAndRetrievingSingleDocuments()
    {
        // Arrange
        var productId = NextId;
        var productName = "White bread";
        var productPrice = 2.99M;
        var externalData = new ExternalData(4.5f);
        await Insert(productId, new("White bred", 1.99M), externalData);

        // Act
        var query = _sut.GetRequiredService<IWriteQuery<UpdateAndRetrieveProduct, UpdateAndRetrieveProduct.Result>>();
        var result = await query.Write(new(productId, productName, productPrice), CancellationToken);

        // Assert
        Assert.Equal(productId, result.Product.Id);
        Assert.Equal(productName, result.Product.Name);
        Assert.Equal(productPrice, result.Product.Price);
        await Exists(productId, new(productName, productPrice), externalData, version: 2, modified: true);
    }

    [Fact]
    public async Task UpdatingMultipleDocuments()
    {
        // Arrange
        var newPrice = 0.99M;
        string[] productIds = [NextId, NextId, NextId];
        ProductData[] productData = [new("White bread", 2.99M), new("Rye bread", 3.99M), new("Bread roll", 0.49M)];
        ExternalData[] externalData = [new(4.5f), new(4.7f), new(4.2f)];

        for (int i = 0; i < productIds.Length; i++)
        {
            await Insert(productIds[i], productData[i], externalData[i]);
        }

        // Act
        var query = _sut.GetRequiredService<IWriteQuery<UpdatePrices>>();
        await query.Write(new(productIds, newPrice), CancellationToken);

        // Assert
        for (int i = 0; i < productIds.Length; i++)
        {
            await Exists(productIds[i], productData[i] with { Price = newPrice }, externalData[i], version: 2, modified: true);
        }
    }

    protected override void RegisterServices(IServiceCollection services)
    {
        services.AddTransient<IWriteQuery<UpdateAndRetrieveProduct, UpdateAndRetrieveProduct.Result>, UpdateProductQuery>();
        services.AddTransient<IWriteQuery<UpdateProduct>, UpdateProductQuery>();
        services.AddTransient<IWriteQuery<UpdatePrices>, UpdatePricesQuery>();
        services.AddTransient<IWriteQuery<UpdateReviewScore>, UpdateReviewScoreQuery>();
    }
}
