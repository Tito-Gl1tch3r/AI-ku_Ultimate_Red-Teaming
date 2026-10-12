using Microsoft.Extensions.DependencyInjection;
using MongoDDD.Core.Exceptions;
using MongoDDD.Core.Queries;
using MongoDDD.Tests.SUT.Contract.Create;
using MongoDDD.Tests.SUT.Persistence.Data;
using MongoDDD.Tests.SUT.Persistence.Queries;

namespace MongoDDD.Tests.QueriesTests;

public class InsertTests(TestsFixture fixture) : TestsBase(fixture)
{
    [Fact]
    public async Task InsertingDocuments()
    {
        // Arrange
        var productId = NextId;
        var productName = "White bread";
        var productPrice = 2.99M;

        // Act
        var query = _sut.GetRequiredService<IWriteQuery<CreateProduct>>();
        await query.Write(new(productId, productName, productPrice), CancellationToken);

        // Assert
        await Exists(productId, new(productName, productPrice), new ExternalData(0f));
    }

    [Fact]
    public async Task RejectingDuplicateDocuments()
    {
        // Arrange
        var productId = NextId;
        await Insert(productId, new("White bread", 2.99M));

        // Act
        var query = _sut.GetRequiredService<IWriteQuery<CreateProduct>>();
        var insertDuplicate = () => query.Write(new(productId, "Rye bread", 3.99M), CancellationToken);

        // Assert
        await Assert.ThrowsAsync<AlreadyExistsException>(insertDuplicate);
    }

    protected override void RegisterServices(IServiceCollection services)
    {
        services.AddTransient<IWriteQuery<CreateProduct>, InsertProductQuery>();
    }
}
