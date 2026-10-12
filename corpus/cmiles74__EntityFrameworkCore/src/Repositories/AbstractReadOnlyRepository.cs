using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Nervestaple.EntityFrameworkCore.Models.Criteria;
using Nervestaple.EntityFrameworkCore.Models.Entities;
using Nervestaple.EntityFrameworkCore.Models.Parameters;

namespace Nervestaple.EntityFrameworkCore.Repositories {

    /// <summary>
    /// Provides a generic read-only repository that may be extended to create
    /// a specific repository.
    /// </summary>
    /// <typeparam name="TEntity">Type of Entity</typeparam>
    /// <typeparam name="TId">Type of unique identifier for the Entity</typeparam>
    public class AbstractReadOnlyRepository<TEntity, TId> : AbstractRepository, IReadOnlyRepository<TEntity, TId> 
        where TEntity : Entity<TId>
        where TId : struct  {

        /// <summary>
        /// SortBuilder used to sort queryables of instances.
        /// </summary>
        /// <returns>sort builder instance</returns>
        protected readonly SortBuilder<TEntity, TId> SortBuilder = new SortBuilder<TEntity, TId>();
        
        /// <summary>
        /// Creates a new repository instance.
        /// </summary>
        /// <param name="context">the database context to use</param>
        /// <returns>a new instance</returns>
        public AbstractReadOnlyRepository(DbContext context) : base(context) {

        }

        /// <summary>
        /// Returns a queryable of entities.
        /// </summary>
        public virtual IQueryable<TEntity> GetEntities()
        {
            return Context.Set<TEntity>();
        }

        /// <inheritdoc/>
        public PagedEntities<TEntity> Get(IPageParameters parameters) {
            return GetAsync(parameters).Result;
        }

        /// <inheritdoc/>
        public async Task<PagedEntities<TEntity>> GetAsync(IPageParameters parameters) {
            return await PageEntitiesAsync(HandleSorts(GetEntities(), parameters.GetSort()), parameters);
        }

        /// <inheritdoc/>
        public TEntity Find(TId id) {
            return FindAsync(id).Result;
        }
        
        /// <inheritdoc />
        public async Task<TEntity> FindAsync(TId id) {
            return await GetEntities().FirstOrDefaultAsync( e => e.Id.Equals(id));
        }

        /// <inheritdoc/>
        public PagedEntities<TEntity> Query(ISearchCriteria<TEntity, TId> searchCriteria, IPageParameters parameters) {
            return QueryAsync(searchCriteria, parameters).Result;
        }

        /// <inheritdoc/>
        public async Task<PagedEntities<TEntity>> QueryAsync(ISearchCriteria<TEntity, TId> searchCriteria, IPageParameters parameters) {
            IQueryable<TEntity> entities = QueryBuilder<TEntity, TId>.GetResults(GetEntities(), searchCriteria);
            entities = PostProcessQuery(searchCriteria, entities);
            return await PageEntitiesAsync(HandleSorts(entities, parameters.GetSort()), parameters);
        }

        /// <summary>
        /// Performs the paging of a queryable set of entities based on the
        /// provided set of page parameters.
        /// </summary>
        /// <param name="entities">queryable of entities</param>
        /// <param name="parameters">parameters used to create page</param>
        /// <returns></returns>
        protected virtual PagedEntities<TEntity> PageEntities(IQueryable<TEntity> entities, IPageParameters parameters) {
            return PageEntitiesAsync(entities, parameters).Result;
        }
        
        /// <summary>
        /// Performs the paging of a queryable set of entities based on the
        /// provided set of page parameters.
        /// </summary>
        /// <param name="entities">queryable of entities</param>
        /// <param name="parameters">parameters used to create page</param>
        /// <returns></returns>
        protected virtual async Task<PagedEntities<TEntity>> PageEntitiesAsync(IQueryable<TEntity> entities, IPageParameters parameters) {
            int rows = await entities.CountAsync();             
            int pages = ComputePages(parameters, entities);
            var entitiesPaged = await PostPagingAsync(entities.Skip(parameters.Page * parameters.Size)
                .Take(parameters.Size));
            var entitiesOut = await entitiesPaged.ToListAsync();
            return new PagedEntities<TEntity>(parameters, pages, rows, entitiesOut);
        }

        /// <summary>
        /// When we join across multiple entities and return a Queryable of the
        /// JoinedEntity type, we lose the Include(...) relationship between
        /// the entities. You may override this method to put those Include(...)
        /// items back on the entities.
        /// </summary>
        /// <param name="entities"></param>
        /// <returns></returns>
        protected virtual IQueryable<TEntity> PostPaging(IQueryable<TEntity> entities) {
            return PostPagingAsync(entities).Result;
        }
        
        /// <summary>
        /// When we join across multiple entities and return a Queryable of the
        /// JoinedEntity type, we lose the Include(...) relationship between
        /// the entities. You may override this method to put those Include(...)
        /// items back on the entities.
        /// </summary>
        /// <param name="entities"></param>
        /// <returns></returns>
        protected virtual async Task<IQueryable<TEntity>> PostPagingAsync(IQueryable<TEntity> entities) {
            return entities;
        }

        /// <summary>
        /// Performs the sorting of a set of entities based on the provided 
        /// enumerable of sort parameters.
        /// </summary>
        /// <param name="entities">queryable of entities</param>
        /// <param name="sorts">enumerable of sort parameters</param>
        /// <returns></returns>
        protected virtual IQueryable<TEntity> HandleSorts(IQueryable<TEntity> entities, IEnumerable<SortParameter> sorts) {
            return SortBuilder.GetSorts(entities, sorts);
        }

        /// <summary>
        /// Provides a method that you may override if you need to do any post-
        /// processing after the "Get" method fetches a queryable of instances.
        /// </summary>
        /// <param name="queryable">queryable of instances</param>
        /// <returns>queryable of instances</returns>
        protected virtual IQueryable<TEntity> PostProcessGet(IQueryable<TEntity> queryable)
        {
            return queryable;   
        }

        /// <summary>
        /// Provides a method that you may override if you need to do any post-
        /// processing after the "Query" method fetches a queryable of
        /// instances.
        /// </summary>
        /// <param name="searchCriteria">search criteria applied</param>
        /// <param name="queryable">queryable of instances</param>
        /// <returns>queryable of instances</returns>
        protected virtual IQueryable<TEntity> PostProcessQuery(ISearchCriteria<TEntity, TId> searchCriteria, IQueryable<TEntity> queryable) {
            return queryable;
        }

        /// <summary>
        /// Computes the total number of pages in that may be created from the
        /// provided queryable of instances. This method is provided as a 
        /// convenience, should you need to page results.
        /// </summary>
        /// <param name="pageParameters">parameters used when fetching page</param>
        /// <param name="queryable">queryable of instances</param>
        /// <returns></returns>
        protected int ComputePages(IPageParameters pageParameters, IQueryable<TEntity> queryable) {
            int rows = queryable.Count();
            int pages = 0;
            
            if(rows > 0) {

                bool even = (rows % pageParameters.Size) == 0;

                if(even) {
                    pages = rows / pageParameters.Size - 1;
                } else {
                    pages = rows / pageParameters.Size;
                }
                
                // we have more than one row, we have at least one page
                if (pages == 0) {
                    pages = 1;
                }
            }

            return pages;
        }

        /// <summary>
        /// Performs the paging of a queryable set of anonymous instances based 
        /// on the provided set of page parameters.
        /// </summary>
        /// <param name="entities">queryable of anonymous instances</param>
        /// <param name="parameters">parameters used to create page</param>
        /// <returns></returns>
        protected PagedEntities<object> PageAnonymous(IQueryable<object> entities, IPageParameters parameters) {
            return PageAnonymousAsync(entities, parameters).Result;
        }
        
        /// <summary>
        /// Performs the paging of a queryable set of anonymous instances based 
        /// on the provided set of page parameters.
        /// </summary>
        /// <param name="entities">queryable of anonymous instances</param>
        /// <param name="parameters">parameters used to create page</param>
        /// <returns></returns>
        protected async Task<PagedEntities<object>> PageAnonymousAsync(IQueryable<object> entities, IPageParameters parameters) {
            int rows = await entities.CountAsync();             
            int pages = ComputePagesAnonymous(parameters, entities);
            var entitiesOut = await entities.Skip(parameters.Page * parameters.Size).Take(parameters.Size).ToListAsync();
            return new PagedEntities<object>(parameters, pages, rows, entitiesOut);
        }

        /// <summary>
        /// Computes the total number of pages in that may be created from the
        /// provided queryable of anonymous instances. This method is provided 
        /// as a convenience, should you need to page results.
        /// </summary>
        /// <param name="pageParameters">parameters used when fetching page</param>
        /// <param name="queryable">queryable of anonymous instances</param>
        /// <returns></returns>
        protected int ComputePagesAnonymous(IPageParameters pageParameters, IQueryable<object> queryable) {
            int rows = queryable.Count();
            int pages = 0;
            
            if(rows > 0) {

                bool even = (rows % pageParameters.Size) == 0;

                if(even) {
                    pages = rows / pageParameters.Size - 1;
                } else {
                    pages = rows / pageParameters.Size;
                }
            }

            return pages;
        }
    }
}