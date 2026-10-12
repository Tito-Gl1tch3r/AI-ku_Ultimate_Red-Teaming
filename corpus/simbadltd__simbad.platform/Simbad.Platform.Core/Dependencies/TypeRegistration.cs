using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Simbad.Platform.Core.Utils;

namespace Simbad.Platform.Core.Dependencies
{
    public sealed class TypeRegistration
    {
        public TypeRegistration(Type implementationType, Type registrationType, Lifetime lifetime)
        {
            if (implementationType.IsDerivedFrom(registrationType) == false)
            {
                throw new ArgumentException($"Type {implementationType} should be derived from {registrationType}.");
            }

            RegistrationType = registrationType;
            ImplementationType = implementationType;
            Lifetime = lifetime;
        }

        public Type RegistrationType { get; private set; }

        public Type ImplementationType { get; private set; }

        public bool IsOpenGenericRegistration { get; private set; }

        public Lifetime Lifetime { get; private set; }

        public static TypeRegistration OpenGeneric(Type implementation, Type registration, Lifetime lifetime = Lifetime.Transient)
        {
            return new TypeRegistration(implementation, registration, lifetime)
            {
                IsOpenGenericRegistration = true,
            };
        }

        public static TypeRegistration For<TImplementation, TRegistration>(Lifetime lifetime = Lifetime.Transient) where TImplementation : TRegistration
        {
            return new TypeRegistration(typeof(TImplementation), typeof(TRegistration), lifetime);
        }

        public static ICollection<TypeRegistration> As<T>(ICollection<Type> implementationTypes, Lifetime lifetime)
        {
            var registrationType = typeof(T);
            var result = new List<TypeRegistration>();
            foreach (var implementationType in implementationTypes)
            {
                result.Add(new TypeRegistration(implementationType, registrationType, lifetime));
            }

            return result;
        }

        public static ICollection<TypeRegistration> AsImplementedInterfaces(ICollection<Type> types, Lifetime lifetime)
        {
            var result = new List<TypeRegistration>();
            foreach (var type in types)
            {
                var implementedInterfaces = AsImplementedInterfaces(type, lifetime);
                result.AddRange(implementedInterfaces);
            }

            return result;
        }

        public static ICollection<TypeRegistration> AsImplementedInterfaces(Type type, Lifetime lifetime)
        {
            var implementedInterfaces = GetImplementedInterfaces(type);
            return implementedInterfaces.Select(x => new TypeRegistration(type, x, lifetime)).ToList();
        }

        public static ICollection<TypeRegistration> AsSelf(ICollection<Type> types, Lifetime lifetime)
        {
            var result = new List<TypeRegistration>();
            foreach (var type in types)
            {
                result.Add(AsSelf(type, lifetime));
            }

            return result;
        }

        public static TypeRegistration AsSelf<T>(Lifetime lifetime = Lifetime.Transient)
        {
            var type = typeof(T);
            return AsSelf(type, lifetime);
        }

        public static TypeRegistration AsSelf(Type type, Lifetime lifetime)
        {
            return new TypeRegistration(type, type, lifetime);
        }

        private static List<Type> GetImplementedInterfaces(Type type)
        {
            var types = type.GetTypeInfo().ImplementedInterfaces.Where(i => i != typeof(IDisposable)).ToList();
            if (type.GetTypeInfo().IsInterface)
            {
                types.Add(type);
            }

            return types;
        }
    }
}