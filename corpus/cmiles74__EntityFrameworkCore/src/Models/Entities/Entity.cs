using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace Nervestaple.EntityFrameworkCore.Models.Entities { 

    /// <summary>
    /// Provides an interface that all entities must implement.
    /// </summary>
    public interface IEntity {

        /// <summary>
        /// Unique identifier for this entity.
        /// </summary>
        /// <returns>unique identifier</returns>
        object Id { get; }

        /// <summary>
        /// Populates the "meta" dictionary, which is used in the JSON HAL structure.
        /// </summary>
        /// <param name="meta">dictionary of links</param>
        void PopulateMeta(IDictionary<string, object> meta);
    }

    /// <summary>
    /// Provides a base class that all entities must extend.
    /// </summary>
    public abstract class AbstractEntity {
        
    }

    /// <summary>
    /// Provides an interface for entities who have typed unique identifiers.
    /// </summary>
    /// <typeparam name="ENTITY">Type of Entity</typeparam>
    public interface IEntity<ENTITY> : IEntity where ENTITY: struct {

        /// <summary>
        /// Unique identifier for this entity.
        /// </summary>
        /// <returns>unique identifier</returns>
        new ENTITY? Id { get; set; }

        /// <summary>
        /// Populates the "meta" dictionary, which is used in the JSON HAL structure.
        /// </summary>
        /// <param name="meta">dictionary of links</param>
        new void PopulateMeta(IDictionary<string, object> meta);
    }

    /// <summary>
    /// Provides a handy base class that entities may implement that provides
    /// a type for the unique identifier as well as a default mapper for that
    /// identifier.
    /// </summary>
    /// <typeparam name="ID">Type of unique identifier for the Entity</typeparam>
    public abstract class Entity<ID> : AbstractEntity, IEntity<ID> where ID: struct {

        object IEntity.Id {
            get { return this.Id; }
        }

        /// <summary>
        /// Unique identifier for this entity.
        /// </summary>
        /// <returns>unique identifier</returns>
        [Key]
        [DatabaseGenerated(DatabaseGeneratedOption.Identity)]
        public virtual ID? Id { 
            get { return this.Id; }
            set { Id = value; }
        }

        /// <summary>
        /// Returns a string with the attribute name of the Id (mapped to database 
        /// primary key) field
        /// </summary>
        public virtual string IdAttribute() {
            return "id";
        }

        /// <summary>
        /// Populates the "meta" dictionary, which is used in the JSON HAL structure.
        /// </summary>
        /// <param name="meta">dictionary of links</param>
        public virtual void PopulateMeta(IDictionary<string, object> meta) {
            // do nothing
        }

        /// <summary>
        /// Flag indicating if the instance has been persisted to the backing 
        /// store
        /// </summary>
        public bool IsPersisted() {
            return Id != null;
        }
    }
}