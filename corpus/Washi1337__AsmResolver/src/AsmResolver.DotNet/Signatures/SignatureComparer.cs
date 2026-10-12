using System.Collections.Generic;

namespace AsmResolver.DotNet.Signatures
{
    /// <summary>
    /// Provides a mechanism for comparing signatures of members defined in a .NET assembly by their contents.
    /// </summary>
    public partial class SignatureComparer :
        IEqualityComparer<byte[]>
    {
        private const int ElementTypeOffset = 8;
        private const SignatureComparisonFlags DefaultFlags = SignatureComparisonFlags.ExactVersion;

        /// <summary>
        /// An immutable default instance of <see cref="SignatureComparer"/>.
        /// </summary>
        public static SignatureComparer Default { get; } = new();

        /// <summary>
        /// Flags for controlling comparison behavior.
        /// </summary>
        public SignatureComparisonFlags Flags { get; }

        /// <summary>
        /// When available, gets the runtime context that is assumed when comparing types.
        /// </summary>
        /// <remarks>
        /// When <c>null</c>, types are always compared as-is. When non-<c>null</c>, any exported type is resolved first
        /// before doing the comparison.
        /// </remarks>
        public RuntimeContext? RuntimeContext { get; }

        /// <summary>
        /// The default <see cref="SignatureComparer"/> constructor.
        /// </summary>
        public SignatureComparer()
        {
            Flags = DefaultFlags;
        }

        /// <summary>
        /// A <see cref="SignatureComparer"/> constructor with a parameter for specifying the <see cref="Flags"/>
        /// used in comparisons.
        /// </summary>
        /// <param name="flags">The <see cref="Flags"/> used in comparisons.</param>
        public SignatureComparer(SignatureComparisonFlags flags)
            : this(null, flags)
        {
        }

        /// <summary>
        /// A <see cref="SignatureComparer"/> constructor with a parameter for specifying the <see cref="Flags"/>
        /// used in comparisons.
        /// </summary>
        /// <param name="context">The runtime context that is assumed when comparing types.</param>
        public SignatureComparer(RuntimeContext? context)
            : this(context, DefaultFlags)
        {
        }

        /// <summary>
        /// A <see cref="SignatureComparer"/> constructor with a parameter for specifying the <see cref="Flags"/>
        /// used in comparisons.
        /// </summary>
        /// <param name="context">The runtime context that is assumed when comparing types.</param>
        /// <param name="flags">The <see cref="Flags"/> used in comparisons.</param>
        public SignatureComparer(RuntimeContext? context, SignatureComparisonFlags flags)
        {
            RuntimeContext = context;
            Flags = flags;
        }

        /// <inheritdoc />
        public virtual bool Equals(byte[]? x, byte[]? y) => ByteArrayEqualityComparer.Instance.Equals(x, y);

        /// <inheritdoc />
        public virtual int GetHashCode(byte[] obj) => ByteArrayEqualityComparer.Instance.GetHashCode(obj);
    }
}
