using System;
using Nervestaple.EntityFrameworkCore.Models.Criteria;
using Nervestaple.EntityFrameworkCore.Models.Parameters;

namespace Test.Models {
    
    public class PersonCriteria : SearchCriteria<Person, Guid> { 
        
        public string FirstName { get; set; }
        
        public string LastName { get; set; }
        
        public DateRangeParameter CreatedAt { get; set; }
        
        public bool? IsAnarchist { get; set; } 
        
        public Guid? ParentPerson { get; set; }
    }
}