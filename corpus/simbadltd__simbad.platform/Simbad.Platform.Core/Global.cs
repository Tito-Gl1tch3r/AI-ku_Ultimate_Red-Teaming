using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.ComponentModel;
using Simbad.Platform.Core.Dependencies;
using Simbad.Platform.Core.Events;
using Simbad.Platform.Core.Substance.IdGeneration;

namespace Simbad.Platform.Core
{
    public static class Global
    {
        public const string AssemblyWildcardsPropertyName = "Simbad.Platform.Core.AssemblyWildcardsPropertyName"; 
        
        private static readonly Dictionary<string, object> _parameters = new Dictionary<string, object>();
        
        public static readonly Ioc Ioc = new Ioc();

        public static T Parameter<T>(string name)
        {
            if (_parameters.ContainsKey(name) == false)
            {
                throw new ArgumentException(
                    $"Cannot found parameter with name <{name}>. Please, ensure that this parameter is initialized before this call.");
            }

            return (T) _parameters[name];
        }

        /// <summary>
        /// Entry point to configure and start using framework
        /// </summary>
        /// <param name="projectAssemblyNameWildcards">List of project assembly names (wildcard supported too, e.g. "Simbad.Platform.*.dll"). It is needed to
        /// connect external logic (like event handlers etc.) with framework mechanisms (like dispatchers etc.)</param>
        /// <returns></returns>
        public static Configuration Configure(params string[] projectAssemblyNameWildcards)
        {
            var configuration = new Configuration();
            configuration.SetParameter(AssemblyWildcardsPropertyName, projectAssemblyNameWildcards);
            
            RegisterCoreServices();

            return configuration;
        }
        
        private static void RegisterCoreServices()
        {
            Ioc.RegisterSingle(TypeRegistration.For<SimpleSynchronousEventDispatcher, IEventDispatcher>(Lifetime.PerLifetimeScope));
            Ioc.RegisterAllTypesDerivedFrom(
                typeof(IEventHandler<>),
                implementationType => TypeRegistration.AsImplementedInterfaces(implementationType, Lifetime.PerLifetimeScope));
        }        

        public sealed class Configuration
        {
            public void SetParameter(string name, object value)
            {
                _parameters[name] = value;
            }

            public Configuration RegisterIdGenertor(Func<Guid> idGenerator)
            {
                IdGenerator.RegisterIdGenertor(idGenerator);

                return this;
            }
        }
    }
}