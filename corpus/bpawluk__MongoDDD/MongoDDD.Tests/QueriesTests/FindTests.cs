using Microsoft.Extensions.DependencyInjection;
using MongoDDD.Core.Exceptions;
using MongoDDD.Core.Queries;
using MongoDDD.Tests.SUT.Contract.Delete;
using MongoDDD.Tests.SUT.Contract.Read;
using MongoDDD.Tests.SUT.Persistence.Data;
using MongoDDD.Tests.SUT.Persistence.Queries;

namespace MongoDDD.Tests.QueriesTests;

public class FindTests(TestsFixture fixture) : TestsBase(fixture)
{
    [Fact]
    public async Task FindingSingleDocuments()
    {
        // Arrange
        var productId = NextId;
        var productData = new ProductData("White bread", 2.99M);
        var externalData = new ExternalData(4.5f);
        await Insert(productId, productData, externalData);

        // Act
        var query = _sut.GetRequiredService<IReadQuery<GetProduct, GetProduct.Result>>();
        var result = await query.Read(new(productId), CancellationToken);

        // Assert
        Assert.Equal(productId, result.Product.Id);
        Assert.Equal(productData.Name, result.Product.Name);
        Assert.Equal(productData.Price, result.Product.Price);
        Assert.Equal(externalData.ReviewScore, result.Product.ReviewScore);
    }

    [Fact]
    public async Task RejectingNonExistentDocumentRetrievals()
    {
        // Act
        var query = _sut.GetRequiredService<IReadQuery<GetProduct, GetProduct.Result>>();
        var findProduct = () => query.Read(new(NextId), CancellationToken);

        // Assert
        await Assert.ThrowsAsync<DoesNotExistException>(findProduct);
    }

    [Fact]
    public async Task RejectingDeletedDocumentRetrievals()
    {
        // Arrange
        var productId = NextId;
        await Insert(productId, new("White bread", 2.99M), new(4.5f));

        // Act
        var deleteQuery = _sut.GetRequiredService<IWriteQuery<DeleteProduct>>();
        await deleteQuery.Write(new(productId), CancellationToken);

        var findQuery = _sut.GetRequiredService<IReadQuery<GetProduct, GetProduct.Result>>();
        var findProduct = () => findQuery.Read(new(productId), CancellationToken);

        // Assert
        await Assert.ThrowsAsync<DoesNotExistException>(findProduct);
    }

    [Fact]
    public async Task FindingMultipleDocuments()
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
        var query = _sut.GetRequiredService<IReadQuery<GetProducts, GetProducts.Result>>();
        var result = await query.Read(new(4.5f), CancellationToken);

        // Assert
        Assert.Equal(2, result.Products.Count());
        Assert.Contains(result.Products, product => product.Id == productIds[0]);
        Assert.Contains(result.Products, product => product.Id == productIds[1]);
    }

    [Theory]
    [InlineData(0, 1, 1)]
    [InlineData(1, 1, 1)]
    [InlineData(1, 2, 1)]
    [InlineData(10, 2, 3)]
    [InlineData(10, 4, 3)]
    public async Task FindingMultipleDocumentsWithPagination(int numberOfDocuments, int pageNumber, int pageSize)
    {
        // Arrange
        for (int i = 0; i < numberOfDocuments; i++)
        {
            await Insert(NextId, new($"Product {i}", i), new(0f));
        }

        // Act
        var query = _sut.GetRequiredService<IReadQuery<GetProductsPage, GetProductsPage.Result>>();
        var result = await query.Read(new(pageNumber, pageSize), CancellationToken);

        // Assert
        int numberOfPages = (int)Math.Ceiling((double)numberOfDocuments / pageSize);
        int pageRemainder = numberOfPages % pageSize;

        var expectedPageSize = pageNumber switch
        {
            _ when pageNumber > numberOfPages => 0,
            _ when pageNumber == numberOfPages && pageRemainder == 0 => pageSize,
            _ when pageNumber == numberOfPages && pageRemainder != 0 => pageRemainder,
            _ => pageSize
        };

        Assert.Equal(pageNumber, result.PageNumber);
        Assert.Equal(numberOfPages, result.NumberOfPages);
        Assert.Equal(expectedPageSize, result.Products.Count());
    }

    [Theory]
    [InlineData(0, 1)]
    [InlineData(1, 0)]
    public async Task RejectingInvalidPageRetrievals(int pageNumber, int pageSize)
    {
        // Act
        var query = _sut.GetRequiredService<IReadQuery<GetProductsPage, GetProductsPage.Result>>();
        var findProducts = () => query.Read(new(pageNumber, pageSize), CancellationToken);

        // Assert
        await Assert.ThrowsAsync<ArgumentException>(findProducts);
    }

    protected override void RegisterServices(IServiceCollection services)
    {
        services.AddTransient<IReadQuery<GetProduct, GetProduct.Result>, FindProductQuery>();
        services.AddTransient<IReadQuery<GetProducts, GetProducts.Result>, FindProductsQuery>();
        services.AddTransient<IReadQuery<GetProductsPage, GetProductsPage.Result>, FindProductsQuery>();
        services.AddTransient<IWriteQuery<DeleteProduct>, DeleteProductQuery>();
    }
}
