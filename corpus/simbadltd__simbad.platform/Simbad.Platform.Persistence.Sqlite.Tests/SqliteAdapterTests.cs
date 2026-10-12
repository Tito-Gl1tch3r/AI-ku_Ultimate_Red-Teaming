using System;
using Simbad.Platform.Core;
using Simbad.Platform.Core.Substance.Registration;
using Simbad.Platform.Core.Tests;
using Simbad.Platform.Persistence.Converting;
using Simbad.Platform.Persistence.Tests;
using Simbad.Platform.Persistence.Transactions;
using Xunit;

namespace Simbad.Platform.Persistence.Sqlite.Tests
{
    public class SqliteAdapterTests
    {
        private readonly Repository<TestBusinessObject> _repository;
        private readonly IUnitOfWork _unitOfWork;

        public SqliteAdapterTests()
        {
            Global.Configure()
                .EnablePersistence(x => x.UseSqlite(".\\test.s3db"));

            Mapping.Configure().Add<TestBusinessObject, TestDao>();

            _unitOfWork = new UnitOfWork();
            _repository = new Repository<TestBusinessObject>(_unitOfWork);
        }

        [Fact]
        public void ShouldSave()
        {
            // Arrange
            var entity = new TestBusinessObject();

            // Act
            _repository.Save(entity);
            _unitOfWork.Commit();
        }

        [Fact]
        public void ShouldLoad()
        {
            // Arrange
            const string TestString = "TEST";
            var entity = new TestBusinessObject
            {
                TestProperty = TestString
            };

            _repository.Save(entity);
            _unitOfWork.Commit();

            // Act
            var entityFromStorage = _repository.Get(entity.Id);

            // Assert
            Assert.Equal(entity.Id, entityFromStorage.Id);
            Assert.Equal(entity.TestProperty, TestString);
        }
    }
}