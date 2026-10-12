using System;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Nervestaple.EntityFrameworkCore.Models.Entities;

namespace Nervestaple.EntityFrameworkCore.Repositories {

    /// <summary>
    /// Provides a generic read/write repository that may be extended to create
    /// a specific repository.
    /// </summary>
    /// <typeparam name="TEntity">Type of Entity</typeparam>
    /// <typeparam name="TId">Type of unique identifier for the Entity</typeparam>
    public class AbstractReadWriteRepository<TEntity, TId> : AbstractReadOnlyRepository<TEntity, TId>, 
        IReadWriteRepository<TEntity, TId>
        where TEntity : Entity<TId>
        where TId : struct
    {
        /// <summary>
        /// Creates a new repository instance.
        /// </summary>
        /// <param name="context">the database context to use</param>
        /// <returns>a new instance</returns>
        public AbstractReadWriteRepository(DbContext context) : base(context) {

        }

        /// <inheritdoc/>
        public TEntity Create(EditModel<TEntity, TId> model) {
            return CreateAsync(model).Result;
        }

        /// <inheritdoc />
        public async Task<TEntity> CreateAsync(EditModel<TEntity, TId> model) {
            // create a new instance and populate its fields
            var newInstance = 
                (TEntity) Activator.CreateInstance(typeof(TEntity));
            
            // update the target instance's fields with the model's values
            model.GetType().GetProperties().ToList().ForEach(p => {
                var prop = newInstance.GetType().GetProperties().Where(i => i.Name == p.Name).SingleOrDefault();
                if (prop != null) {
                    prop.SetValue(newInstance, p.GetValue(model));
                }
            });

            // save the instance
            await Context.AddAsync<TEntity>(newInstance);
            newInstance = PostCreate(newInstance, model);
            await Context.SaveChangesAsync();

            // return the new instance
            return newInstance;
        }

        /// <inheritdoc/>
        public TEntity Create(TEntity instance) {
            return CreateAsync(instance).Result;
        }

        /// <inheritdoc/>
        public async Task<TEntity> CreateAsync(TEntity instance) {
            // save the instance
            await Context.AddAsync<TEntity>(instance);
            instance = await PostCreateAsync(instance);
            await Context.SaveChangesAsync();

            // return the new instance
            return instance;
        }

        /// <inheritdoc/>
        public virtual TEntity PostCreate(TEntity instance, EditModel<TEntity, TId> model) {
            return PostCreateAsync(instance, model).Result;
        }

        /// <inheritdoc/>
        public async Task<TEntity> PostCreateAsync(TEntity instance, EditModel<TEntity, TId> model) {
            return instance;
        }

        /// <inheritdoc/>
        public virtual TEntity PostCreate(TEntity instance) {
            return PostCreateAsync(instance).Result;
        }

        /// <inheritdoc/>
        public async Task<TEntity> PostCreateAsync(TEntity instance) {
            return instance;
        }

        /// <inheritdoc/>
        public TEntity Update(TId id, EditModel<TEntity, TId> model) {
            return UpdateAsync(id, model).Result;
        }

        /// <inheritdoc/>
        public async Task<TEntity> UpdateAsync(TId id, EditModel<TEntity, TId> model) {
            return HandlePostUpdateAsync(id, model).Result;
        }

        /// <inheritdoc/>
        public virtual TEntity PostUpdate(TEntity instance, EditModel<TEntity, TId> model) {
            return PostUpdateAsync(instance, model).Result;
        }

        /// <inheritdoc/>
        public async Task<TEntity> PostUpdateAsync(TEntity instance, EditModel<TEntity, TId> model) {
            return instance;
        }

        /// <inheritdoc/>
        public void Delete(TId id)
        {
            DeleteAsync(id).RunSynchronously();
        }

        /// <inheritdoc/>
        public async Task DeleteAsync(TId id) {
            TEntity entity = await FindAsync(id);
            Context.Remove(entity);
            await PostDeleteAsync(id, entity);
            await Context.SaveChangesAsync();
        }

        /// <inheritdoc/>
        public virtual void PostDelete(TId id, TEntity entity) {
            PostDeleteAsync(id, entity).RunSynchronously();
        }

        /// <inheritdoc/>
        public async Task PostDeleteAsync(TId id, TEntity instance) {
            
        }

        /// <summary>
        /// Performs update after the default update has been performed
        /// </summary>
        /// <param name="id">unique identifier of the entity</param>
        /// <param name="model">edit model for the entity</param>
        /// <returns>the updated entity</returns>
        protected virtual TEntity HandlePostUpdate(TId id, EditModel<TEntity, TId> model) {
            return HandlePostUpdateAsync(id, model).Result;
        }
        
        /// <summary>
        /// Performs update after the default update has been performed
        /// </summary>
        /// <param name="id">unique identifier of the entity</param>
        /// <param name="model">edit model for the entity</param>
        /// <returns>the updated entity</returns>
        protected virtual async Task<TEntity> HandlePostUpdateAsync(TId id, EditModel<TEntity, TId> model)
        {
            // fetch the target instance
            var instance = await FindAsync(id);

            // update the target instance's fields with the model's values
            model.GetType().GetProperties().ToList().ForEach(p => {
                var prop = instance.GetType().GetProperties().SingleOrDefault(i => i.Name == p.Name);
                if (prop != null) {
                    prop.SetValue(instance, p.GetValue(model));
                }
            });

            // save and return the target instance
            Context.Update(instance);
            instance = await PostUpdateAsync(instance, model);
            await Context.SaveChangesAsync();
            return instance;
        }
        
        /// <summary>
        /// Returns the value for the provided model's property
        /// </summary>
        /// <param name="model">the update model object</param>
        /// <param name="property">string with the model's property name</param>
        /// <typeparam name="TType">type for the model's property</typeparam>
        protected TType GetModelPropertyValue<TType>(object model, string property)
        {
            var prop = model.GetType().GetProperties().SingleOrDefault(p => p.Name.Equals(property));
            if (prop != null)
            {
                return prop.GetValue(model) != null ? (TType) prop.GetValue(model) : default(TType);
            }

            return default(TType);
        }
    }
}