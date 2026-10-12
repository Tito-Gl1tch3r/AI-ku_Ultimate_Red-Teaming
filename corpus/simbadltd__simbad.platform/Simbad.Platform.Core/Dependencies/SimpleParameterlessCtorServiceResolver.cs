using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using Simbad.Platform.Core.Utils;

namespace Simbad.Platform.Core.Dependencies
{
    internal sealed class SimpleParameterlessCtorServiceResolver : IServiceResolver
    {
        private readonly ConcurrentBag<Type> _safeTypes = new ConcurrentBag<Type>();
        
        private readonly ConcurrentDictionary<Type, object> _singletones = new ConcurrentDictionary<Type, object>();

        private readonly Lazy<IDictionary<Type, List<TypeRegistration>>> _typeRegistrations =
            new Lazy<IDictionary<Type, List<TypeRegistration>>>(
                () => Global.Ioc.Registrations.GroupBy(x => x.RegistrationType).ToDictionary(x => x.Key, x => x.ToList()));

        private void EnsureTypeIsSafe(Type type)
        {
            if (_safeTypes.Contains(type))
            {
                return;
            }

            if (type.IsClass == false)
            {
                throw new InvalidOperationException(
                    $"Cannot create instance of type <{type}>, type is not a class.");
            }

            if (type.IsAbstract)
            {
                throw new InvalidOperationException(
                    $"Cannot create instance of type <{type}>, type is an abstract class.");
            }

            if (type.HasParameterlessCtor() == false)
            {
                throw new InvalidOperationException(
                    $"Cannot create instance of type <{type}>, type has no parameterless ctor.");
            }

            _safeTypes.Add(type);
        }

        public T Resolve<T>() where T : class
        {
            return Resolve(typeof(T)) as T;
        }

        public object Resolve(Type abstractionType)
        {
            if (abstractionType.IsGenericEnumerable())
            {
                return ResolveMany(abstractionType.GetCollectionItemType());
            }
            
            if (_typeRegistrations.Value.ContainsKey(abstractionType) == false)
            {
                throw new InvalidOperationException($"Cannot create instance of type <{abstractionType}>, missed registration of implementation for this type.");
            }

            var typeRegistrations = _typeRegistrations.Value[abstractionType];
            if (typeRegistrations.Count > 1)
            {
                throw new InvalidOperationException($"Cannot create instance of type <{abstractionType}>, more than one registration for this type found.");
            }

            var typeRegistration = typeRegistrations.Single();
            var result = CreateInstanceFor(typeRegistration);
            return result;
        }

        public IEnumerable<T> ResolveMany<T>()
        {
            return ResolveMany(typeof(T)).OfType<T>().ToList();
        }
        
        public IEnumerable ResolveMany(Type abstractionType)
        {
            var result = new ArrayList();
            
            if (_typeRegistrations.Value.ContainsKey(abstractionType) == false)
            {
                return result;
            }

            var typeRegistrations = _typeRegistrations.Value[abstractionType];

            foreach (var typeRegistration in typeRegistrations)
            {
                result.Add(CreateInstanceFor(typeRegistration));
            }

            return result;
        }

        private object CreateInstanceFor(TypeRegistration typeRegistration)
        {
            EnsureTypeIsSafe(typeRegistration.ImplementationType);

            object Factory(TypeRegistration x) => Activator.CreateInstance(x.ImplementationType);

            var result = typeRegistration.Lifetime == Lifetime.Singleton
                ? _singletones.GetOrAdd(typeRegistration.RegistrationType, x => Factory(typeRegistration))
                : Factory(typeRegistration);
            
            return result;
        }
    }
}