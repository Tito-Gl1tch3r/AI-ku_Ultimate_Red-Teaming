using System.Reflection;
using System.Text.Json;
using TJC.Persist.Helpers;
using TJC.Singleton;

namespace TJC.Persist;

/// <summary>
/// Manage persist objects
/// </summary>
public class PersistManager : SingletonBase<PersistManager>
{
    private static readonly JsonSerializerOptions SerializerOptions = new()
    {
        WriteIndented = false,
    };

    /// <summary>
    /// Instantiate singleton
    /// </summary>
    protected PersistManager()
    {
        PersistTypeRegistry.RegisterAllFromAssembly(Assembly.GetExecutingAssembly());
    }

    /// <summary>
    /// Register all types from assembly which inherit from <see cref="IPersistObject"/>
    /// </summary>
    /// <param name="assembly"></param>
    public static void RegisterAllFromAssembly(Assembly assembly)
    {
        PersistTypeRegistry.RegisterAllFromAssembly(assembly);
    }

    /// <summary>
    /// Register any type inheriting from <see cref="IPersistObject"/>
    /// </summary>
    /// <param name="type"></param>
    public static void RegisterType(Type type)
    {
        PersistTypeRegistry.Register(type);
    }

    /// <summary>
    /// Deserialize any object inheriting from <see cref="IPersistObject"/> to string
    /// </summary>
    /// <param name="obj"></param>
    /// <returns></returns>
    public static string Serialize(IPersistObject obj)
    {
        var type = obj.GetType();
        var payload = JsonSerializer.SerializeToElement(obj, type, SerializerOptions);

        var wrapper = new PersistWrapper()
        {
            Type = PersistTypeRegistry.GetName(type),
            Payload = payload,
        };
        return JsonSerializer.Serialize(wrapper, SerializerOptions);
    }

    /// <summary>
    /// Deserialize string to any object inheriting from <see cref="IPersistObject"/>
    /// </summary>
    /// <param name="json"></param>
    /// <returns></returns>
    /// <exception cref="InvalidOperationException"></exception>
    public static IPersistObject Deserialize(string json)
    {
        var wrapper = JsonSerializer.Deserialize<PersistWrapper>(json);

        if (wrapper == null || string.IsNullOrWhiteSpace(wrapper.Type))
            throw new InvalidOperationException("Invalid serialization wrapper.");

        var type = PersistTypeRegistry.GetTypeByName(wrapper.Type);
        if (type == null || !typeof(IPersistObject).IsAssignableFrom(type))
            throw new InvalidOperationException($"Invalid or unknown type: {wrapper.Type}");

        var obj = (IPersistObject?)wrapper.Payload.Deserialize(type);
        return obj ?? throw new InvalidOperationException("Failed to deserialize object.");
    }
}
