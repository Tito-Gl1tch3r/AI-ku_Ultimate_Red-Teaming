namespace Net.Leksi.Dto;

/// <summary>
/// <para xml:lang="ru">
/// Класс объектов для хранения и доступа к уже созданным при загрузке или десериализации объектам
/// для предотвращения их дублирования
/// </para>
/// <para xml:lang="en">
/// An object class for storing and accessing objects already created during loading or deserialization
/// to prevent duplication
/// </para>
/// </summary>
public class ObjectCache
{

    private static readonly KeyEqualityComparer _keyComparer = new();
    private readonly TypesForest _typesForest;

    private Dictionary<Type, Dictionary<object[], object>> _objectsCache = new();

    /// <summary>
    /// <para xml:lang="ru">
    /// Количество объектов в кеше
    /// </para>
    /// <para xml:lang="en">
    /// Number of objects in the cache
    /// </para>
    /// </summary>
    public int Count => _objectsCache.Count;

    /// <summary>
    /// <para xml:lang="ru">
    /// Конструктор
    /// </para>
    /// <para xml:lang="en">
    /// Constructor
    /// </para>
    /// </summary>
    /// <param name="typesForest"></param>
    public ObjectCache(TypesForest typesForest) 
    {
        _typesForest = typesForest;
    }


    /// <summary>
    /// <para xml:lang="ru">
    /// Пытается извлечь из кеша ссылку на объект указанного типа и с указанным набором ключевых свойств
    /// </para>
    /// <para xml:lang="en">
    /// Attempts to retrieve from the cache a reference to an object of the specified type and with the specified set of key properties
    /// </para>
    /// </summary>
    /// <param name="type">
    /// <para xml:lang="ru">
    /// Интерфейсный тип, под которым искомый объект помёщён в кеш
    /// </para>
    /// <para xml:lang="en">
    /// Interface type under which the searched object is placed in the cache
    /// </para>
    /// </param>
    /// <param name="key">
    /// <para xml:lang="ru">
    /// Набор значений ключевых свойств искомого объекта
    /// </para>
    /// <para xml:lang="en">
    /// Set of values of the key properties of the searched object
    /// </para>
    /// </param>
    /// <param name="result">
    /// <para xml:lang="ru">
    /// Найденный объект в случае успеха
    /// </para>
    /// <para xml:lang="en">
    /// Found object if successful
    /// </para>
    /// </param>
    /// <returns>
    /// <para xml:lang="ru">
    /// Успешно или нет
    /// </para>
    /// <para xml:lang="en">
    /// Successful or not
    /// </para>
    /// </returns>
    public bool TryGet(Type type, object[] key, out object? result)
    {
        if (_objectsCache.ContainsKey(type))
        {
            return _objectsCache[type].TryGetValue(key, out result);
        }
        result = default;
        return false;
    }

    /// <summary>
    /// <para xml:lang="ru">
    /// Добавляет в кеш или заменяет существующий объект указанного типа и с указанным набором ключевых свойств
    /// </para>
    /// <para xml:lang="en">
    /// Adds to the cache or replaces an existing object of the specified type and with the specified set of key properties
    /// </para>
    /// </summary>
    /// <param name="type">
    /// <para xml:lang="ru">
    /// Интерфейсный тип, под которым объект помещается в кеш
    /// </para>
    /// <para xml:lang="en">
    /// Interface type under which the object is placed in the cache
    /// </para>
    /// </param>
    /// <param name="key">
    /// <para xml:lang="ru">
    /// Набор значений ключевых свойств помещаемого в кеш объекта
    /// </para>
    /// <para xml:lang="en">
    /// A set of values for the key properties of the object placed in the cache
    /// </para>
    /// </param>
    /// <param name="value">
    /// <para xml:lang="ru">
    /// Помещаемый в кеш объект
    /// </para>
    /// <para xml:lang="en">
    /// The object to be cached
    /// </para>
    /// </param>
    public void Add(Type type, object[] key, object value)
    {
        if (!_objectsCache.ContainsKey(type))
        {
            _objectsCache.Add(type, new Dictionary<object[], object>(_keyComparer));
            if (!_objectsCache.ContainsKey(value.GetType()))
            {
                _objectsCache[value.GetType()] = new Dictionary<object[], object>(_keyComparer);
            }
        }
        if (!_objectsCache[type].ContainsKey(key))
        {
            if (_objectsCache[value.GetType()].ContainsKey(key))
            {
                _typesForest.Copy(type, value, _objectsCache[value.GetType()][key]);
                _objectsCache[type][key] = _objectsCache[value.GetType()][key];
            }
            else
            {
                _objectsCache[value.GetType()][key] = value;
                _objectsCache[type][key] = value;
            }
        }

    }

    /// <summary>
    /// <para xml:lang="ru">
    /// Очищает кеш
    /// </para>
    /// <para xml:lang="en">
    /// Clear cache
    /// </para>
    /// </summary>
    public void Clear()
    {
        _objectsCache.Clear();
    }

}
