using System.ComponentModel.DataAnnotations.Schema;
using Newtonsoft.Json;

namespace Nervestaple.EntityFrameworkCore.Models.Entities {

    /// <summary>
    /// Provides an Entity that has a StringIdentifier as it's primary key.
    ///
    /// This entity maps it's database primary key to the "DbId" property, this
    /// is then used to provide the StringIdentifier struct that is used by the
    /// exposed API as the identifier.
    /// </summary>
    public abstract class StringIdentifierEntity : Entity<StringIdentifier> {

        /// <summary>
        /// The underlying unique identifier of the instance.
        /// </summary>
        [JsonProperty("id")]
        public virtual string DbId { get; set; }

        /// <summary>
        /// Returns a string with the attribute name of the Id (mapped to database 
        /// primary key) field
        /// </summary>
        public override string IdAttribute() {
            return "DbId";
        }

        /// <summary>
        /// Unique ID of the instance.
        /// </summary>
        [JsonIgnore]
        [NotMapped]
        public override StringIdentifier? Id {
            get 
            {
                return new StringIdentifier(DbId);
            }

            set
            {
                if (value.HasValue) {
                    this.DbId = value.Value.Identifier;
                }
            }
        }

    }
}