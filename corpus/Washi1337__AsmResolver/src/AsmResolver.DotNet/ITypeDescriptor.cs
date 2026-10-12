using AsmResolver.DotNet.Signatures;

namespace AsmResolver.DotNet
{
    /// <summary>
    /// Provides members for describing a type in a managed assembly.
    /// </summary>
    public interface ITypeDescriptor : IMemberDescriptor
    {
        /// <summary>
        /// Gets the namespace the type resides in.
        /// </summary>
        string? Namespace
        {
            get;
        }

        /// <summary>
        /// Gets the resolution scope that defines the type.
        /// </summary>
        IResolutionScope? Scope
        {
            get;
        }

        /// <summary>
        /// Determines whether the type is considered a value type or reference type by the runtime.
        /// </summary>
        /// <param name="context">The runtime context that is assumed.</param>
        /// <returns><c>true</c> when the type is considered a value type, <c>false</c> when it is a reference type, <c>null</c> when unknown.</returns>
        bool? TryGetIsValueType(RuntimeContext? context);

        /// <summary>
        /// Attempts to resolve the type reference to its definition, assuming the provided module as resolution context.
        /// </summary>
        /// <param name="context">The context to assume when resolving the type.</param>
        /// <param name="definition">The resolved type definition, or <c>null</c> if the type could not be resolved.</param>
        /// <returns>A value describing the success or failure status of the type resolution.</returns>
        ResolutionStatus Resolve(RuntimeContext? context, out TypeDefinition? definition);

        /// <summary>
        /// Transforms the type descriptor to an instance of a <see cref="ITypeDefOrRef"/>, which can be referenced by
        /// a metadata token.
        /// </summary>
        /// <returns>The constructed TypeDefOrRef instance.</returns>
        ITypeDefOrRef ToTypeDefOrRef();

        /// <summary>
        /// Converts the type in a type signature.
        /// </summary>
        /// <param name="context">The runtime context to assume when creating the signature.</param>
        /// <returns>The new type signature.</returns>
        /// <remarks>
        /// When this type is a signature, gets the underlying type signature instance.
        /// Otherwise, a new signature will be instantiated.
        /// </remarks>
        TypeSignature ToTypeSignature(RuntimeContext? context);
    }
}
