namespace Net.Leksi.Dto;

/// <summary>
/// <para xml:lang="ru">
/// Атрибут, указывающий на фактическое свойство класса, если его имя отличается от имени свойства реализованного интерфейса
/// </para>
/// <para xml:lang="en">
/// Attribute pointing to the actual property of the class, if its name differs from the property name of the implemented interface
/// </para>
/// </summary>
[AttributeUsage(AttributeTargets.Property)]
public class ActualPropertyAttribute : Attribute
{
    /// <summary>
    /// <para xml:lang="ru">
    /// Имя фактического свойства
    /// </para>
    /// <para xml:lang="en">
    /// Actual property name
    /// </para>
    /// </summary>
    public string PropertyName { get; init; }

    /// <summary>
    /// <para xml:lang="ru">
    /// Инициализирует именем фактического свойства
    /// </para>
    /// <para xml:lang="en">
    /// Initializes with actual property name
    /// </para>
    /// </summary>
    /// <param name="propertyName"></param>
    public ActualPropertyAttribute(string propertyName)
    {
        PropertyName = propertyName;
    }

}
