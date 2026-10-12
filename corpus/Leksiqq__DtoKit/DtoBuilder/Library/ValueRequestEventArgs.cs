namespace Net.Leksi.Dto;

/// <summary>
/// <para xml:lang="ru">
/// Потомок <see cref="EventArgs"/>, для передачи в <see cref="ValueRequestEventHandler"/>
/// </para>
/// <para xml:lang="en">
/// Child of <see cref="EventArgs"/>, to be passed to <see cref="ValueRequestEventHandler"/>
/// </para>
/// </summary>
public class ValueRequestEventArgs : EventArgs
{
    private PropertyNode _propertyNode = null!;
    private string _path = null!;
    private object _target = null!;
    private bool _isReset = false;

    /// <summary>
    /// <para xml:lang="ru">
    /// Сигнализирует, что было присвоено значение <code>null</code>
    /// </para>
    /// <para xml:lang="en">
    /// Signals that <code>null</code> has been assigned
    /// </para>
    /// </summary>
    internal bool IsReset => _isReset;

    /// <summary>
    /// <para xml:lang="ru">
    /// Инициализирует текущий аргумент
    /// </para>
    /// <para xml:lang="en">
    /// Initializes the current argument
    /// </para>
    /// </summary>
    internal void Init(PropertyNode propertyNode, object target, string path)
    {
        _propertyNode = propertyNode;
        _path = path;
        _target = target;
        IsCommited = false;
        _isReset = false;
    }

    /// <summary>
    /// <para xml:lang="ru">
    /// Тип объекта корневого уровня
    /// </para>
    /// <para xml:lang="en">
    /// Type of the root level object
    /// </para>
    /// </summary>
    public Type RootType { get; internal set; } = null!;

    /// <summary>
    /// <para xml:lang="ru">
    /// Значение текущего узла или листа дерева объекта
    /// </para>
    /// <para xml:lang="en">
    /// The value of the current node or leaf of the object tree
    /// </para>
    /// </summary>
    public object? Value
    {
        get
        {
            return (IsLeaf) ? _propertyNode.PropertyInfo?.GetValue(_target) : (_isReset ? null : _target);
        }
        set
        {
            if(!IsNullable && value is null)
            {
                throw new InvalidOperationException($"At not nullable request \"{ Path }\" null can not be assigned.");
            }
            if (!IsLeaf)
            {
                if(value is null)
                {
                    _isReset = true;
                }
                else if (!object.ReferenceEquals(value, _target))
                {
                    _target = value!;
                    _isReset = false;
                }
            }
            else
            {
                _propertyNode.PropertyInfo!.SetValue(_target, value);
                IsCommited = true;
            }
        }
    }

    /// <summary>
    /// <para xml:lang="ru">
    /// Указывает, принимает ли соответствующее свойство значения <code>null</code>
    /// </para>
    /// <para xml:lang="en">
    /// Indicates whether the corresponding property accepts <code>null</code> values
    /// </para>
    /// </summary>
    public bool IsNullable => _propertyNode.IsNullable;

    /// <summary>
    /// <para xml:lang="ru">
    /// Указывает, является ли данный узел листом
    /// </para>
    /// <para xml:lang="en">
    /// Indicates if this node is a leaf
    /// </para>
    /// </summary>
    public bool IsLeaf => _propertyNode.IsLeaf;

    /// <summary>
    /// <para xml:lang="ru">
    /// Абсолютный путь от корня дерева объекта
    /// </para>
    /// <para xml:lang="en">
    /// Absolute path from the root of the object tree
    /// </para>
    /// </summary>
    public string Path => _path;

    /// <summary>
    /// <para xml:lang="ru">
    /// Тип узла дерева применённого интерфейса, соответствующего текущему узлу дерева объекта
    /// </para>
    /// <para xml:lang="en">
    /// The type of the tree node of the applied interface corresponding to the current tree node of the object
    /// </para>
    /// </summary>
    public Type NominalType => _propertyNode.TypeNode.Type;

    /// <summary>
    /// <para xml:lang="ru">
    /// Тип текущего узла дерева объекта
    /// </para>
    /// <para xml:lang="en">
    /// Type of the current node of the object tree
    /// </para>
    /// </summary>
    public Type ActualType => _propertyNode.PropertyInfo?.PropertyType ?? _target.GetType();

    /// <summary>
    /// <para xml:lang="ru">
    /// Сигнализирует, что текущий узел дерева объекта был завершён
    /// </para>
    /// <para xml:lang="en">
    /// Signals that the current object tree node has been commited
    /// </para>
    /// </summary>
    public bool IsCommited { get; set; } = false;

}
