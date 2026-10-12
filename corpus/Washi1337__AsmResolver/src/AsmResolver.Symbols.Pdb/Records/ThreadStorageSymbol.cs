using AsmResolver.Symbols.Pdb.Leaves;

namespace AsmResolver.Symbols.Pdb.Records;

/// <summary>
/// Represents a thread storage symbol stored in a PDB symbol stream.
/// </summary>
public partial class ThreadStorageSymbol : CodeViewSymbol, IVariableSymbol
{
    /// <summary>
    /// Initializes an empty thread storage symbol.
    /// </summary>
    protected ThreadStorageSymbol()
    {
    }

    /// <summary>
    /// Creates a new named thread storage.
    /// </summary>
    /// <param name="name">The name of the symbol.</param>
    /// <param name="variableType">The data type of the symbol.</param>
    public ThreadStorageSymbol(Utf8String name, CodeViewTypeRecord variableType)
    {
        Name = name;
        VariableType = variableType;
    }

    /// <inheritdoc/>
    public override CodeViewSymbolType CodeViewSymbolType => IsGlobal ? CodeViewSymbolType.GThread32 : CodeViewSymbolType.LThread32;

    /// <summary>
    /// Gets or sets a value indicating whether the symbol is a global thread storage symbol.
    /// </summary>
    public bool IsGlobal
    {
        get;
        set;
    }

    /// <summary>
    /// Gets or sets a value indicating whether the symbol is a local thread storage symbol.
    /// </summary>
    public bool IsLocal
    {
        get => !IsGlobal;
        set => IsGlobal = !value;
    }

    /// <summary>
    /// Gets or sets the file segment index this symbol is located in.
    /// </summary>
    public ushort SegmentIndex
    {
        get;
        set;
    }

    /// <summary>
    /// Gets or sets the offset within the file that this symbol is defined at.
    /// </summary>
    public uint Offset
    {
        get;
        set;
    }

    /// <inheritdoc />
    [LazyProperty]
    public partial CodeViewTypeRecord? VariableType
    {
        get;
        set;
    }

    /// <summary>
    /// Gets or sets the name of the symbol.
    /// </summary>
    [LazyProperty]
    public partial Utf8String? Name
    {
        get;
        set;
    }

    /// <summary>
    /// Obtains the name of the symbol.
    /// </summary>
    /// <returns>The name.</returns>
    /// <remarks>
    /// This method is called upon initialization of the <see cref="Name"/> property.
    /// </remarks>
    protected virtual Utf8String? GetName() => null;

    /// <summary>
    /// Obtains the type of the variable.
    /// </summary>
    /// <returns>The type.</returns>
    /// <remarks>
    /// This method is called upon initialization of the <see cref="VariableType"/> property.
    /// </remarks>
    protected virtual CodeViewTypeRecord? GetVariableType() => null;

    /// <inheritdoc />
    public override string ToString()
    {
        return $"S_{CodeViewSymbolType.ToString().ToUpper()}: [{SegmentIndex:X4}:{Offset:X8}] {VariableType} {Name}";
    }
}
