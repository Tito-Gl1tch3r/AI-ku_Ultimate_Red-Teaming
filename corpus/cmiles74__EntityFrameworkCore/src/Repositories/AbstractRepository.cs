using System;
using Microsoft.EntityFrameworkCore;

namespace Nervestaple.EntityFrameworkCore.Repositories {

    /// <summary>
    /// Provides an abstract repository that all other repositories may extend.
    /// </summary>
    public abstract class AbstractRepository : IDisposable {

        /// <summary>
        /// Database context
        /// </summary>
        protected readonly DbContext Context;

        /// <summary>
        /// Returns true if this repository has been disposed.
        /// <returns>
        /// true if this repository has been disposed
        /// </returns>
        /// </summary>
        #region IDisposable Support
        private bool _disposedValue = false; // To detect redundant calls

        /// <summary>
        /// Context for this repository.
        /// </summary>
        public AbstractRepository(DbContext context) {
            Context = context;
        }

        /// <summary>
        /// Disposes the repository
        /// </summary>
        /// <param name="disposing">flag indicating we should be disposed</param>
        protected virtual void Dispose(bool disposing) {
            if (!_disposedValue)
            {
                if (disposing)
                {
                    Context.Dispose();
                }

                _disposedValue = true;
            }
        }

        /// <inheritdoc/>
        void IDisposable.Dispose()
        {
            Dispose(true);
        }
        #endregion
    }
}