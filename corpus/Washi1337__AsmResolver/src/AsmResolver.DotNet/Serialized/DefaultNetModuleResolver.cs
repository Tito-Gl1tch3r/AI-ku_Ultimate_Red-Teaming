using System;
using System.IO;

namespace AsmResolver.DotNet.Serialized
{
    /// <summary>
    /// Provides a basic implementation for a net module resolver, that searches for the net module in a directory.
    /// </summary>
    public class DefaultNetModuleResolver : INetModuleResolver
    {
        /// <summary>
        /// Creates a new net module resolver that searches for the module in a directory.
        /// </summary>
        /// <param name="readerParameters">The parameters to use for reading a module.</param>
        public DefaultNetModuleResolver(ModuleReaderParameters readerParameters)
        {
            ReaderParameters = readerParameters ?? throw new ArgumentNullException(nameof(readerParameters));
        }

        /// <summary>
        /// Gets the parameters to be used for reading a .NET module.
        /// </summary>
        public ModuleReaderParameters ReaderParameters
        {
            get;
        }

        /// <inheritdoc />
        public ModuleDefinition? Resolve(string name, ModuleDefinition originModule)
        {
            if (originModule.FilePath is not { Length: > 0 } filePath
                || Path.GetDirectoryName(filePath) is not { } directory
                || Path.Combine(directory, name) is not {} modulePath
                || !File.Exists(modulePath))
            {
                return null;
            }

            try
            {
                return ModuleDefinition.FromFile(modulePath, ReaderParameters);
            }
            catch
            {
                // Ignore errors.
                return null;
            }
        }

    }
}
