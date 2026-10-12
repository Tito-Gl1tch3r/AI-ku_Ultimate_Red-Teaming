namespace AsmResolver.DotNet;

/// <summary>
/// Provides members describing all possible results of a resolution of an assembly or member.
/// </summary>
public enum ResolutionStatus
{
    /// <summary>
    /// Indicates the resolution was successful.
    /// </summary>
    Success,

    /// <summary>
    /// Indicates the reference to be resolved is invalid or incomplete.
    /// </summary>
    InvalidReference,

    /// <summary>
    /// Indicates the reference could not be resolved because no runtime context was provided.
    /// </summary>
    MissingRuntimeContext,

    /// <summary>
    /// Indicates the reference to be resolved defines a circular resolution scope.
    /// </summary>
    CircularResolutionScope,

    /// <summary>
    /// Indicates the requested assembly of the reference to be resolved could not be found.
    /// </summary>
    AssemblyNotFound,

    /// <summary>
    /// Indicates the declaring assembly of the reference to be resolved contained invalid metadata.
    /// </summary>
    AssemblyBadImage,

    /// <summary>
    /// Indicates the module of the reference to be resolved could not be found.
    /// </summary>
    ModuleNotFound,

    /// <summary>
    /// Indicates the requested type could not be found in the resolved declaring assembly.
    /// </summary>
    TypeNotFound,

    /// <summary>
    /// Indicates the requested field or method could not be found in the resolved declaring type.
    /// </summary>
    MemberNotFound,
}
