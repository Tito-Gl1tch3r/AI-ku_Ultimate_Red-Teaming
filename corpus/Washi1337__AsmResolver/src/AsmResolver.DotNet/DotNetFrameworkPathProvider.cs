using System;
using System.Collections.Generic;
using System.Diagnostics.CodeAnalysis;
using System.IO;
using AsmResolver.Shims;

namespace AsmResolver.DotNet;

/// <summary>
/// Provides a mechanism for locating installations of the .NET Framework on a Windows machine.
/// </summary>
public sealed class DotNetFrameworkPathProvider : DotNetFxPathProvider
{
    private record struct GacGroup(GacDirectory[] Gac, GacDirectory[] GacMsil);

    // Note: These are assumed to be sorted in descending order (newest first).
    private readonly DotNetFxInstallation[] _installs32;
    private readonly DotNetFxInstallation[] _installs64;

    private DotNetFrameworkPathProvider()
    {
        string? windowsDirectory = Environment.GetEnvironmentVariable("windir");
        if (string.IsNullOrEmpty(windowsDirectory))
        {
            _installs32 = [];
            _installs64 = [];
            return;
        }

        // Hardcoded implementation paths as they are unlikely to ever change.
        string systemGac = Path.Combine(windowsDirectory, "assembly");
        string frameworkGac = PathShim.Combine(windowsDirectory, "Microsoft.NET", "assembly");

        _installs32 = DetectInstalls(
            PathShim.Combine(windowsDirectory, "Microsoft.NET", "Framework"),
            new GacGroup(
                [
                    new(Path.Combine(systemGac, "GAC")),
                    new(Path.Combine(systemGac, "GAC_32")),
                ],
                [
                    new(Path.Combine(systemGac, "GAC_MSIL"))
                ]
            ),
            new GacGroup(
                [
                    new(Path.Combine(frameworkGac, "GAC"), "v4.0_"),
                    new(Path.Combine(frameworkGac, "GAC_32"), "v4.0_"),
                    new(Path.Combine(systemGac, "GAC")),
                    new(Path.Combine(systemGac, "GAC_32")),
                ],
                [
                    new(Path.Combine(systemGac, "GAC_MSIL")),
                    new(Path.Combine(frameworkGac, "GAC_MSIL"), "v4.0_"),
                ]
            )
        );

        _installs64 = DetectInstalls(
            PathShim.Combine(windowsDirectory, "Microsoft.NET", "Framework64"),
            new GacGroup(
                [
                    new(Path.Combine(systemGac, "GAC")),
                    new(Path.Combine(systemGac, "GAC_64")),
                ],
                [
                    new(Path.Combine(systemGac, "GAC_MSIL"))
                ]
            ),
            new GacGroup(
                [
                    new(Path.Combine(frameworkGac, "GAC"), "v4.0_"),
                    new(Path.Combine(frameworkGac, "GAC_64"), "v4.0_"),
                    new(Path.Combine(systemGac, "GAC")),
                    new(Path.Combine(systemGac, "GAC_64")),
                ],
                [
                    new(Path.Combine(frameworkGac, "GAC_MSIL"), "v4.0_"),
                    new(Path.Combine(systemGac, "GAC_MSIL"))
                ]
            )
        );
    }

    /// <summary>
    /// Gets the singleton instance of the <see cref="DotNetFrameworkPathProvider"/> class.
    /// </summary>
    public static DotNetFrameworkPathProvider Instance
    {
        get;
    } = new();

    private static DotNetFxInstallation[] DetectInstalls(string baseDirectory, GacGroup gacGroup2, GacGroup gacGroup4)
    {
        var result = new List<DotNetFxInstallation>();

        string version4Path = Path.Combine(baseDirectory, "v4.0.30319");
        if (Directory.Exists(version4Path))
        {
            result.Add(new DotNetFxInstallation(
                new Version(4, 0),
                version4Path,
                null,
                gacGroup4.Gac,
                gacGroup4.GacMsil
            ));
        }

        string version2Path = Path.Combine(baseDirectory, "v2.0.50727");
        if (Directory.Exists(version2Path))
        {
            result.Add(new DotNetFxInstallation(
                new Version(2, 0),
                version2Path,
                null,
                gacGroup2.Gac,
                gacGroup2.GacMsil
            ));
        }

        return result.ToArray();
    }

    /// <inheritdoc />
    public override bool TryGetCompatibleRuntime(Version version, bool is32Bit, [NotNullWhen(true)] out DotNetFxInstallation? runtime)
    {
        var candidates = is32Bit? _installs32 :  _installs64;

        foreach (var candidate in candidates)
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
        // TODO:

        runtime = null;
        return false;
    }
}
