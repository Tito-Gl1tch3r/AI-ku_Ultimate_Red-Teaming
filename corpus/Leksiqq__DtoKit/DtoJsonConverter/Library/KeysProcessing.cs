namespace Net.Leksi.Dto;

/// <summary>
/// <para xml:lang="ru">
/// Виды способа обработки свойств при сериализации и десериализации
/// </para>
/// <para xml:lang="en">
/// Types of how properties are handled during serialization and deserialization
/// </para>
/// </summary>
public enum KeysProcessing
{
    /// <summary>
    /// <para xml:lang="ru">
    /// Все записываемые свойства попадут в результирующий JSON, если ссылка на объект 
    /// встретилась впервые и только ключевые свойства в остальных случаях
    /// </para>
    /// <para xml:lang="en">
    /// All properties that are written will be included in the resulting JSON if the object reference
    /// met for the first time and only key properties in other cases
    /// </para>
    /// </summary>
    OnlyKeysForRepeats,
    /// <summary>
    /// <para xml:lang="ru">
    /// Все записываемые свойства попадут в результирующий JSON
    /// </para>
    /// <para xml:lang="en">
    /// All writable properties will be included in the resulting JSON
    /// </para>
    /// </summary>
    Usual,
    /// <summary>
    /// <para xml:lang="ru">
    /// Только ключевые свойства попадут в результирующий JSON. (Полезно для запросов с клиента, который работает
    /// с интерфейсами и знать не хочет ни о каких ключах)
    /// </para>
    /// <para xml:lang="en">
    /// Only the key properties will be included in the resulting JSON. (Useful for requests from a client that is operating
    /// with interfaces and doesn't want to know about any keys)
    /// </para>    /// </summary>
    OnlyKeys
}
