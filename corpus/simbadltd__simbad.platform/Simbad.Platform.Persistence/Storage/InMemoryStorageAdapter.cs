using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Data;
using System.Linq;
using Simbad.Platform.Persistence.Transactions;
using Simbad.Platform.Persistence.Utils;

namespace Simbad.Platform.Persistence.Storage
{
    internal sealed class InMemoryStorageAdapter : IStorageAdapter
    {
        private static readonly ConcurrentDictionary<string, object> _locks = new ConcurrentDictionary<string, object>();

        private static readonly Dictionary<string, Dictionary<Guid, string>> _database = new Dictionary<string, Dictionary<Guid, string>>();
        
        public T Fetch<T>(Guid id, IDbConnection connection, IDbTransaction transaction) where T : Dao
        {
            return Fetch(id, typeof(T), connection, transaction) as T;
        }

        public Dao Fetch(Guid id, Type type, IDbConnection connection, IDbTransaction transaction)
        {
            var tableName = GetTableName(type);
            CreateTableIfNotExists(tableName);

            lock (AcquireLock(tableName))
            {
                return _database[tableName].ContainsKey(id) == false ? null : Json.Deserialize(_database[tableName][id], type) as Dao;
            }
        }

        public ICollection<T> Fetch<T>(Func<T, bool> predicate, IDbConnection connection, IDbTransaction transaction) where T : Dao
        {
            var result = FetchAll<T>(connection, transaction).Where(predicate).ToList();
            return result;
        }

        public ICollection<T> FetchAll<T>(IDbConnection connection, IDbTransaction transaction) where T : Dao
        {
            return FetchAll(typeof(T), connection, transaction).OfType<T>().ToList();
        }

        public ICollection<Dao> FetchAll(Type type, IDbConnection connection, IDbTransaction transaction)
        {
            var tableName = GetTableName(type);
            CreateTableIfNotExists(tableName);

            lock (AcquireLock(tableName))
            {
                return _database[tableName].Values.Select(x => Json.Deserialize(x, type) as Dao).ToList();
            }
        }

        public void Transaction(Action<ITransactionWrapper> action)
        {
            // todo:[kk] Transactions is too complex for in-memory storage, that's why we've just skip it for this type of storage
            var transactionWrapper = new DefaultTransactionWrapper(null, null, this);
            action(transactionWrapper);
        }

        public TResult Transaction<TResult>(Func<ITransactionWrapper, TResult> action)
        {
            // todo:[kk] Transactions is too complex for in-memory storage, that's why we've just skip it for this type of storage
            var transactionWrapper = new DefaultTransactionWrapper(null, null, this);
            return action(transactionWrapper);
        }

        public void Save<T>(T model, IDbConnection connection, IDbTransaction transaction) where T : Dao
        {
            Save(model, typeof(T), connection, transaction);
        }

        public void Save(Dao model, Type type, IDbConnection connection, IDbTransaction transaction)
        {
            // todo [kk]: check that type is derived from Dao

            var tableName = GetTableName(type);
            CreateTableIfNotExists(tableName);

            lock (AcquireLock(tableName))
            {
                var data = Json.Serialize(model);
                _database[tableName][model.Id] = data;
            }
        }

        public void Delete<T>(Guid id, IDbConnection connection, IDbTransaction transaction) where T : Dao
        {
            Delete(id, typeof(T), connection, transaction);
        }

        public void Delete(Guid id, Type type, IDbConnection connection, IDbTransaction transaction)
        {
            var tableName = GetTableName(type);
            CreateTableIfNotExists(tableName);

            lock (AcquireLock(tableName))
            {
                if (_database[tableName].ContainsKey(id))
                {
                    _database[tableName].Remove(id);
                }
            }
        }

        public void DeleteAll(Type type, IDbConnection connection, IDbTransaction transaction)
        {
            var tableName = GetTableName(type);
            CreateTableIfNotExists(tableName);

            lock (AcquireLock(tableName))
            {
                _database[tableName].Clear();
            }
        }

        private static string GetTableName(Type type)
        {
            var tableName = string.Concat(type.Namespace, ".", type.Name);
            return tableName;
        }

        private static void CreateTableIfNotExists(string tableName)
        {
            lock (AcquireLock(tableName))
            {
                if (_database.ContainsKey(tableName) == false)
                {
                    _database[tableName] = new Dictionary<Guid, string>();
                }
            }
        }

        private static object AcquireLock(string tableName)
        {
            return _locks.GetOrAdd(tableName, s => new object());
        }
    }
}