using Microsoft.Extensions.DependencyInjection;
using MongoDDD.Core.Exceptions;
using MongoDDD.Core.Queries;
using MongoDDD.Tests.SUT.Contract.Update;
using MongoDDD.Tests.SUT.Core;
using MongoDDD.Tests.SUT.Persistence;
using MongoDDD.Tests.SUT.Persistence.Data;
using MongoDDD.Tests.SUT.Persistence.Queries;

namespace MongoDDD.Tests.RepositoryTests;

public class ProductRepositoryWithExternalDataTests(TestsFixture fixture) : TestsBase(fixture)
{
    [Fact]
    public async Task AddingAggregates()
    {
        // Arrange
        var productName = "White bread";
        var productPrice = 2.99M;
        var newProduct = new Product(NextId, productName, productPrice);

        // Act
        var products = _sut.GetRequiredService<IProductRepository>();
        await products.Add(newProduct, CancellationToken);

        // Assert
        await Exists(newProduct.Id, new(productName, productPrice), new ExternalData(0f));
    }

    [Fact]
    public async Task RejectingDuplicateAggregates()
    {
        // Arrange
        var productId = NextId;
        await Insert(productId, new("White bread", 2.99M));
        var newProduct = new Product(productId, "Rye bread", 3.99M);

        // Act
        var products = _sut.GetRequiredService<IProductRepository>();
        var addDuplicate = () => products.Add(newProduct, CancellationToken);

        // Assert
        await Assert.ThrowsAsync<AlreadyExistsException>(addDuplicate);
    }

    [Fact]
    public async Task ModifyingAggregates()
    {
        // Arrange
        var productId = NextId;
        var productName = "White bread";
        var productPrice = 2.99M;
        var externalData = new ExternalData(4.5f);
        await Insert(productId, new("White bred", 1.99M), externalData);

        // Act
        var products = _sut.GetRequiredService<IProductRepository>();
        var product = await products.Get(productId, CancellationToken);
        product.Rename(productName);
        product.SetPrice(productPrice);
        await products.Save(product, CancellationToken);

        // Assert
        await Exists(productId, new(productName, productPrice), externalData, version: 2, modified: true);
    }

    [Fact]
    public async Task ModifyingExternalData()
    {
        // Arrange
        var productId = NextId;
        var reviewScore = 4.5f;
        var productData = new ProductData("White bread", 2.99M);
        await Insert(productId, productData, new ExternalData(0f));

        // Act
        var reviewScoreUpdate = _sut.GetRequiredService<IWriteQuery<UpdateReviewScore>>();
        await reviewScoreUpdate.Write(new(productId, reviewScore), CancellationToken);

        // Assert
        await Exists(productId, productData, new ExternalData(reviewScore));
    }

    [Fact]
    public async Task RejectingConcurrentAggregateModifications()
    {
        // Arrange
        var productId = NextId;
        var productName = "White bread";
        var productPrice = 2.99M;
        var externalData = new ExternalData(4.5f);
        await Insert(productId, new("White bred", productPrice), externalData);

        // Act
        var products = _sut.GetRequiredService<IProductRepository>();

        var product = await products.Get(productId, CancellationToken);
        product.Rename(productName);

        var theSameProduct = await products.Get(productId, CancellationToken);
        theSameProduct.SetPrice(productPrice);

        await products.Save(product, CancellationToken);
        var saveTheSameProduct = () => products.Save(theSameProduct, CancellationToken);

        // Assert
        await Assert.ThrowsAsync<ConcurrentUpdateException>(saveTheSameProduct);
        await Exists(productId, new(productName, productPrice), externalData, version: 2, modified: true);
    }

    [Fact]
    public async Task RejectingNonExistentAggregateRetrievals()
    {
        // Act
        var products = _sut.GetRequiredService<IProductRepository>();
        var getProduct = () => products.Get(NextId, CancellationToken);

        // Assert
        await Assert.ThrowsAsync<DoesNotExistException>(getProduct);
    }

    [Fact]
    public async Task RemovingAggregates()
    {
        // Arrange
        var productId = NextId;
        var productData = new ProductData("White bread", 2.99M);
        var externalData = new ExternalData(4.5f);
        await Insert(productId, productData, externalData);

        // Act
        var products = _sut.GetRequiredService<IProductRepository>();
        await products.Remove(productId, CancellationToken);
        var getProduct = () => products.Get(productId, CancellationToken);

        // Assert
        await Assert.ThrowsAsync<DoesNotExistException>(getProduct);
        await Exists(productId, productData, externalData, deleted: true);
    }

    protected override void RegisterServices(IServiceCollection services)
    {
        services.AddTransient<IProductRepository, ProductRepositoryWithExternalData>();
        services.AddTransient<IWriteQuery<UpdateReviewScore>, UpdateReviewScoreQuery>();
    }
}
