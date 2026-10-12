using System;

namespace AsmResolver.DotNet;

/// <summary>
/// Describes a .NET FX installation.
/// </summary>
/// <param name="version">The version of the runtime.</param>
/// <param name="installDirectory">The base directory all libraries are installed in.</param>
/// <param name="facadesDirectory">The base directory all facade libraries are installed in (when available).</param>
/// <param name="gacDirectories">The collection of relevant architecture-specific Global Assembly Cache (GAC) directories to consider.</param>
/// <param name="gacMsilDirectories">The collection of relevant architecture-independent Global Assembly Cache (GAC) directories to consider.</param>
public sealed class DotNetFxInstallation(
    Version version,
    string installDirectory,
    string? facadesDirectory,
    GacDirectory[] gacDirectories,
    GacDirectory[] gacMsilDirectories
)
{
    /// <summary>
    /// Gets the version of the runtime.
    /// </summary>
    public Version Version { get; } = version;

    /// <summary>
    /// Gets the base directory all libraries are installed in.
    /// </summary>
    public string InstallDirectory { get; } = installDirectory;

    /// <summary>
    /// When available, gets the base directory all facade libraries are installed in.
    /// </summary>
    public string? FacadesDirectory { get; } = facadesDirectory;

    /// <summary>
    /// Gets the collection of relevant architecture-specific Global Assembly Cache (GAC) directories to consider.
    /// </summary>
    public GacDirectory[] GacDirectories { get; } = gacDirectories;

    /// <summary>
    /// Gets the collection of relevant architecture-independent Global Assembly Cache (GAC) directories to consider.
    /// </summary>
    public GacDirectory[] GacMsilDirectories { get; } = gacMsilDirectories;
}
