using System;

namespace Nervestaple.EntityFrameworkCore.Models.Parameters {

    /// <summary>
    /// Provides an object that represents a date range.
    /// </summary>
    public class DateRangeParameter {

        /// <summary>
        /// the begining of the date range
        /// </summary>
        public DateTime? Start { get; set; }

        /// <summary>
        /// the end of the date range
        /// </summary>
        public DateTime? End { get; set; }

        /// <summary>
        /// Creates a new instance.
        /// <param name="start">Starting date and time of the range</param>
        /// <param name="end">Ending date and time of the range</param>
        /// </summary>
        public DateRangeParameter(DateTime? start, DateTime? end) {
            Start = start;
            End = end;
        }

        /// <summary>
        /// Creates a new instance that represents an empty or null date.
        /// </summary>
        /// <returns>new instance representing a null field</returns>
        public static DateRangeParameter Null() {
            return new DateRangeParameter(null, null);
        }
    }
}