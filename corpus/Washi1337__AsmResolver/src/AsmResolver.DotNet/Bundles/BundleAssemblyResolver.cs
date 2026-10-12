using System.IO;
using AsmResolver.DotNet.Serialized;

namespace AsmResolver.DotNet.Bundles;

/// <summary>
/// Provides an implementation of an assembly resolver that prefers assemblies embedded in single-file-host executable.
/// </summary>
public class BundleAssemblyResolver : IAssemblyResolver
{
    private readonly BundleManifest _manifest;
    private readonly IAssemblyResolver _baseResolver;
    private readonly ModuleReaderParameters _readerParameters;

    /// <summary>
    /// Creates a new bundle assembly resolver.
    /// </summary>
    /// <param name="manifest">The bundle to assume.</param>
    /// <param name="readerParameters">The reader parameters to use when loading dependencies.</param>
    /// <param name="baseResolver">The base resolver to use, or <c>null</c> to use the default resolution mechanism.</param>
    public BundleAssemblyResolver(
        BundleManifest manifest,
        ModuleReaderParameters readerParameters,
        IAssemblyResolver? baseResolver = null)
    {
        _manifest = manifest;

        // Bundles are .NET core 3.1+ only -> we can always default to .NET Core assembly resolution.
        _baseResolver = baseResolver ?? new DotNetCoreAssemblyResolver(
            manifest.GetTargetRuntime().Version,
            readerParameters: readerParameters
        );

        _readerParameters = readerParameters;
    }

    /// <inheritdoc />
    public ResolutionStatus Resolve(AssemblyDescriptor assembly, ModuleDefinition? originModule, out AssemblyDefinition? definition)
    {
        // Prefer embedded files before we forward to the default assembly resolution algorithm.

        var result = TryResolveFromEmbeddedFiles(assembly, out definition);
        if (result != ResolutionStatus.Success)
            result = _baseResolver.Resolve(assembly, originModule, out definition);

        return result;
    }

    private ResolutionStatus TryResolveFromEmbeddedFiles(AssemblyDescriptor assembly, out AssemblyDefinition? definition)
    {
        try
        {
            for (int i = 0; i < _manifest.Files.Count; i++)
            {
                var file = _manifest.Files[i];
                if (file.Type != BundleFileType.Assembly)
                    continue;

                if (Path.GetFileNameWithoutExtension(file.RelativePath) == assembly.Name)
                {
                    definition = AssemblyDefinition.FromBytes(
                        file.GetData(),
                        readerParameters: _readerParameters,
                        createRuntimeContext: false
                    );

                    return ResolutionStatus.Success;
                }
            }
        }
        catch
        {
            definition = null;
            return ResolutionStatus.AssemblyBadImage;
        }

        definition = null;
        return ResolutionStatus.MemberNotFound;
    }
}
