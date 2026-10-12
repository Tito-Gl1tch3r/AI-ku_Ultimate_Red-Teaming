namespace Nervestaple.EntityFrameworkCore.Models.Parameters {
    
    /// <summary>
    /// A set of parameters that defines the sort order for a set of
    /// resource instances.
    /// </summary>
    public class SortParameter {

        /// <summary>
        /// the field by which to sort
        /// </summary>
        /// <returns>sort field</returns>
        public string Field { get; set; }

        /// <summary>
        /// flag indicating if the instances should be sorted in 
        /// descending order
        /// </summary>
        /// <returns>flag indicating descending sort</returns>
        public bool Desc { get; set; } = false;

        /// <summary>
        /// Creates a new instance.
        /// </summary>
        public SortParameter() : this("id", false) {
            
        }

        /// <summary>
        /// Creates a new instance.
        /// <param name="field">Field on which to sort</param>
        /// </summary>
        public SortParameter(string field) : this(field, false) {
            
        }

        /// <summary>
        /// Creates a new instance.
        /// <param name="field">Field on which to sort</param>
        /// <param name="desc">Flag indicating if the sort should be descending</param>
        /// </summary>
        public SortParameter(string field, bool desc) {
            Field = field;
            Desc = desc;
        }
    }
}