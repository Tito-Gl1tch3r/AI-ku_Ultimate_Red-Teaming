using Simbad.Platform.Core;
using Simbad.Platform.Core.Dependencies;
using Simbad.Platform.Persistence.Storage;

namespace Simbad.Platform.Persistence
{
    public sealed class PersistenceConfiguration
    {
        public PersistenceConfiguration(Global.Configuration globalConfiguration)
        {
            GlobalConfiguration = globalConfiguration;
        }

        public Global.Configuration GlobalConfiguration { get; private set; }
        
        /// <summary>
        /// Enables very simple persistence based on the in-memory storage. It is good option for prototyping, MVPs. But it should not be used in any production
        /// ready functionality. Transactions are NOT supported in this storage.
        /// </summary>
        public PersistenceConfiguration UseInMemoryStorage()
        {
            Global.Ioc.RegisterSingle(TypeRegistration.For<InMemoryStorageAdapter, IStorageAdapter>(Lifetime.PerLifetimeScope));

            return this;
        }        
    }
}