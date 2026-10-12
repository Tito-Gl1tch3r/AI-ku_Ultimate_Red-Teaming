using System.Reflection;

namespace Net.Leksi.Dto;

/// <summary>
/// <para xml:lang="ru">
/// Класс для сортировки <see cref="PropertyNode"/>
/// Первыми ставятся ключевые свойства, затем листовые, затем узловые
/// Внутри каждого из указанных множеств сортируются по именам в алфавитном порядке
/// </para>
/// <para xml:lang="en">
/// Class for sorting <see cref="PropertyNode"/>
/// Key properties are put first, then leaf properties, then node properties
/// Within each of the specified sets are sorted by name in alphabetical order
/// </para>
/// </summary>
public class PropertyNodeComparer : IComparer<PropertyNode>
{
    /// <inheritdoc/>
    public int Compare(PropertyNode? x, PropertyNode? y)
    {
        if (x == y)
        {
            return 0;
        }
        if (x is null)
        {
            return -1;
        }
        if (y is null)
        {
            return 1;
        }
        KeyAttribute? xKeyAttribute = x.PropertyInfo?.GetCustomAttribute<KeyAttribute>();
        KeyAttribute? yKeyAttribute = y.PropertyInfo?.GetCustomAttribute<KeyAttribute>();
        if (xKeyAttribute is KeyAttribute && yKeyAttribute is null)
        {
            return -1;
        }
        if (xKeyAttribute is null && yKeyAttribute is KeyAttribute)
        {
            return 1;
        }
        if (x.TypeNode.ChildNodes is null && y.TypeNode.ChildNodes is { })
        {
            return -1;
        }
        if (x.TypeNode.ChildNodes is { } && y.TypeNode.ChildNodes is null)
        {
            return 1;
        }
        return string.Compare(x.Name, y.Name);
    }
}
