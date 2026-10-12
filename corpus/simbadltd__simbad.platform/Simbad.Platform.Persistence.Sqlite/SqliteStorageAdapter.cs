using System;
using System.Collections.Generic;
using System.Data;
using System.IO;
using System.Linq;
using Mono.Data.Sqlite;
using Simbad.Platform.Core;
using Simbad.Platform.Persistence.Storage;
using Simbad.Platform.Persistence.Transactions;
using Simbad.Platform.Persistence.Utils;

namespace Simbad.Platform.Persistence.Sqlite
{
    public sealed class SqliteStorageAdapter : IStorageAdapter
    {
        static SqliteStorageAdapter()
        {
            Bootstrap.LoadSqliteDll();
        }
        
        public T Fetch<T>(Guid id, IDbConnection connection, IDbTransaction transaction) where T : Dao
        {
            return Fetch(id, typeof(T), connection, transaction) as T;
        }

        public Dao Fetch(Guid id, Type type, IDbConnection connection, IDbTransaction transaction)
        {
            // todo [kk]: check that type is derived from PersistenceModel

            var tableName = GetTableName(type);
            CreateTableIfNotExists(tableName, connection, transaction);

            var text = $@"SELECT [Data] FROM [{tableName}] WHERE Id = @id";
            var data = ReadData(connection, transaction, text, ("id", Id2Str(id)));

            if (data == null || data.Count == 0)
            {
                return null;
            }

            var model = Json.Deserialize(data.Single(), type) as Dao;
            return model;
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
            CreateTableIfNotExists(tableName, connection, transaction);

            var text = $@"SELECT [Data] FROM [{tableName}]";
            var data = ReadData(connection, transaction, text);

            var models = data.Select(x => Json.Deserialize(x, type) as Dao).ToList();
            return models;
        }

        public void Transaction(Action<ITransactionWrapper> action)
        {
            using (var connection = CreateConnection())
            {
                connection.Open();
                using (var transaction = connection.BeginTransaction(IsolationLevel.ReadCommitted))
                {
                    var transactionWrapper = new DefaultTransactionWrapper(connection, transaction, this);
                    action(transactionWrapper);
                    transaction.Commit();
                }
            }
        }

        public TResult Transaction<TResult>(Func<ITransactionWrapper, TResult> action)
        {
            using (var connection = CreateConnection())
            {
                connection.Open();
                using (var transaction = connection.BeginTransaction(IsolationLevel.ReadCommitted))
                {
                    var transactionWrapper = new DefaultTransactionWrapper(connection, transaction, this);
                    var result = action(transactionWrapper);
                    transaction.Commit();

                    return result;
                }
            }
        }

        public void Save<T>(T model, IDbConnection connection, IDbTransaction transaction) where T : Dao
        {
            Save(model, typeof(T), connection, transaction);
        }

        public void Save(Dao model, Type type, IDbConnection connection, IDbTransaction transaction)
        {
            // todo [kk]: check that type is derived from Dao

            var tableName = GetTableName(type);
            CreateTableIfNotExists(tableName, connection, transaction);

            var data = Json.Serialize(model);
            SaveData(tableName, model.Id, data, connection, transaction);
        }

        public void Delete<T>(Guid id, IDbConnection connection, IDbTransaction transaction) where T : Dao
        {
            Delete(id, typeof(T), connection, transaction);
        }

        public void Delete(Guid id, Type type, IDbConnection connection, IDbTransaction transaction)
        {
            var tableName = GetTableName(type);
            CreateTableIfNotExists(tableName, connection, transaction);

            var text = $@"DELETE FROM [{tableName}] WHERE Id = @id";
            ExecuteNonQuery(connection, transaction, text, ("id", Id2Str(id)));
        }

        public void DeleteAll(Type type, IDbConnection connection, IDbTransaction transaction)
        {
            var tableName = GetTableName(type);
            CreateTableIfNotExists(tableName, connection, transaction);

            var text = $@"DELETE FROM [{tableName}]";
            ExecuteNonQuery(connection, transaction, text);
        }

        private static string GetTableName(Type type)
        {
            var tableName = string.Concat(type.Namespace, ".", type.Name);
            return tableName;
        }

        private static void SaveData(string tableName, Guid id, string data, IDbConnection connection,
            IDbTransaction transaction)
        {
            var idStr = Id2Str(id);

            var updateText = $@"UPDATE [{tableName}] SET Data = @data WHERE Id = @id";
            ExecuteNonQuery(connection, transaction, updateText, ("id", idStr), ("data", data));

            var insertOrIgnoreText = $@"INSERT OR IGNORE INTO [{tableName}] (Id, Data) VALUES (@id, @data)";
            ExecuteNonQuery(connection, transaction, insertOrIgnoreText, ("id", idStr), ("data", data));
        }

        private static string Id2Str(Guid id)
        {
            return id.ToString("D");
        }

        private static void CreateTableIfNotExists(string tableName, IDbConnection connection, IDbTransaction transaction)
        {
            var text =
                $@"CREATE TABLE IF NOT EXISTS [{tableName}] ([Id] NVARCHAR(36) NOT NULL PRIMARY KEY,[Data] NVARCHAR NOT NULL)";

            ExecuteNonQuery(connection, transaction, text);
        }

        private static SqliteConnection CreateConnection()
        {
            var dbFilePath = Global.Parameter<string>(PersistenceConfigurationExtension.DbPathParameterName);
            if (!File.Exists(dbFilePath))
            {
                var directoryName = Path.GetDirectoryName(dbFilePath);
                if (string.IsNullOrEmpty(directoryName) == false) Directory.CreateDirectory(directoryName);
                SqliteConnection.CreateFile(dbFilePath);
            }

            var connection = new SqliteConnection
            {
                ConnectionString = new SqliteConnectionStringBuilder { DataSource = dbFilePath }.ConnectionString
            };

            return connection;
        }

        private static void ExecuteNonQuery(IDbConnection connection, IDbTransaction transaction, string text,
            params (string, object)[] @params)
        {
            var command = connection.CreateCommand();
            command.Transaction = transaction;
            command.CommandText = text;

            if (@params != null)
            {
                foreach (var p in @params)
                {
                    var parameter = command.CreateParameter();
                    parameter.ParameterName = p.Item1;
                    parameter.Value = p.Item2;

                    command.Parameters.Add(parameter);
                }
            }

            command.ExecuteNonQuery();
        }

        private static List<string> ReadData(IDbConnection connection, IDbTransaction transaction, string text,
            params (string, object)[] @params)
        {
            var data = new List<string>();

            var command = connection.CreateCommand();
            command.Transaction = transaction;
            command.CommandText = text;

            if (@params != null)
            {
                foreach (var p in @params)
                {
                    var parameter = command.CreateParameter();
                    parameter.ParameterName = p.Item1;
                    parameter.Value = p.Item2;
                }
            }

            var reader = command.ExecuteReader();

            while (reader.Read())
            {
                data.Add(reader.GetString(0));
            }

            return data;
        }
    }
}