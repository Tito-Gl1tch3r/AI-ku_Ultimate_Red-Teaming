using System;
using System.Collections.Generic;
using System.Diagnostics.CodeAnalysis;
using System.IO;
using System.Linq;
using AsmResolver.Shims;

namespace AsmResolver.DotNet;

/// <summary>
/// Provides a mechanism for looking up runtime libraries in a Mono installation folder.
/// </summary>
public sealed class MonoPathProvider : DotNetFxPathProvider
{
    private record struct MonoInstallation(Version Version, string Directory);

    private static readonly string[] DefaultMonoWindowsPaths = [
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Mono")
    ];

    private static readonly string[] DefaultMonoUnixPaths = [
        "/usr/lib/mono",
        "/lib/mono"
    ];

    private readonly DotNetFxInstallation[] _installs = [];
    private readonly DotNetFxInstallation[] _referenceInstalls = [];
    private readonly GacDirectory[] _gac = [];

    static MonoPathProvider()
    {
        DefaultInstallDirectory = FindMonoPath();
        Default = new MonoPathProvider(DefaultInstallDirectory);
    }

    /// <summary>
    /// Creates a mono path provider using the provided Mono installation path.
    /// </summary>
    public MonoPathProvider(string? installDirectory)
    {
        if (installDirectory is null || !Directory.Exists(installDirectory))
            return;

        InstallDirectory = installDirectory;

        string gac = Path.Combine(installDirectory, "gac");
        if (Directory.Exists(gac))
            _gac = [new GacDirectory(gac)];

        DetectMonoRuntimes(installDirectory, out var apiDirectories, out var implDirectories);
        _installs = implDirectories.OrderByDescending(x => x.Version).Select(ToDotNetFxRuntime).ToArray();
        _referenceInstalls = apiDirectories.OrderByDescending(x => x.Version).Select(ToDotNetFxRuntime).ToArray();
    }

    /// <summary>
    /// Gets the path to the Mono installation on the current system.
    /// </summary>
    public static string? DefaultInstallDirectory
    {
        get;
    }

    /// <summary>
    /// Gets the default path provider representing the global Mono installation on the current system.
    /// </summary>
    public new static MonoPathProvider Default
    {
        get;
    }

    /// <summary>
    /// When available, gets the path to the installation directory that this provider considers.
    /// </summary>
    public string? InstallDirectory
    {
        get;
    }

    /// <inheritdoc />
    public override bool TryGetCompatibleRuntime(Version version, bool is32Bit, [NotNullWhen(true)] out DotNetFxInstallation? runtime)
    {
        foreach (var candidate in _installs)
        {
            if (candidate.Version <= version)
            {
                runtime = candidate;
                return true;
            }
        }

        runtime = null;
        return false;
    }

    /// <inheritdoc />
    public override bool TryGetCompatibleReferenceRuntime(Version version, bool is32Bit, [NotNullWhen(true)] out DotNetFxInstallation? runtime)
    {
        foreach (var candidate in _referenceInstalls)
        {
            if (candidate.Version <= version)
            {
                runtime = candidate;
                return true;
            }
        }

        runtime = null;
        return false;
    }

    private static void DetectMonoRuntimes(
        string installDirectory,
        out List<MonoInstallation> apiDirectories,
        out List<MonoInstallation> implDirectories)
    {
        apiDirectories = [];
        implDirectories = [];

        foreach (string directory in Directory.GetDirectories(installDirectory))
        {
            string directoryName = Path.GetFileName(directory)!;

            // We're looking for directories in the format "x.x[.x]" or "x.x[.x]-api"
            if (!char.IsDigit(directoryName[0]) || directoryName[1] != '.')
                continue;

            string versionString = directoryName;
            var collection = implDirectories;

            // Are we a reference implementation directory?
            if (versionString.EndsWith("-api"))
            {
                versionString = directoryName.Remove(directoryName.Length - 4);
                collection = apiDirectories;
            }

            // Try parse the name as a version number.
            if (!VersionShim.TryParse(versionString, out var version))
                continue;

            collection.Add(new MonoInstallation(version, directory));
        }
    }

    private DotNetFxInstallation ToDotNetFxRuntime(MonoInstallation installation)
    {
        string directory = installation.Directory;
        string? facadesDirectory = Path.Combine(directory, "Facades");
        if (!Directory.Exists(facadesDirectory))
            facadesDirectory = null;

        return new DotNetFxInstallation(
            installation.Version,
            directory,
            facadesDirectory,
            [],
            _gac
        );
    }

    private static string? FindMonoPath()
    {
        string? path = null;

        // Try platform-specific detection mechanisms first.
        if (RuntimeInformationShim.IsRunningOnWindows)
            path = FindWindowsMonoPath();
        else if (RuntimeInformationShim.IsRunningOnUnix)
            path = FindUnixMonoPath();

        // If we're still unsure, we can try to get the mono runtime directory if we're currently running under mono.
        path ??= FindReflectionMonoPath();

        return path;
    }

#if NET8_0_OR_GREATER
    [UnconditionalSuppressMessage("SingleFile", "IL3000", Justification = "We're explicitly checking for this scenario.")]
#endif
    private static string? FindReflectionMonoPath()
    {
        if (Type.GetType("Mono.Runtime") is not { } monoRuntimeType)
            return null;

        // <base>/x.x/mscorlib.dll
        string? versionPath = Path.GetDirectoryName(monoRuntimeType.Assembly.Location);
        string? baseInstallationPath = Path.GetDirectoryName(versionPath);

        return Directory.Exists(baseInstallationPath)
            ? baseInstallationPath
            : null;
    }

    private static string? FindWindowsMonoPath()
    {
        // Try common windows installs.
        foreach (string knownPath in DefaultMonoWindowsPaths)
        {
            if (Directory.Exists(knownPath))
                return knownPath;
        }

        return null;
    }

    private static string? FindUnixMonoPath()
    {
        // Try common unix installs first.
        foreach (string knownPath in DefaultMonoUnixPaths)
        {
            if (Directory.Exists(knownPath))
                return knownPath;
        }

        // If we're running on nix, we need to get it from the nix package.
        if (Directory.Exists("/nix/store") && FindNixMonoPath() is { } nixPath)
            return nixPath;

        return null;
    }

    private static string? FindNixMonoPath()
    {
        // Probe "mono" from PATH. It will be in "<nix-mono-root>/bin/mono".
        // The stdlib libraries are then located in "<nix-mono-root>/lib/mono"
        string[]? paths = Environment.GetEnvironmentVariable("PATH")?.Split(Path.PathSeparator);
        if (paths is null)
            return null;

        foreach (string path in paths)
        {
            string candidateMonoBinaryPath = Path.Combine(path, "mono");
            if (File.Exists(candidateMonoBinaryPath)
                && NativeMethods.RealPath(candidateMonoBinaryPath) is { } binaryPath
                && Path.GetDirectoryName(Path.GetDirectoryName(binaryPath)) is { } rootPath
                && PathShim.Combine(rootPath, "lib", "mono") is { } installPath
                && Directory.Exists(installPath))
            {
                return installPath;
            }
        }

        return null;
    }
}
