using Microsoft.Extensions.DependencyInjection;
using System.Collections;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Net.Leksi.Dto;

/// <summary>
/// <para xml:lang="ru">
/// Фабрика по производству <see cref="JsonConverter"/> для специальной обработки 
/// зарегистрированных интерфейсов и <see cref="IList"/>'ов таких элементов. 
/// Под специальной обработкой понимается:
/// 1) повторное использование объектов и списков объектов
/// в противоположность их созданию при каждой десериализации.
/// 2) повторное использование списка верхнего уровня с указанием, добавить в него новые элементы или
/// перезаписать.
/// </para>
/// <para xml:lang="en">
/// Manufacturing factory <see cref="JsonConverter"/> for special processing
/// registered interfaces and <see cref="IList"/>'s of such elements.
/// Special processing means:
/// 1) reuse of objects and lists of objects
/// as opposed to creating them on every deserialization.
/// 2) reuse the top-level list, specifying whether to add new elements to it or
/// overwrite.
/// </para>
/// </summary>
public class DtoJsonConverterFactory : JsonConverterFactory
{

    private readonly EventArgs _eventArgs = new();

    private object? _target = null;
    private bool _used = false;
    private bool _useEndOfDataNull = true;
    private bool _withMagic = false;
    private KeysProcessing _keysProcessing = KeysProcessing.OnlyKeysForRepeats;

    internal ObjectCache ObjectCache { get; init; }

    internal TypesForest TypesForest { get; init; }

    internal Dictionary<Type, List<object>> ObjectsPool { get; init; } = new();

    /// <summary>
    /// <para xml:lang="ru">
    /// "Крепление" для объекта, запланированного для повторного использования
    /// </para>
    /// <para xml:lang="en">
    /// "Mount" for an object scheduled for reuse
    /// </para>
    /// </summary>
    public object? Target
    {
        get
        {
            return _target;
        }
        set
        {
            if (
                value is null
                || TypesForest.ServiceProvider.Select(sd => sd.ServiceType).Any(t => t.IsAssignableFrom(value!.GetType()))
                || value is IList
                    && value.GetType().IsGenericType
                    && TypesForest.ServiceProvider.Select(sd => sd.ServiceType).Any(t => t.IsAssignableFrom(value.GetType().GenericTypeArguments[0]))
            )
            {
                _target = value;
            }
            else
            {
                throw new ArgumentException(value!.ToString());
            }
        }
    }

    /// <summary>
    /// <para xml:lang="ru">
    /// Значение свойства <c>true</c> указывает, что элемент null в списке верхнего уровня означает
    /// окончание передачи серии данных (смотрите также Net.Leksi.PartialLoader.PartialLoader&lt;&gt;)
    /// </para>
    /// <para xml:lang="en">
    /// The <c>true</c> property value indicates that the null element in the top-level list means
    /// end of data series transfer (see also Net.Leksi.PartialLoader.PartialLoader&lt;&gt;)
    /// </para>
    /// </summary>
    public bool UseEndOfDataNull
    {
        get => _useEndOfDataNull;
        set
        {
            CheckUsed();
            _useEndOfDataNull = value;
        }
    }

    /// <summary>
    /// <para xml:lang="ru">
    /// Значение свойства <c>true</c> указывает, что при <see cref="UseEndOfDataNull"/><c> == true</c> встретился элемент null в списке верхнего уровня
    /// </para>
    /// <para xml:lang="en">
    /// The <c>true</c> property value indicates that when <see cref="UseEndOfDataNull"/><c> == true</c>, a null element was encountered in the top-level list
    /// </para>
    /// </summary>
    public bool IsEndOfData { get; internal set; }

    /// <summary>
    /// <para xml:lang="ru">
    /// Значение свойства <c>true</c> указывает, что в результирующей JSON-строке для зарегистрированных интерфейсов будет добавлено специальное поле,
    /// сигнализирующее, что она была построена с помощью <see cref="DtoConverter{T}"/>
    /// </para>
    /// <para xml:lang="en">
    /// The <c>true</c> property value indicates that a special field will be added to the resulting JSON string for registered interfaces,
    /// signaling that it was built with <see cref="DtoConverter{T}"/>
    /// </para>
    /// </summary>
    public bool WithMagic
    {
        get => _withMagic;
        set
        {
            CheckUsed();
            _withMagic = value;
        }
    }

    /// <summary>
    /// <para xml:lang="ru">
    /// СВойство, указывающее, как будут обрабатываться свойства сериализуемых объектов:
    /// <see cref="KeysProcessing.OnlyKeysForRepeats"/>: все записываемые свойства попадут в результирующий JSON, если ссылка на объект 
    /// встретилась впервые и только ключевые свойства в остальных случаях (установлено по умолчанию);
    /// <see cref="KeysProcessing.Usual"/>: все записываемые свойства попадут в результирующий JSON;
    /// <see cref="KeysProcessing.OnlyKeys"/>: только ключевые свойства попадут в результирующий JSON. (Полезно для запросов с клиента, который работает
    /// с интерфейсами и знать не хочет ни о каких ключах).
    /// В случае, когда передаются только ключевые свойства, в JSON также добавляется служебное специальное поле <code>"$keyOnly": true</code>
    /// </para>
    /// <para xml:lang="en">
    /// A property indicating how the properties of serialized objects will be processed:
    /// <see cref="KeysProcessing.OnlyKeysForRepeats"/>: all writeable properties will be in the resulting JSON if the object reference
    /// met for the first time and only key properties in other cases (set by default);
    /// <see cref="KeysProcessing.Usual"/>: all writeable properties will be included in the resulting JSON;
    /// <see cref="KeysProcessing.OnlyKeys"/>: Only key properties will be included in the resulting JSON. (Useful for requests from a client that is running
    /// with interfaces and doesn't want to know about any keys).
    /// In the case when only key properties are passed, a service special field <code>"$keyOnly": true</code> is also added to JSON
    /// </para>
    /// </summary>
    public KeysProcessing KeysProcessing
    {
        get => _keysProcessing;
        set
        {
            CheckUsed();
            _keysProcessing = value;
        }
    }

    /// <summary>
    /// <para xml:lang="ru">
    /// Инициализируется лесом зарегистрированных типов <see cref="TypesForest"/>
    /// </para>
    /// <para xml:lang="en">
    /// Initialized with a forest of registered types <see cref="TypesForest"/>
    /// </para>
    /// </summary>
    /// <param name="typesForest"></param>
    /// <exception cref="ArgumentNullException">
    /// <para xml:lang="ru">
    /// Без леса зарегистрированных типов <see cref="TypesForest"/> ничего не будет работать
    /// </para>
    /// <para xml:lang="en">
    /// Without a forest of registered types <see cref="TypesForest"/> nothing will work
    /// </para>
    /// </exception>
    public DtoJsonConverterFactory(TypesForest typesForest)
    {
        TypesForest = typesForest ?? throw new ArgumentNullException(nameof(typesForest)) ;
        ObjectCache = TypesForest.ServiceProvider.GetService<ObjectCache>() ?? new ObjectCache(TypesForest);
    }

    /// <summary>
    /// <para xml:lang="ru">
    /// При повторном использовании <see cref="DtoJsonConverterFactory"/> с установленным в <see cref="KeysProcessing.OnlyKeys"/> 
    /// свойством <see cref="KeysProcessing"/>
    /// следует очистить кеш, созданный для учёта повторяющихся объектов. (Скорее всего, не понадобится при использовании в ASP.NET, так как обычно сервис 
    /// будет регистрироваться как <code>Transient</code>
    /// </para>
    /// <para xml:lang="en">
    /// When reusing <see cref="DtoJsonConverterFactory"/> with property set to <see cref="KeysProcessing.OnlyKeys"/>
    /// <see cref="KeysProcessing"/>
    /// should clear the cache created to account for duplicate objects. (Probably not needed when used in ASP.NET, as a service usually
    /// will be registered as <code>Transient</code>
    /// </para>
    /// </summary>
    public void ClearCache()
    {
        ObjectCache.Clear();
    }


    #region Реализация JsonConverterFactory

    /// <inheritdoc/>
    public override bool CanConvert(Type typeToConvert)
    {
        _used = true;
        if (TypesForest.ServiceProvider.Select(sd => sd.ServiceType).Any(t => typeof(ListStub<>).MakeGenericType(new Type[] { t }).IsAssignableFrom(typeToConvert)))
        {
            return true;
        }
        bool result = TypesForest.ServiceProvider.IsRegistered(typeToConvert);
        if (result)
        {
            TypesForest.GetTypeNode(typeToConvert);
        }
        else
        {
            result = IsSupportedType(typeToConvert);
        }
        return result;
    }

    /// <inheritdoc/>
    public override JsonConverter? CreateConverter(Type typeToConvert, JsonSerializerOptions options)
    {
        JsonConverter converter;
        Type? type = TypesForest.ServiceProvider.Select(sd => sd.ServiceType).Where(
                t => typeof(ListStub<>).MakeGenericType(new Type[] { t }).IsAssignableFrom(typeToConvert)
            ).FirstOrDefault((Type?)null);
        if (type is { })
        {
            ListStubKind kind = typeToConvert.IsAssignableFrom(typeof(AppendableListStub<>).MakeGenericType(new Type[] { type })) 
                ? ListStubKind.Appendable
                : (
                    typeToConvert.IsAssignableFrom(typeof(RewritableListStub<>).MakeGenericType(new Type[] { type })) 
                    ? ListStubKind.Rewriteable
                        : ListStubKind.Updateable
                )
            ;
            converter = (JsonConverter)Activator.CreateInstance(
                    typeof(ListDeserializer<>).MakeGenericType(new Type[] { type }),
                    args: new object[] { this, kind }
                )!;
        }
        else if (IsSupportedType(typeToConvert))
        {
            converter = (JsonConverter)Activator.CreateInstance(
                    typeof(SupportedTypeConverter<>).MakeGenericType(new Type[] { typeToConvert }),
                    args: new object[] { this }
                )!;
        }
        else
        {
            converter = (JsonConverter)Activator.CreateInstance(
                    typeof(DtoConverter<>).MakeGenericType(new Type[] { typeToConvert }), 
                    args: new object[] { this }
                )!;
        }

        return converter;
    }
    #endregion

    private void CheckUsed()
    {
        if (_used)
        {
            throw new InvalidOperationException("Cannot configure after using.");
        }
    }

    private bool IsSupportedType(Type typeToConvert)
    {
        return typeToConvert.IsEnum;
    }

}

