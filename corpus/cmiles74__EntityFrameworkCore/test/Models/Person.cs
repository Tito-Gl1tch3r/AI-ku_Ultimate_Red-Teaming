using System;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;
using Nervestaple.EntityFrameworkCore.Models.Entities;

namespace Test.Models {
    
    [Table("People")]
    public class Person : Entity<Guid> {
    
        [DatabaseGenerated(DatabaseGeneratedOption.Identity)]
        [Key, Column("prepop_dataset_id")]
        public override Guid? Id { get; set; }

        [Column("parent")]
        public Guid? ParentPerson { get; set; }
        
        public string FirstName { get; set; }
        
        public string LastName { get; set; }
        
        [Column("created_date")]
        public DateTime CreatedAt { get; set; }
        
        [Column("anarchist")]
        public bool? IsAnarchist { get; set; } 
    }
}