namespace Net.Leksi.Dto;
/// <summary>
/// <para xml:lang="ru">
/// Запрос на получение значения одного свойства при загрузке объекта
/// </para>
/// <para xml:lang="en">
/// Request to get the value of one property when loading an object
/// </para>
/// </summary>
public class ValueRequest
{
    /// <summary>
    /// <para xml:lang="ru">
    /// На сколько узлов к корню нужно вернуться после выполнения текущего запроса
    /// Столько же объектов нужно извлечь из стека
    /// </para>
    /// <para xml:lang="en">
    /// How many nodes to return to the root after executing the current request
    /// How many objects to pop off the stack
    /// </para>
    /// </summary>
    public int PopsCount { get; internal set; } = 0;

    /// <summary>
    /// <para xml:lang="ru">
    /// Информация для запроса
    /// </para>
    /// <para xml:lang="en">
    /// Request information
    /// </para>
    /// </summary>
    public PropertyNode PropertyNode { get; internal set; } = null!;

    /// <summary>
    /// <para xml:lang="ru">
    /// Абсолютный путь от корневого узла дерева объекта в стандартной нотации 
    /// </para>
    /// <para xml:lang="en">
    /// Absolute path from the root node of object&apos;s tree in standard notation
    /// </para>
    /// </summary>
    public string Path { get; internal set; } = string.Empty;

#if DEBUG
    public override string ToString()
    {
        return $"{Path}, {(PropertyNode.IsLeaf ? string.Empty : "+" + PropertyNode.TypeNode.Type)}, {PopsCount}";
    }
#endif
}
