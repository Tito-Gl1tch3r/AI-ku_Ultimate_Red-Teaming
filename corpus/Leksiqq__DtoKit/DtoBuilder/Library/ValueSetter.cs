namespace Net.Leksi.Dto;

/// <summary>
/// <para xml:lang="ru">
/// Делегат, определяющий сигнатуру метода, который запрашивает значение свойства при использовании <see cref="DtoBuilder"/> с классом-хэлпером. 
/// Должен быть также помечен <see cref="PathAttribute"/>.
/// </para>
/// <para xml:lang="en">
/// A delegate that defines the signature of the method that queries the value of the property when using <see cref="DtoBuilder"/> with a helper class.
/// Should also be marked with <see cref="PathAttribute"/>.
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
/// <param name="isCommited">
/// <para xml:lang="ru">
/// Если установить значение <code>true</code>, то узел считается завершённым и его свойства не будут требовать
/// присвоения значений. То есть узел будет считаться листом. То же самое произойдёт, 
/// если вернуть <code>null</code> в качестве нового
/// значения.
/// </para>
/// <para xml:lang="en">
/// If you set the value to <code>true</code>, then the node is considered complete and its properties will not require
/// value assignments. That is, the node will be considered a leaf. The same will happen if you return <code>null</code> 
/// as new value.
/// </para>
/// </param>
/// <returns>
/// <para xml:lang="ru">
/// Новое или старое значение свойства.
/// </para>
/// <para xml:lang="en">
/// New or old property value.
/// </para>
/// </returns>
public delegate object? ValueSetter(string path, Type type, object? value, ref bool isCommited);
