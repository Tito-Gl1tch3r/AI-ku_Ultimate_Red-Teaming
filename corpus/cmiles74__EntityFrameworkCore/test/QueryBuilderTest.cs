
using System;
using System.Linq;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using Test.Models;
using Nervestaple.EntityFrameworkCore.Repositories;

namespace Test
{
    /// <summary>
    /// Provides a test suite for the query builder
    /// </summary>
    [TestClass]
    public class QueryBuilderTest {
        
        // nam of our in-memory test database
        private static string _databaseName = Guid.NewGuid().ToString();
        
        // service provider to provide logging
        private static ServiceProvider _serviceProvider =
            new ServiceCollection().AddLogging(b => {
                b.AddConsole();
                b.SetMinimumLevel(LogLevel.Debug);
            }).BuildServiceProvider();

        // database context for testing
        private static DbContextOptions<TestDbContext> _dbContextOptions = new DbContextOptionsBuilder<TestDbContext>()
            .UseInMemoryDatabase(_databaseName)
            .UseLoggerFactory(_serviceProvider.GetService<ILoggerFactory>()).Options;
        
        // our parent person
        private static Person parent = null;
        
        // our child person
        private static Person child = null;

        /// <summary>
        /// Prepares the database for the tests
        /// </summary>
        /// <param name="testContext">test context</param>
        [ClassInitialize]
        public static void Setup(TestContext testContext) {
            using (var context = new TestDbContext(_dbContextOptions)) {
                    
                parent = new Person {
                    FirstName =  "Joanna",
                    LastName = "Miles",
                    CreatedAt =  DateTime.Now,
                    IsAnarchist = null
                };
                context.Add(parent);
                context.SaveChanges();

                child = new Person {
                    FirstName = "Emily",
                    LastName = "Miles",
                    CreatedAt = DateTime.Now,
                    IsAnarchist =  true,
                    ParentPerson = parent.Id
                };
                context.Add(child);
                context.SaveChanges();
            }
        }

        /// <summary>
        /// Queries with a criteria parameter that contains a Guid?
        /// </summary>
        [TestMethod]
        public void EqualsWithGuid() {
            using (var context = new TestDbContext(_dbContextOptions)) {
                var criteria = new PersonCriteria() {
                    ParentPerson = parent.Id
                };
                var entities = QueryBuilder<Person, Guid>.GetResults(context.People, criteria);
                Assert.IsTrue(entities.Count() == 1, 
                    "Emily has one parent, found " + entities.Count());
            }
        }
        
        /// <summary>
        /// Queries with a criteria parameter that contains a empty Guid, we
        /// can't really query with a null Guid
        /// </summary>
        [TestMethod]
        public void EqualsWithEmptyGuid() {
            using (var context = new TestDbContext(_dbContextOptions)) {
                var criteria = new PersonCriteria() {
                    ParentPerson = Guid.Empty
                };
                var entities = QueryBuilder<Person, Guid>.GetResults(context.People, criteria);
                Assert.IsTrue(entities.Count() == 1, 
                    "Only one person has no parent; found " + entities.Count());
            }
        }
        
        /// <summary>
        /// Queries with a criteria parameter that is a string
        /// </summary>
        [TestMethod]
        public void EqualsWithString() {
            using (var context = new TestDbContext(_dbContextOptions)) {
                var criteria = new PersonCriteria() {
                    LastName = "Miles"
                };
                var entities = QueryBuilder<Person, Guid>.GetResults(context.People, criteria);
                Assert.IsTrue(entities.Count() == 2, 
                    "There should be two people have the last name \"Miles\", found " + entities.Count());
            }
        }
        
        /// <summary>
        /// Queries with a criteria parameter that is a null string
        /// </summary>
        [TestMethod]
        public void EqualsWithNullString() {
            using (var context = new TestDbContext(_dbContextOptions)) {
                var criteria = new PersonCriteria() {
                    LastName = null
                };
                var entities = QueryBuilder<Person, Guid>.GetResults(context.People, criteria);
                Assert.IsTrue(entities.Count() == 2, 
                    "There should be zero people with a null last name, found " + entities.Count());
            }
        }
        
        /// <summary>
        /// Queries with a criteria parameter that is a nullable boolean
        /// </summary>
        [TestMethod]
        public void EqualsWithNullableBoolean() {
            using (var context = new TestDbContext(_dbContextOptions)) {
                var criteria = new PersonCriteria() {
                    IsAnarchist = true
                };
                var entities = QueryBuilder<Person, Guid>.GetResults(context.People, criteria);
                Assert.IsTrue(entities.Count() == 1, 
                    "There should be only one anarchist, found " + entities.Count());
            }
        }
    }
}
