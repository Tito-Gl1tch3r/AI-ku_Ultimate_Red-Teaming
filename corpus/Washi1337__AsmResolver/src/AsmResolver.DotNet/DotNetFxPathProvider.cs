using System;
using System.Diagnostics.CodeAnalysis;
using AsmResolver.Shims;

namespace AsmResolver.DotNet;

/// <summary>
/// Provides a mechanism for locating legacy .NET FX runtime installation directories on a system.
/// </summary>
public abstract class DotNetFxPathProvider
{
    /// <summary>
    /// Gets the system-default .NET FX path provider.
    /// </summary>
    public static DotNetFxPathProvider Default
    {
        get
        {
            if (field is null)
            {
                if (RuntimeInformationShim.IsRunningOnWindows)
                    field = DotNetFrameworkPathProvider.Instance;
                else
                    field = MonoPathProvider.Default;
            }

            return field;
        }
    }

    /// <summary>
    /// Attempts to obtain the most compatible implementation runtime present on the current system given a .NET FX version.
    /// </summary>
    /// <param name="version">The version of the runtime the .NET FX binary is targeting.</param>
    /// <param name="is32Bit"><c>true</c> if the 32-bits version should be preferred.</param>
    /// <param name="runtime">The located runtime installation, or <c>null</c> if none was found.</param>
    /// <returns><c>true</c> if the runtime was located successfully, <c>false</c> otherwise.</returns>
    public abstract bool TryGetCompatibleRuntime(
        Version version,
        bool is32Bit,
        [NotNullWhen(true)] out DotNetFxInstallation? runtime
    );

    /// <summary>
    /// Attempts to obtain the most compatible reference runtime present on the current system given a .NET FX version.
    /// </summary>
    /// <param name="version">The version of the runtime the .NET FX binary is targeting.</param>
    /// <param name="is32Bit"><c>true</c> if the 32-bits version should be preferred.</param>
    /// <param name="runtime">The located runtime installation, or <c>null</c> if none was found.</param>
    /// <returns><c>true</c> if the runtime was located successfully, <c>false</c> otherwise.</returns>
    public abstract bool TryGetCompatibleReferenceRuntime(
        Version version,
        bool is32Bit,
        [NotNullWhen(true)] out DotNetFxInstallation? runtime
    );
}
