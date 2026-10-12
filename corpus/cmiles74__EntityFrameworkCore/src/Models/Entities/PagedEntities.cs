using System.Collections.Generic;
using Nervestaple.EntityFrameworkCore.Models.Parameters;

namespace Nervestaple.EntityFrameworkCore.Models.Entities {

    /// <summary>
    /// Provides a data object that wraps a page of entity instances. It 
    /// includes some metadata about the wrapped collection including a 
    /// count of all instances and the number of pages available.
    /// </summary>
    /// <typeparam name="ENTITY">Type of Entity</typeparam>
    public class PagedEntities<ENTITY> {

        /// <summary>
        /// Page parameters instance indicating the page being returned and the
        /// size of the page
        /// </summary>
        public IPageParameters PageParameters { get; set; } = new PageParameters();

        /// <summary>
        /// the number of pages in the collection
        /// </summary>
        public int Pages { get; set; } = 0;

        /// <summary>
        /// the number of items in the collection
        /// </summary>
        public int Count { get; set; } = 0;

        /// <summary>
        /// collection of resource being returned
        /// </summary>
        public IEnumerable<ENTITY> Resource { get; set; }

        /// <summary>
        /// Creates a new collection of paged entities.
        /// <param name="pageParameters">Parameters indicating which page to fetch</param>
        /// <param name="pages">The total number of pages in the complete result set</param>
        /// <param name="count">The total number of instances in the complete result set</param>
        /// <param name="resource">Enumeration of resource instances in this page of results</param>
        /// </summary>
        public PagedEntities(IPageParameters pageParameters, int pages, int count, IEnumerable<ENTITY> resource) {
            PageParameters = pageParameters;
            Pages = pages;
            Count = count;
            Resource = resource;
        }
    }
}