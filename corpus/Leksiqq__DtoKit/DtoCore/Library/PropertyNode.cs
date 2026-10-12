using System.Reflection;

namespace Net.Leksi.Dto
{

    /// <summary>
    /// <para xml:lang="ru">
    /// Узел или лист дерева "свойств и типов" для кеширования рефлексии и программирования построения объектов
    /// </para>
    /// <para xml:lang="en">
    /// Node or leaf of the "properties and types" tree for reflection caching and object building programming
    /// </para>
    /// </summary>
    public class PropertyNode
    {
        /// <summary>
        /// <para xml:lang="ru">
        /// Имя свойства, определённого в интерфейсе
        /// </para>
        /// <para xml:lang="en">
        /// The name of the property defined in the interface
        /// </para>
        /// </summary>
        public string? Name { get; set; } = null;
        /// <summary>
        /// <para xml:lang="ru">
        /// Рефлекесия свойства, определённого в классе
        /// </para>
        /// <para xml:lang="en">
        /// Reflection of the property defined in the class
        /// </para>
        /// </summary>
        public PropertyInfo? PropertyInfo { get; set; } = null;
        /// <summary>
        /// <para xml:lang="ru">
        /// Описание типа свойства, определённого в интерфейсе <see cref="TypeNode"/>
        /// </para>
        /// <para xml:lang="en">
        /// Description of the property type defined in the interface <see cref="TypeNode"/>
        /// </para>
        /// </summary>
        public TypeNode TypeNode { get; set; } = null!;
        /// <summary>
        /// <para xml:lang="ru">
        /// Определяет, может ли данное свойство быть обнулено, то есть имеет ли &quot;?&quot; в определении типа
        /// </para>
        /// <para xml:lang="en">
        /// Determines if this property can be nulled, i.e. has &quot;?&quot; in the type definition
        /// </para>       
        /// </summary>
        public bool IsNullable { get; set; } = false;
        /// <summary>
        /// <para xml:lang="ru">
        /// Определяет, является ли узел листом
        /// Это верно для любых типов, не зарегистрированных в <see cref="DtoServiceProvider"/>
        /// </para>
        /// <para xml:lang="en">
        /// Determines if the node is a leaf
        /// This is true for any types not registered with <see cref="DtoServiceProvider"/>
        /// </para>
        /// </summary>
        public bool IsLeaf => TypeNode.ChildNodes is null;
        /// <summary>
        /// 
        /// </summary>
        public bool IsKey { get; internal set; } = false;
    }
}
