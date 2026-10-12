using System;
using System.Collections.Generic;
using System.Data;
using Simbad.Platform.Persistence.Transactions;

namespace Simbad.Platform.Persistence.Storage
{
    public interface IStorageAdapter
    {
        T Fetch<T>(Guid id, IDbConnection connection, IDbTransaction transaction) where T : Dao;

        Dao Fetch(Guid id, Type type, IDbConnection connection, IDbTransaction transaction);

        ICollection<T> Fetch<T>(Func<T, bool> predicate, IDbConnection connection, IDbTransaction transaction) where T : Dao;

        ICollection<T> FetchAll<T>(IDbConnection connection, IDbTransaction transaction) where T : Dao;

        ICollection<Dao> FetchAll(Type type, IDbConnection connection, IDbTransaction transaction);

        void Transaction(Action<ITransactionWrapper> action);

        TResult Transaction<TResult>(Func<ITransactionWrapper, TResult> action);

        void Save<T>(T dao, IDbConnection connection, IDbTransaction transaction) where T : Dao;

        void Save(Dao dao, Type type, IDbConnection connection, IDbTransaction transaction);

        void Delete<T>(Guid id, IDbConnection connection, IDbTransaction transaction) where T : Dao;

        void Delete(Guid id, Type type, IDbConnection connection, IDbTransaction transaction);

        void DeleteAll(Type type, IDbConnection connection, IDbTransaction transaction);
    }
}