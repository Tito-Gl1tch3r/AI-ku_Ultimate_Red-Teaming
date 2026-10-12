using System.Collections;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Net.Leksi.Dto;

/// <summary>
/// <para xml:lang="ru">
/// Конвертер для десериализации списка верхнего уровня, то есть корневого элемента JSON.
/// Требуется кастомный, так как мы хотим использовать существующий список (например, <see cref="System.Collections.ObjectModel.ObservableCollection{T}"/> на клиенте, а не 
/// создавать каждый раз новый или не создавать новый промежуточный для заполнения. Также настраивается способ заполнения: перезапись
/// или добавление.
/// Данный конвертер не предназначен для сериализации
/// </para>
/// <para xml:lang="en">
/// Converter to deserialize the top-level list, i.e. the root JSON element.
/// Requires custom since we want to use an existing list (e.g. <see cref="System.Collections.ObjectModel.ObservableCollection{T}"/> on the client, not
/// create a new one every time or don't create a new intermediate one to fill. The filling method is also configured: overwriting
/// or adding.
/// This converter is not intended for serialization
/// </para>
/// </summary>
/// <typeparam name="T"></typeparam>
internal class ListDeserializer<T> : JsonConverter<ListStub<T>> where T : class
{
    private readonly DtoJsonConverterFactory _factory;
    private readonly ListStubKind _kind;
    private KeyEqualityComparer? _keyComparer = null;
    private Dictionary<int, object[]>? _keysMap = null;
    private TypeNode? _typeNode = null;
    private ObjectCache? _objectCache = null;


    public ListDeserializer(DtoJsonConverterFactory factory, ListStubKind kind)
    {
        _factory = factory;
        _kind = kind;
    }

    /// <inheritdoc cref="JsonConverter{T}.Read(ref Utf8JsonReader, Type, JsonSerializerOptions)"/>
    /// <returns>
    /// <para xml:lang="ru">
    /// Возвращает заглушку, заполненный лист передаётся через <see cref="DtoJsonConverterFactory.Target"/>
    /// </para>
    /// <para xml:lang="en">
    /// Returns a stub, the filled sheet is passed via <see cref="DtoJsonConverterFactory.Target"/>
    /// </para>
    /// </returns>
    /// <exception cref="JsonException">
    /// <para xml:lang="ru">
    /// 1) Если элемент JSON не является массивом
    /// 2) Если <see cref="DtoJsonConverterFactory.UseEndOfDataNull"/><c> == true</c>, при этом встретился 
    /// элемент после <c>null</c>
    /// </para>
    /// <para xml:lang="en">
    /// 1) If the JSON element is not an array
    /// 2) If <see cref="DtoJsonConverterFactory.UseEndOfDataNull"/><c> == true</c>, and there is an element after <c>null</c>
    /// </para>    
    /// </exception>
    public override ListStub<T>? Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        IList? result = null;
        T updateableProbe = null!;
        if(_kind is ListStubKind.Updateable)
        {
            _keyComparer = new KeyEqualityComparer();
            _keysMap = new Dictionary<int, object[]>();
            _typeNode = _factory.TypesForest.GetTypeNode(typeof(T));
            _objectCache = new ObjectCache(_factory.TypesForest);
        }
        if (_factory.Target is null || !typeof(IList).IsAssignableFrom(_factory.Target.GetType()) || reader.TokenType != JsonTokenType.StartArray)
        {
            throw new JsonException();
        }
        _factory.IsEndOfData = false;
        result = (IList)_factory.Target;
        _factory.Target = null;
        int i = _kind is ListStubKind.Appendable ? result.Count : 0;
        for (; reader.Read() && reader.TokenType != JsonTokenType.EndArray; i++)
        {
            if (_factory.IsEndOfData)
            {
                throw new JsonException();
            }
            bool hasElement = i < result.Count;
            if (_factory.TypesForest.ServiceProvider.Select(sd => sd.ServiceType).Any(type => type.IsAssignableFrom(typeof(T))))
            {
                if(_kind is not ListStubKind.Updateable)
                {
                    if (hasElement)
                    {
                        _factory.Target = result[i];
                    }
                    else if (_factory.ObjectsPool.TryGetValue(typeof(T), out List<object>? pool) && pool.Count > 0)
                    {
                        _factory.Target = pool[0];
                        pool.RemoveAt(0);
                    }
                }
                else
                {
                    if(updateableProbe is { })
                    {
                        _factory.Target = updateableProbe;
                    }
                }
            }
            T? value = JsonSerializer.Deserialize<T>(ref reader, options);
            if (value is null && _factory.UseEndOfDataNull)
            {
                _factory.IsEndOfData = true;
            }
            else
            {
                if(_kind is ListStubKind.Updateable)
                {
                    updateableProbe = value!;
                    UpdateElement(result, updateableProbe);
                }
                else
                {
                    if (!hasElement || !object.ReferenceEquals(value, result[i]))
                    {
                        if (i < result.Count)
                        {
                            result[i] = value;
                        }
                        else
                        {
                            result.Add(value);
                        }
                    }
                }
            }
        }
        if(_kind is not ListStubKind.Updateable)
        {
            if (i < result.Count && !_factory.ObjectsPool.ContainsKey(typeof(T)))
            {
                _factory.ObjectsPool[typeof(T)] = new List<object>();
            }
            while (i < result.Count)
            {
                if(result[i] is { })
                {
                    _factory.ObjectsPool[typeof(T)].Add(result[i]!);
                }
                result.RemoveAt(i);
            }
        }
        return _kind switch { 
            ListStubKind.Appendable => AppendableListStub<T>.Instance, 
            ListStubKind.Rewriteable => RewritableListStub<T>.Instance, 
            _ => UpdateableListStub<T>.Instance };
    }

    /// <summary>
    /// <para xml:lang="ru">
    /// Данный конвертер не предназначен для сериализации
    /// </para>
    /// <para xml:lang="en">
    /// This converter is not intended for serialization
    /// </para>
    /// </summary>
    /// <exception cref="NotImplementedException"></exception>
    public override void Write(Utf8JsonWriter writer, ListStub<T> value, JsonSerializerOptions options)
    {
        throw new NotImplementedException();
    }

    private void UpdateElement(IList result, T updateableProbe)
    {
        object[] key = _typeNode!.GetKey(updateableProbe)!;
        for (int i = _objectCache!.Count; i < result.Count; i++)
        {
            object[] itemKey = _typeNode!.GetKey(result[i]!)!;
            _objectCache.Add(result[i]!.GetType(), itemKey, result[i]!);
        }
        if (_objectCache.TryGet(updateableProbe.GetType(), key, out object? item))
        {
            _factory.TypesForest.Copy(updateableProbe.GetType(), updateableProbe, item!);
        }
    }

}
