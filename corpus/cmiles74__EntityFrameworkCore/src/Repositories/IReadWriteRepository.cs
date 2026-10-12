using System.Threading.Tasks;
using Nervestaple.EntityFrameworkCore.Models.Entities;

namespace Nervestaple.EntityFrameworkCore.Repositories {

    /// <summary>
    /// Provides an interface that all read/write repositories must implement.
    /// </summary>
    /// <typeparam name="ENTITY">Type of Entity</typeparam>
    /// <typeparam name="ID">Type of unique identifier for the Entity</typeparam>
    public interface IReadWriteRepository<ENTITY, ID> : IReadOnlyRepository<ENTITY, ID>
        where ENTITY: Entity<ID>
        where ID: struct 
    {

        /// <summary>
        /// Returns a new entity populated with the provided data.
        /// <param name="model">Data object used to populate the new Entity</param>
        /// </summary>
        ENTITY Create(EditModel<ENTITY, ID> model);
        
        /// <summary>
        /// Returns a new entity populated with the provided data.
        /// <param name="model">Data object used to populate the new Entity</param>
        /// </summary>
        Task<ENTITY> CreateAsync(EditModel<ENTITY, ID> model);
        
        /// <summary>
        /// Adds the provided entity to the persistence context
        /// <param name="instance">Instance to persist</param>
        /// </summary>
        ENTITY Create(ENTITY instance);
        
        /// <summary>
        /// Adds the provided entity to the persistence context
        /// <param name="instance">Instance to persist</param>
        /// </summary>
        Task<ENTITY> CreateAsync(ENTITY instance);

        /// <summary>
        /// Called after creation of the new Entity and before that Entity is 
        /// persisted
        /// </summary>
        ENTITY PostCreate(ENTITY instance, EditModel<ENTITY, ID> model);
        
        /// <summary>
        /// Called after creation of the new Entity and before that Entity is 
        /// persisted
        /// </summary>
        Task<ENTITY> PostCreateAsync(ENTITY instance, EditModel<ENTITY, ID> model);
        
        /// <summary>
        /// Called after creation of the new Entity and before that Entity is 
        /// persisted
        /// </summary>
        ENTITY PostCreate(ENTITY instance);
        
        /// <summary>
        /// Called after creation of the new Entity and before that Entity is 
        /// persisted
        /// </summary>
        Task<ENTITY> PostCreateAsync(ENTITY instance);

        /// <summary>
        /// Returns a current copy of the entity after updating the Entity with
        /// the matching unique identifier with the values provided in the model
        /// <param name="id">Unique ID of the Entity to update</param>
        /// <param name="model">Data object used to update the Entity</param>
        /// </summary>
        ENTITY Update(ID id, EditModel<ENTITY, ID> model);
        
        /// <summary>
        /// Returns a current copy of the entity after updating the Entity with
        /// the matching unique identifier with the values provided in the model
        /// <param name="id">Unique ID of the Entity to update</param>
        /// <param name="model">Data object used to update the Entity</param>
        /// </summary>
        Task<ENTITY> UpdateAsync(ID id, EditModel<ENTITY, ID> model);

        /// <summary>
        /// Called after updating of the Entity and before that Entity is 
        /// persisted
        /// </summary>
        ENTITY PostUpdate(ENTITY instance, EditModel<ENTITY, ID> model);
        
        /// <summary>
        /// Called after updating of the Entity and before that Entity is 
        /// persisted
        /// </summary>
        Task<ENTITY> PostUpdateAsync(ENTITY instance, EditModel<ENTITY, ID> model);
        
        /// <summary>
        /// Deletes the entity with the provided unique identifier.
        /// </summary>
        /// <param name="id">Unique identifier of the entity to delete</param>
        void Delete(ID id);
        
        /// <summary>
        /// Deletes the entity with the provided unique identifier.
        /// </summary>
        /// <param name="id">Unique identifier of the entity to delete</param>
        Task DeleteAsync(ID id);

        /// <summary>
        /// Called after deleting the entity but before committing.
        /// </summary>
        /// <param name="id">Unique identifier of the entity that was deleted</param>
        /// <param name="instance">The instance that will be deleted</param>
        void PostDelete(ID id, ENTITY instance);
        
        /// <summary>
        /// Called after deleting the entity but before committing.
        /// </summary>
        /// <param name="id">Unique identifier of the entity that was deleted</param>
        /// <param name="instance">The instance that will be deleted</param>
        Task PostDeleteAsync(ID id, ENTITY instance);
    }
}