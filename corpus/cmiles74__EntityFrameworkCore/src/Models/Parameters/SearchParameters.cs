using Nervestaple.EntityFrameworkCore.Models.Criteria;
using Nervestaple.EntityFrameworkCore.Models.Entities;

namespace Nervestaple.EntityFrameworkCore.Models.Parameters {

    /// <summary> Provides a base class that all search parameter classes may extend.
    /// </summary>
    /// <typeparam name="ENTITY">Type of Entity</typeparam>
    /// <typeparam name="ID">Type of unique identifier for the Entity</typeparam>
    public abstract class SearchParameters<ENTITY, ID> : ISearchParameters<ENTITY, ID> 
        where ENTITY : IEntity<ID>
        where ID : struct {

        /// <summary>
        /// A set of page parameters indicating how the results of the query
        /// should be returned. This includes the size of each page, which 
        /// page and how the instances should be sorted.
        /// </summary>
        /// <returns>page parameters</returns>
        [QueryIgnore]
        public virtual PageParameters PageParameters { get; set; } = new PageParameters();

        /// <summary>
        /// The actual search parameters used to build the query.
        /// </summary>
        public abstract ISearchCriteria<ENTITY, ID> SearchCriteria { get; }
    }
}