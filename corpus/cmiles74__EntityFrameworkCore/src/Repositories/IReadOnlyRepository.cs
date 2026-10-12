using System;
using System.Linq;
using System.Threading.Tasks;
using Nervestaple.EntityFrameworkCore.Models.Criteria;
using Nervestaple.EntityFrameworkCore.Models.Entities;
using Nervestaple.EntityFrameworkCore.Models.Parameters;

namespace Nervestaple.EntityFrameworkCore.Repositories {

    /// <summary>
    /// Provides an interface that all read-only repositories must implement.
    /// </summary>
    /// <typeparam name="ENTITY">Type of Entity</typeparam>
    /// <typeparam name="ID">Type of unique identifier for the Entity</typeparam>
    public interface IReadOnlyRepository<ENTITY, ID> : IDisposable 
        where ENTITY: IEntity<ID>
        where ID: struct {

        /// <summary>
        /// returns the entity with the matching unique identifier
        /// </summary>
        ENTITY Find(ID id);
        
        /// <summary>
        /// returns the entity with the matching unique identifier
        /// </summary>
        Task<ENTITY> FindAsync(ID id);

        /// <summary>
        /// Returns the entities that were returned by the query.
        /// </summary>
        IQueryable<ENTITY> GetEntities();

        /// <summary>
        /// Returns a page of entities built with the provided parameters.
        /// <param name="parameters">Page parameters used to build the page of entities</param>
        /// </summary>
        PagedEntities<ENTITY> Get(IPageParameters parameters);
        
        /// <summary>
        /// Returns a page of entities built with the provided parameters.
        /// <param name="parameters">Page parameters used to build the page of entities</param>
        /// </summary>
        Task<PagedEntities<ENTITY>> GetAsync(IPageParameters parameters);

        /// <summary>
        /// Queries for matching entities using the provided search criteria and page parameters.
        /// <param name="searchCriteria">Search criteria for the query</param>
        /// <param name="parameters">Page parameters used to select the page of entities</param>
        /// </summary>
        PagedEntities<ENTITY> Query(ISearchCriteria<ENTITY, ID> searchCriteria, IPageParameters parameters);
        
        /// <summary>
        /// Queries for matching entities using the provided search criteria and page parameters.
        /// <param name="searchCriteria">Search criteria for the query</param>
        /// <param name="parameters">Page parameters used to select the page of entities</param>
        /// </summary>
        Task<PagedEntities<ENTITY>> QueryAsync(ISearchCriteria<ENTITY, ID> searchCriteria, IPageParameters parameters);
    }
}