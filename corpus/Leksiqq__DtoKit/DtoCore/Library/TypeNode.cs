namespace Net.Leksi.Dto;

/// <summary>
/// <para xml:lang="ru">
/// Узел дерева "свойств и типов" для кеширования рефлексии и программирования построения объектов
/// </para>
/// <para xml:lang="en">
/// "properties and types" tree node for reflection caching and object building programming
/// </para>
/// </summary>
public class TypeNode
{
    /// <summary>
    /// <para xml:lang="ru">
    /// Тип свойства, определённый в интерфейсе
    /// </para>
    /// <para xml:lang="en">
    /// Property type defined in the interface
    /// </para>
    /// </summary>
    public Type Type { get; internal set; } = null!;
    /// <summary>
    /// <para xml:lang="ru">
    /// Тип свойства, определённый в классе
    /// </para>
    /// <para xml:lang="en">
    /// Property type defined in the class
    /// </para>
    /// </summary>
    public Type ActualType { get; internal set; } = null!;
    /// <summary>
    /// <para xml:lang="ru">
    /// Список дочерних узлов, соответствующих свойствам, определённым в интерфейсе
    /// </para>
    /// <para xml:lang="en">
    /// List of child nodes corresponding to the properties defined in the interface
    /// </para>
    /// </summary>
    public List<PropertyNode>? ChildNodes { get; internal set; }
    /// <summary>
    /// <para xml:lang="ru">
    /// Количество ключевых свойств, определённых в классе
    /// </para>
    /// <para xml:lang="en">
    /// Number of key properties defined in the class
    /// </para>
    /// </summary>
    public int KeysCount { get; internal set; } = 0;
    /// <summary>
    /// <para xml:lang="ru">
    /// "Программа" построения объекта
    /// </para>
    /// <para xml:lang="en">
    /// "Program" for building an object
    /// </para> 
    /// </summary>
    public List<ValueRequest>? ValueRequests { get; internal set; } = null;
    /// <summary>
    /// <para xml:lang="ru">
    /// Метод для извлечения ключей из объекта, соответствующего данному узлу
    /// </para>
    /// <para xml:lang="en">
    /// Method for extracting keys from the object corresponding to the given node
    /// </para>
    /// </summary>
    /// <param name="item">
    /// <para xml:lang="ru">
    /// Объект, из которого нужно извлечь ключи
    /// </para>
    /// <para xml:lang="en">
    /// Object to extract keys from
    /// </para>
    /// </param>
    /// <returns>
    /// <para xml:lang="ru">
    /// Массив с ключами
    /// </para>
    /// <para xml:lang="en">
    /// Array with keys
    /// </para>
    /// </returns>
    public object[]? GetKey(object item)
    {
        return ChildNodes?.Take(KeysCount).SelectMany(v => 
        {
            object value = v.PropertyInfo!.GetValue(item)!;
            if (v.IsKey)
            {
                return v.TypeNode.ChildNodes!.Select(cn => cn.PropertyInfo!.GetValue(value)!);
            }
            return new[] { value };
        }).ToArray();
    }

}
