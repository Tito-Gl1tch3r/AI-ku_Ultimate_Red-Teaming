using System;

namespace Nervestaple.EntityFrameworkCore.Models.Entities {

    /// <summary>
    /// A database identifier that is also a string.
    /// </summary>
    public struct StringIdentifier : IComparable<StringIdentifier>
    {
        /// <summary>
        /// The identifier.
        /// </summary>
        public string Identifier { get; set; }

        /// <summary>
        /// Creates a new instance.
        /// <param name="identifier">The identifier</param>
        /// </summary>
        public StringIdentifier(string identifier) {
            this.Identifier = identifier;
        }

        /// <summary>
        /// Returns a string representation of the instance.
        /// </summary>
        public override string ToString() {
            return Identifier;
        }

        /// <inheritdoc/>
        public int CompareTo(StringIdentifier other)
        {
            return this.Identifier.CompareTo(other.Identifier);
        }
    }
}