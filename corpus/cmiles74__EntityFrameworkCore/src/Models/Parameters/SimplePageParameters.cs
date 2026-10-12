using System.Collections.Generic;

namespace Nervestaple.EntityFrameworkCore.Models.Parameters {

    /// <summary>
    /// Provides a simple page parameters implementation that allows for one
    /// sort parameter to apply to the results.
    /// </summary>
    public class SimplePageParameters : IPageParameters {

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
        /// the fields by which to sort
        /// </summary>
        /// <returns>the sort field</returns>
        public string Sort { get; set; }

        /// <summary>
        /// flag indicating if the instances should be sorted in 
        /// descending order
        /// </summary>
        /// <returns>flag indicating descending sort</returns>
        public bool Desc { get; set; }

        /// <summary>
        /// Creates a new instance.
        /// </summary>
        public SimplePageParameters() {
            Size = 100;
            Page = 0;
            Sort = "id";
            Desc = false;
        }

        /// <inheritdoc/>
        public IEnumerable<SortParameter> GetSort()
        {
            return new List<SortParameter> { new SortParameter(Sort, Desc) };
        }
    }
}