using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using Simbad.Platform.Core.Dependencies;
using Xunit;

namespace Simbad.Platform.Core.Tests
{
    public class SimpleParameterlessCtorServiceResolverTests
    {
        private readonly SimpleParameterlessCtorServiceResolver _target;

        public SimpleParameterlessCtorServiceResolverTests()
        {
            _target = new SimpleParameterlessCtorServiceResolver();

            Global.Ioc.Reset();
        }

        [Fact]
        public void Should_CreateInstance_When_TypesRegisteredProperly()
        {
            Global.Ioc.Register(TypeRegistration.For<TestService, ITestService>());

            var service = _target.Resolve<ITestService>();

            Assert.NotNull(service);
            Assert.Equal(typeof(TestService), service.GetType());
        }
        
        [Fact]
        public void Should_CreateMultipleInstances_When_TypesRegisteredProperly()
        {
            Global.Ioc.Register(TypeRegistration.For<TestService, ITestService>());
            Global.Ioc.Register(TypeRegistration.For<TestService2, ITestService>());

            var services = _target.ResolveMany<ITestService>().ToList();

            Assert.NotEmpty(services);
            Assert.Equal(2, services.Count);
            
            Assert.Contains(services, x => x.GetType() == typeof(TestService));
            Assert.Contains(services, x => x.GetType() == typeof(TestService2));
        }     
        
        [Fact]
        public void Should_CreateMultipleInstances_When_ResolvingThrough_GenericEnumerable()
        {
            Global.Ioc.Register(TypeRegistration.For<TestService, ITestService>());
            Global.Ioc.Register(TypeRegistration.For<TestService2, ITestService>());

            var services = (_target.Resolve(typeof(IEnumerable<ITestService>)) as IEnumerable).OfType<ITestService>().ToList();

            Assert.NotEmpty(services);
            Assert.Equal(2, services.Count);
            
            Assert.Contains(services, x => x.GetType() == typeof(TestService));
            Assert.Contains(services, x => x.GetType() == typeof(TestService2));
        }

        [Fact]
        public void Should_CreateSingletonInstance_When_SingletonLifetime_Configured()
        {
            Global.Ioc.Register(TypeRegistration.For<TestService, ITestService>(Lifetime.Singleton));
            
            var service1 = _target.Resolve<ITestService>();
            var service2 = _target.Resolve<ITestService>();

            Assert.NotNull(service1);
            Assert.NotNull(service2);
            Assert.Same(service1, service2);            
        }

        [Fact]
        public void ShouldThrow_When_RegistrationMissed()
        {
            var ex = Assert.Throws<InvalidOperationException>(() => _target.Resolve<ITestService>());

            Assert.Contains("missed registration of implementation for this type", ex.Message);
        }

        [Fact]
        public void ShouldThrow_When_MoreThanOne_RegistrationFound()
        {
            Global.Ioc.Register(TypeRegistration.For<TestService, ITestService>());
            Global.Ioc.Register(TypeRegistration.For<TestService2, ITestService>());
            
            var ex = Assert.Throws<InvalidOperationException>(() => _target.Resolve<ITestService>());

            Assert.Contains("more than one registration for this type found", ex.Message);            
        }

        [Fact]
        public void ShouldThrow_When_ImplementationType_IsNotAClass()
        {
            Global.Ioc.Register(TypeRegistration.For<int, object>());

            var ex = Assert.Throws<InvalidOperationException>(() => _target.Resolve<object>());
            
            Assert.Contains("type is not a class", ex.Message);
        }
        
        [Fact]
        public void ShouldThrow_When_ImplementationType_IsAnAbstractClass()
        {
            Global.Ioc.Register(TypeRegistration.For<AbstractTestService, ITestService>());
            
            var ex = Assert.Throws<InvalidOperationException>(() => _target.Resolve<ITestService>());
            
            Assert.Contains("type is an abstract class", ex.Message);
        }        
        
        [Fact]
        public void ShouldThrow_When_ImplementationType_HasNoParameterlessCtor()
        {
            Global.Ioc.Register(TypeRegistration.For<ServiceWithoutParameterlessCtor, ITestService>());
            
            var ex = Assert.Throws<InvalidOperationException>(() => _target.Resolve<ITestService>());
            
            Assert.Contains("type has no parameterless ctor", ex.Message);
        }

        private interface ITestService
        {
        }

        private class TestService : ITestService
        {
        }

        private class TestService2 : ITestService
        {
        }

        private abstract class AbstractTestService : ITestService
        {
        }
        
        private class ServiceWithoutParameterlessCtor : ITestService
        {
            private readonly int _field;
            
            public ServiceWithoutParameterlessCtor(int field)
            {
                _field = field;
            }
        }
    }
}