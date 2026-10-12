using System.Collections.Generic;
using Newtonsoft.Json;

namespace Nervestaple.EntityFrameworkCore.Models.Parameters {
    
    /// <summary>
    /// A set of parameters used to specify which page of resources will be 
    /// returned, it's size and how the resource instances should be sorted.
    /// </summary>
    public class PageParameters : IPageParameters {

        /// <summary>
        /// the requested page size
        /// </summary>
        /// <returns>the page size</returns>
        public int Size { get; set; }

        /// <summary>
        /// the requested page of data
        /// </summary>
        /// <returns>the page number</returns>
        public int Page { get; set; }

        /// <summary>
        /// a list of sort parameters
        /// </summary>
        /// <returns>list of sort parameters</returns>
        public IList<SortParameter> Sort { get; set; }

        /// <summary>
        /// Creates a new instance.
        /// </summary>
        [JsonConstructor]
        public PageParameters() {
            Size = 100;
            Page = 0;
        }

        /// <summary>
        /// Creates a new instance.
        /// <param name="size">Size of the page (defaults to 100)</param>
        /// <param name="page">Page of results to return (defaults to 0)</param>
        /// </summary>
        public PageParameters(int size = 100, int page = 0) : 
            this(new List<SortParameter>() { new SortParameter("id") }, size, page) {

        }

        /// <summary>
        /// Creates a new instance.
        /// <param name="sort">List of sorts for the result set</param>
        /// <param name="size">Size of the page (defaults to 100)</param>
        /// <param name="page">Page of results to return (defaults to 0)</param>
        /// </summary>
        public PageParameters(List<SortParameter> sort, int size = 100, int page = 0) {
            Sort = sort;
            Size = size;
            Page = page;
        }

        /// <summary>
        /// Returns the list of sorts.
        /// </summary>
        public IEnumerable<SortParameter> GetSort()
        {
            return Sort != null ? Sort : new List<SortParameter>() { new SortParameter("id") };
        }
    }
}