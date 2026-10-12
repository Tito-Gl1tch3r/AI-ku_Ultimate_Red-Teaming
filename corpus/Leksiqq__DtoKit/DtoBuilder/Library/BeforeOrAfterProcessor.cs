namespace Net.Leksi.Dto;
/// <summary>
/// <para xml:lang="ru">
/// Делегат, определяющий сигнатуру методов, которые вызываются перед и после каждого запроса при использовании 
/// <see cref="DtoBuilder"/> с классом-хэлпером. 
/// <see cref="BeforeAttribute"/>, <see cref="AfterAttribute"/>
/// </para>
/// <para xml:lang="en">
/// Delegate that defines the signature of methods that are called before and after each request when used
/// <see cref="DtoBuilder"/> with helper class.
/// <see cref="BeforeAttribute"/>, <see cref="AfterAttribute"/>
/// </para>
/// </summary>
/// <param name="path">
/// <para xml:lang="ru">
/// Абсолютный путь от корня дерева объекта
/// </para>
/// <para xml:lang="en">
/// Absolute path from the root of the object tree
/// </para>
/// </param>
/// <param name="type">
/// <para xml:lang="ru">
/// Номинальный тип свойства
/// </para>
/// <para xml:lang="en">
/// Nominal property type
/// </para>
/// </param>
/// <param name="value">
/// <para xml:lang="ru">
/// Текущее значение свойства
/// </para>
/// <para xml:lang="en">
/// The current value of the property
/// </para>
/// </param>
/// <param name="isLeaf">
/// <para xml:lang="ru">
/// Указывает, является ли текущий узел листом
/// </para>
/// <para xml:lang="en">
/// Indicates if the current node is a leaf
/// </para>
/// </param>
/// <param name="isNullable">
/// <para xml:lang="ru">
/// Указывает, может ли быть присвоено значение <code>null</code>
/// </para>
/// <para xml:lang="en">
/// Indicates whether <code>null</code> can be assigned
/// </para>
/// </param>
public delegate void BeforeOrAfterProcessor(string path, Type type, object? value, bool isLeaf, bool isNullable);
