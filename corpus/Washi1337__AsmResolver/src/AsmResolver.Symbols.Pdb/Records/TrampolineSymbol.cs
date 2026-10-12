namespace AsmResolver.Symbols.Pdb.Records;

/// <summary>
/// Represents a trampoline symbol.
/// </summary>
public partial class TrampolineSymbol : CodeViewSymbol
{
    /// <summary>
    /// Initializes an empty trampoline symbol.
    /// </summary>
    protected TrampolineSymbol()
    {
    }

    /// <summary>
    /// Creates a new trampoline symbol.
    /// </summary>
    /// <param name="kind">The trampoline kind.</param>
    /// <param name="thunkSize">The size of the thunk, in bytes.</param>
    /// <param name="thunkOffset">The offset within the segment of the thunk, in bytes.</param>
    /// <param name="targetOffset">The offset within the segment of the target, in bytes.</param>
    /// <param name="thunkSegmentIndex">The index of the segment the thunk is in.</param>
    /// <param name="targetSegmentIndex">The index of the segment the target is in.</param>
    public TrampolineSymbol(TrampolineSymbolKind kind, ushort thunkSize, uint thunkOffset, uint targetOffset, ushort thunkSegmentIndex, ushort targetSegmentIndex)
    {
        Kind = kind;
        ThunkSize = thunkSize;
        ThunkOffset = thunkOffset;
        TargetOffset = targetOffset;
        ThunkSegmentIndex = thunkSegmentIndex;
        TargetSegmentIndex = targetSegmentIndex;
    }

    /// <summary>
    /// Gets or sets the trampoline kind.
    /// </summary>
    public TrampolineSymbolKind Kind
    {
        get;
        set;
    }

    /// <summary>
    /// Gets or sets the size of the thunk in bytes.
    /// </summary>
    public ushort ThunkSize
    {
        get;
        set;
    }

    /// <summary>
    /// Gets or sets the offset within the segment the thunk is defined in.
    /// </summary>
    public uint ThunkOffset
    {
        get;
        set;
    }

    /// <summary>
    /// Gets or sets the offset within the segment the target is defined in.
    /// </summary>
    public uint TargetOffset
    {
        get;
        set;
    }

    /// <summary>
    /// Gets or sets the index of the segment the thunk is defined in.
    /// </summary>
    public ushort ThunkSegmentIndex
    {
        get;
        set;
    }

    /// <summary>
    /// Gets or sets the index of the segment the target is defined in.
    /// </summary>
    public ushort TargetSegmentIndex
    {
        get;
        set;
    }

    /// <inheritdoc/>
    public override CodeViewSymbolType CodeViewSymbolType => CodeViewSymbolType.Trampoline;

    /// <inheritdoc />
    public override string ToString()
    {
        return $"S_TRAMPOLINE: [{TargetSegmentIndex:X4}:{TargetOffset:X8}] [{ThunkSegmentIndex:X4}:{ThunkOffset:X8}]";
    }
}

/// <summary>
/// Provides members defining all possible trampoline symbol kinds.
/// </summary>
public enum TrampolineSymbolKind : ushort
{
#pragma warning disable CS1591
    Incremental = 0x0,
    BranchIsland = 0x1
#pragma warning restore CS1591
}
