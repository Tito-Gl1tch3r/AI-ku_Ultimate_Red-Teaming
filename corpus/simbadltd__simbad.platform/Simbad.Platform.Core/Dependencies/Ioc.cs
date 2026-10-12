using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Simbad.Platform.Core.Utils;

namespace Simbad.Platform.Core.Dependencies
{
    public sealed class Ioc
    {
        private static readonly Lazy<Assembly[]> _assembliesToScan = new Lazy<Assembly[]>(
            () => GetAssemblies(
                      Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location),
                      Global.Parameter<string[]>(Global.AssemblyWildcardsPropertyName)) ?? new[] { Assembly.GetExecutingAssembly() });
        
        private static readonly object _syncRoot = new object();
        
        private static IServiceResolver _serviceResolver = new SimpleParameterlessCtorServiceResolver();

        private static readonly List<TypeRegistration> _registrations = new List<TypeRegistration>();

        public IServiceResolver Resolver => _serviceResolver;

        public List<TypeRegistration> Registrations
        {
            get
            {
                lock (_syncRoot)
                {
                    return new List<TypeRegistration>(_registrations);
                }
            }
        }

        public void Register(TypeRegistration typeRegistration)
        {
            lock (_syncRoot)
            {
                _registrations.Add(typeRegistration);
            }
        }
        
        public void RegisterSingle(TypeRegistration typeRegistration)
        {
            lock (_syncRoot)
            {
                var newRegistrations = _registrations.Where(x => x.RegistrationType != typeRegistration.RegistrationType).ToList();
                newRegistrations.Add(typeRegistration);

                _registrations.Clear();
                _registrations.AddRange(newRegistrations);
            }
        }

        public void RegisterAllTypesDerivedFrom(Type registrationType, Func<Type, ICollection<TypeRegistration>> registrationFunc)
        {
            var typeInfo = registrationType.GetTypeInfo();
            var implementationTypes = AllTypes(x => x.GetTypeInfo().IsDerivedFrom(typeInfo)).ToList();

            foreach (var implementationType in implementationTypes)
            {
                var typeRegistrations = registrationFunc(implementationType);
                foreach (var typeRegistration in typeRegistrations)
                {
                    Register(typeRegistration);
                }
            }
         }
        
        private static ICollection<Type> AllTypes(Func<Type, bool> predicate)
        {
            return _assembliesToScan.Value.SelectMany(GetLoadableTypes).Where(predicate).ToList();
        }        
        
        private static Assembly[] GetAssemblies(string path, params string[] assembliesWildCards)
        {
            return Directory.GetFiles(path).Where(f => assembliesWildCards.Any(x => StringUtils.MatchWildcard(x, Path.GetFileName(f)))).Select(Assembly.LoadFrom).ToArray();
        }        
        
        private static IEnumerable<Type> GetLoadableTypes(Assembly assembly)
        {
            if (assembly == null)
            {
                throw new ArgumentNullException(nameof(assembly));
            }

            try
            {
                return assembly.DefinedTypes.Select(t => t.AsType()).Where(t => t.IsClass && t.IsAbstract == false);
            }
            catch (ReflectionTypeLoadException ex)
            {
                return ex.Types.Where(t => t != null);
            }
        }        

        public void Reset()
        {
            lock (_syncRoot)
            {
                _registrations.Clear();
            }
        }
        
        public void UseResolver(IServiceResolver serviceResolver)
        {
            _serviceResolver = serviceResolver;
        }
    }
}