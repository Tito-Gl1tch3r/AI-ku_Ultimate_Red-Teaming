using System.Reflection;
using TJC.Persist.Helpers;
using TJC.Persist.Tests.Mocks;

namespace TJC.Persist.Tests;

public class PersistManagerValidationTests : TestBase
{
    [Fact]
    public void RegistrationHelpers_RegisterAndRetrievePersistType()
    {
        PersistManager.RegisterAllFromAssembly(Assembly.GetExecutingAssembly());

        Assert.Equal(
            typeof(ExamplePersistObject),
            PersistTypeRegistry.GetTypeByName("ExamplePersistObject")
        );
        Assert.Equal(
            "ExamplePersistObject",
            PersistTypeRegistry.GetName(typeof(ExamplePersistObject))
        );
    }

    [Fact]
    public void RegisterType_InvalidType_ThrowsInvalidOperationException()
    {
        Assert.Throws<InvalidOperationException>(() => PersistManager.RegisterType(typeof(string)));
    }

    [Fact]
    public void Registry_UnknownEntries_ThrowInvalidOperationException()
    {
        Assert.Throws<InvalidOperationException>(() =>
            PersistTypeRegistry.GetTypeByName("MissingPersistType")
        );
        Assert.Throws<InvalidOperationException>(() =>
            PersistTypeRegistry.GetName(typeof(PersistManagerValidationTests))
        );
    }

    [Fact]
    public void Deserialize_InvalidWrapper_ThrowsInvalidOperationException()
    {
        Assert.Throws<InvalidOperationException>(() =>
            PersistManager.Deserialize("{\"Type\":\"\",\"Payload\":{}}")
        );
        Assert.Throws<InvalidOperationException>(() =>
            PersistManager.Deserialize("{\"Type\":\"Unknown\",\"Payload\":{}}")
        );
    }
}
