namespace Net.Leksi.Dto;

/// <summary>
/// <para xml:lang="ru">
/// При использовании <see cref="DtoBuilder"/> с классом-хэлпером связывает абсолютный 
/// путь от корня дерева объекта с соответствующим сеттером.
/// </para>
/// <para xml:lang="en">
/// When using <see cref="DtoBuilder"/> with a helper class, binds an absolute
/// path from the root of the object tree with the corresponding setter.
/// </para>
/// </summary>
[AttributeUsage(AttributeTargets.Method, AllowMultiple = true)]
public class PathAttribute: Attribute
{
    /// <summary>
    /// <para xml:lang="ru">
    /// Абсолютный путь от корня дерева объекта.
    /// </para>
    /// <para xml:lang="en">
    /// Absolute path from the root of the object tree.
    /// </para>
    /// </summary>
    public string Path { get; init; }
    /// <summary>
    /// <para xml:lang="ru">
    /// Инициализирует абсолютным путём от корня дерева объекта
    /// </para>
    /// <para xml:lang="en">
    /// Initializes with an absolute path from the root of the object tree
    /// </para>
    /// </summary>
    /// <param name="path"></param>
    public PathAttribute(string path)
    {
        Path = path;
    }
}
