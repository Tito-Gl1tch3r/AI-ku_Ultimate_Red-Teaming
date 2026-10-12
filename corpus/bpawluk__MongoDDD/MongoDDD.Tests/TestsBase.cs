using Microsoft.Extensions.DependencyInjection;
using MongoDB.Bson;
using MongoDB.Driver;
using MongoDDD.Persistence;
using MongoDDD.Persistence.Data;
using MongoDDD.Tests.SUT.Persistence.Configuration;
using MongoDDD.Tests.SUT.Persistence.Data;

namespace MongoDDD.Tests;

[Collection(nameof(TestsCollection))]
public abstract class TestsBase : IAsyncLifetime
{
    private static readonly TimeSpan _timeout = TimeSpan.FromSeconds(5);

    protected readonly IServiceProvider _sut;

    protected static string NextId => ObjectId.GenerateNewId().ToString();

    protected MongoClient DatabaseClient => _sut.GetRequiredService<MongoClient>();

    protected ProductsDatabaseSettings DatabaseSettings => _sut.GetRequiredService<ProductsDatabaseSettings>();

    protected CancellationToken CancellationToken { get; } = new CancellationTokenSource(_timeout).Token;

    public TestsBase(TestsFixture fixture)
    {
        var databaseSettings = new ProductsDatabaseSettings()
        {
            Connection = fixture.MongoRunner.ConnectionString,
            Database = "productsDatabase",
            Collection = "productsCollection"
        };

        var services = new ServiceCollection();

        services.AddSingleton(databaseSettings);
        services.AddSingleton(databaseSettings.CreateClient());
        RegisterServices(services);

        _sut = services.BuildServiceProvider();
    }

    public virtual Task InitializeAsync() => Task.CompletedTask;

    protected abstract void RegisterServices(IServiceCollection services);

    protected async Task Insert(string id, ProductData productData)
    {
        var document = new DatabaseDocument<ProductData, None>(id, productData, None.Value);
        await GetCollection<DatabaseDocument<ProductData, None>>().InsertOneAsync(document);
    }

    protected async Task Insert(string id, ProductData productData, ExternalData externalData)
    {
        var document = new DatabaseDocument<ProductData, ExternalData>(id, productData, externalData);
        await GetCollection<DatabaseDocument<ProductData, ExternalData>>().InsertOneAsync(document);
    }

    protected async Task Exists(string id, ProductData productData, int version = 1, bool modified = false, bool deleted = false)
    {
        var filter = Builders<DatabaseDocument<ProductData, None>>.Filter.Eq(databaseDocument => databaseDocument.Id, id);
        var actualDocument = await GetCollection<DatabaseDocument<ProductData, None>>().Find(filter).Limit(1).SingleOrDefaultAsync();
        Assert.Equal(productData, actualDocument.Data);
        Assert.Equal(version, actualDocument.Version);
        AssertDocumentState(actualDocument, id, version, modified, deleted);
    }

    protected async Task Exists(string id, ProductData productData, ExternalData externalData, int version = 1, bool modified = false, bool deleted = false)
    {
        var filter = Builders<DatabaseDocument<ProductData, ExternalData>>.Filter.Eq(databaseDocument => databaseDocument.Id, id);
        var actualDocument = await GetCollection<DatabaseDocument<ProductData, ExternalData>>().Find(filter).Limit(1).SingleOrDefaultAsync();
        Assert.Equal(productData, actualDocument.Data);
        Assert.Equal(externalData, actualDocument.ExternalData);
        AssertDocumentState(actualDocument, id, version, modified, deleted);
    }

    private void AssertDocumentState<TData, TExternalData>(DatabaseDocument<TData, TExternalData> actualDocument, string id, int version, bool modified, bool deleted)
    {
        Assert.Equal(id, actualDocument.Id);
        Assert.True(DateTime.UtcNow - actualDocument.Created < _timeout);

        if (modified)
        {
            Assert.NotNull(actualDocument.Modified);
            Assert.True(DateTime.UtcNow - actualDocument.Modified < _timeout);
            Assert.True(actualDocument.Modified >= actualDocument.Created);
        }
        else
        {
            Assert.Null(actualDocument.Modified);
        }

        if (deleted)
        {
            Assert.NotNull(actualDocument.Deleted);
            Assert.True(DateTime.UtcNow - actualDocument.Deleted < _timeout);
            Assert.True(actualDocument.Deleted >= actualDocument.Created);
        }
        else
        {
            Assert.Null(actualDocument.Deleted);
        }
    }

    private IMongoCollection<T> GetCollection<T>() => DatabaseClient.GetDatabase(DatabaseSettings.Database).GetCollection<T>(DatabaseSettings.Collection);

    public Task DisposeAsync() => GetCollection<BsonDocument>().DeleteManyAsync(FilterDefinition<BsonDocument>.Empty);
}
