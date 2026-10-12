using Simbad.Platform.Core;
using Simbad.Platform.Core.Substance.Registration;
using Simbad.Platform.Core.Tests;
using Simbad.Platform.Persistence.Converting;
using Simbad.Platform.Persistence.Transactions;
using Xunit;

namespace Simbad.Platform.Persistence.Tests
{
    public class InMemoryStorageAdapterTests
    {
        private readonly Repository<TestBusinessObject> _repository;
        private readonly IUnitOfWork _unitOfWork;

        public InMemoryStorageAdapterTests()
        {
            Global.Configure().EnablePersistence(x => x.UseInMemoryStorage());

            Mapping.Configure().Add<TestBusinessObject, TestDao>();

            _unitOfWork = new UnitOfWork();
            _repository = new Repository<TestBusinessObject>(_unitOfWork);
        }

        [Fact]
        public void Should_Save()
        {
            // Arrange
            var entity = new TestBusinessObject();

            // Act
            _repository.Save(entity);
            _unitOfWork.Commit();
        }

        [Fact]
        public void Should_Get_ById()
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
        
        [Fact]
        public void Should_Get_ByPredicate()
        {
            // Arrange
            const string TestString = "TEST_Unique";
            var entity = new TestBusinessObject
            {
                TestProperty = TestString
            };

            _repository.Save(entity);
            _unitOfWork.Commit();

            // Act
            var entityFromStorage = _repository.FindSingle(x => x.TestProperty == TestString);

            // Assert
            Assert.Equal(entity.Id, entityFromStorage.Id);
            Assert.Equal(entity.TestProperty, TestString);
        }
        
        [Fact]
        public void Should_Delete_ById()
        {
            // Arrange
            const string TestString = "TEST";
            var entity = new TestBusinessObject
            {
                TestProperty = TestString
            };

            _repository.Save(entity);
            _unitOfWork.Commit();
            
            _repository.Delete(entity.Id);
            _unitOfWork.Commit();

            // Act
            var entityFromStorage = _repository.Get(entity.Id);

            // Assert
            Assert.Null(entityFromStorage);
        }        
        
        [Fact]
        public void Should_DeleteAll()
        {
            // Arrange
            const string TestString = "TEST";
            var entity = new TestBusinessObject
            {
                TestProperty = TestString
            };

            _repository.Save(entity);
            _unitOfWork.Commit();
            
            _repository.DeleteAll();
            _unitOfWork.Commit();

            // Act
            var entitiesFromStorage = _repository.GetAll();

            // Assert
            Assert.Empty(entitiesFromStorage);
        }          
    }
}