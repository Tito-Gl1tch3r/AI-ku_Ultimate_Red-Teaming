using System;
using System.Collections.Generic;
using System.IO;
using AsmResolver.DotNet.Serialized;
using AsmResolver.IO;

namespace AsmResolver.DotNet;

/// <summary>
/// Provides an implementation of an assembly resolver that includes the global assembly cache (GAC), as well
/// as any custom search directories.
/// </summary>
public class DotNetFxAssemblyResolver : AssemblyResolverBase
{
    private readonly DotNetFxInstallation? _installation;

    /// <summary>
    /// Creates a new .NET FX assembly resolver.
    /// </summary>
    public DotNetFxAssemblyResolver(
        Version runtimeVersion,
        bool is32Bit,
        DotNetFxPathProvider? pathProvider = null,
        ModuleReaderParameters? readerParameters = null)
        : base(readerParameters ?? new ModuleReaderParameters(UncachedFileService.Instance))
    {
        pathProvider ??= DotNetFxPathProvider.Default;
        if (!pathProvider.TryGetCompatibleRuntime(runtimeVersion, is32Bit, out _installation))
            pathProvider.TryGetCompatibleReferenceRuntime(runtimeVersion, is32Bit, out _installation);
    }

    /// <summary>
    /// Creates a new .NET FX assembly resolver.
    /// </summary>
    public DotNetFxAssemblyResolver(
        DotNetFxInstallation installation,
        ModuleReaderParameters? readerParameters = null)
        : base(readerParameters ?? new ModuleReaderParameters(UncachedFileService.Instance))
    {
        _installation = installation;
    }

    /// <inheritdoc />
    public override string? ProbeAssemblyFilePath(AssemblyDescriptor assembly, ModuleDefinition? originModule)
    {
        string? path = null;

        // At runtime, mscorlib is always loaded from the base installation directory.
        if (path is null && assembly.Name == "mscorlib" && _installation is not null)
            path = Path.Combine(_installation.InstallDirectory, "mscorlib.dll");

        // If public key token is available, try GAC.
        if (path is null && assembly.GetPublicKeyToken() is not null)
            path = ProbeRuntimeDirectories(assembly);

        // Try search directories.
        path ??= ProbeSearchDirectories(assembly, originModule);

        return path;
    }

    private string? ProbeRuntimeDirectories(AssemblyDescriptor assembly)
    {
        if (_installation is null)
            return null;

        return ProbeGacDirectories(_installation.GacDirectories)
            ?? ProbeGacDirectories(_installation.GacMsilDirectories)
            ?? ProbeDirectory(assembly, _installation.InstallDirectory)
            ?? (!string.IsNullOrEmpty(_installation.FacadesDirectory)
                ? ProbeDirectory(assembly, _installation.FacadesDirectory!)
                : null);

        string? ProbeGacDirectories(IList<GacDirectory> directories)
        {
            for (int i = 0; i < directories.Count; i++)
            {
                if (directories[i].Probe(assembly) is { } p)
                    return p;
            }

            return null;
        }
    }
}
