namespace Nervestaple.EntityFrameworkCore.Models.Parameters {

    /// <summary>
    /// Provides an object that represents a decimal range.
    /// </summary>
    public class DecimalRangeParameter {

        /// <summary>
        /// the begining of the range
        /// </summary>
        public decimal? Start { get; set; }

        /// <summary>
        /// the end of the range
        /// </summary>
        public decimal? End { get; set; }

        /// <summary>
        /// Creates a new instance.
        /// <param name="start">Starting value for the range</param>
        /// <param name="end">Ending value for the range</param>
        /// </summary>
        public DecimalRangeParameter(decimal? start, decimal? end) {
            Start = start;
            End = end;
        }

        /// <summary>
        /// Creates a new instance represents a null or empty decimal field
        /// </summary>
        /// <returns>new instance representing a null field</returns>
        public static DecimalRangeParameter Null() {
            return new DecimalRangeParameter(null, null);
        }
    }
}