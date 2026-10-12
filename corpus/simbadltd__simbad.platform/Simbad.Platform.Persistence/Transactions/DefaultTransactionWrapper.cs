using System;
using System.Collections.Generic;
using System.Data;
using Simbad.Platform.Persistence.Storage;

namespace Simbad.Platform.Persistence.Transactions
{
    public sealed class DefaultTransactionWrapper : ITransactionWrapper
    {
        private readonly IDbTransaction _transaction;

        private readonly IDbConnection _connection;

        private readonly IStorageAdapter _storageAdapter;

        public DefaultTransactionWrapper(IDbConnection connection, IDbTransaction transaction, IStorageAdapter storageAdapter)
        {
            _connection = connection;
            _transaction = transaction;
            _storageAdapter = storageAdapter;
        }

        public T Fetch<T>(Guid id) where T : Dao
        {
            return _storageAdapter.Fetch<T>(id, _connection, _transaction);
        }

        public Dao Fetch(Guid id, Type type)
        {
            return _storageAdapter.Fetch(id, type, _connection, _transaction);
        }

        public ICollection<T> Fetch<T>(Func<T, bool> predicate) where T : Dao
        {
            return _storageAdapter.Fetch(predicate, _connection, _transaction);
        }

        public ICollection<T> FetchAll<T>(IDbConnection connection, IDbTransaction transaction) where T : Dao
        {
            return _storageAdapter.FetchAll<T>(_connection, _transaction);
        }

        public ICollection<Dao> FetchAll(Type type)
        {
            return _storageAdapter.FetchAll(type, _connection, _transaction);
        }

        public void Save(Dao dao, Type type)
        {
            _storageAdapter.Save(dao, type, _connection, _transaction);
        }

        public void Delete<T>(Guid id) where T : Dao
        {
            Delete(id, typeof(T));
        }

        public void Delete(Guid id, Type type)
        {
            _storageAdapter.Delete(id, type, _connection, _transaction);
        }

        public void DeleteAll(Type type)
        {
            _storageAdapter.DeleteAll(type, _connection, _transaction);
        }
    }
}
