using System;
using System.Collections.Generic;
using System.Globalization;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace Pepersistence
{
    public abstract class BasePersistenceManager<T> where T : ISaveData, new()
    {
        protected readonly JsonSerializerSettings SerializerSettings;
        private readonly List<ISavable<T>> savableObjects;
        private readonly ISaveSource saveSource;
        private IReadOnlyList<ISaveDataMigration> migrations;
        private T saveData;

        public bool IsLoaded { get; private set; }

        public BasePersistenceManager(ISaveSource saveSource)
        {
            this.saveSource = saveSource;
            savableObjects = new List<ISavable<T>>();

            SerializerSettings = new JsonSerializerSettings
            {
                Error = (sender, args) =>
                {
                    Debug.LogError($"Save load error at path '{args.ErrorContext.Path}': {args.ErrorContext.Error.Message}");
                    args.ErrorContext.Handled = true;
                }
            };
        }

        public void Register(ISavable<T> savable)
        {
            savableObjects.Add(savable);
        }

        public void InitializeMigration(IReadOnlyList<ISaveDataMigration> migrations)
        {
            this.migrations = migrations;
        }

        public void Save()
        {
            if (!IsLoaded)
            {
                Debug.LogWarning("Skip a save. Save method must be called after Load to prevent progress loss.");
                return;
            }

            for (int i = 0; i < savableObjects.Count; i++)
            {
                savableObjects[i].Save(ref saveData);
            }

            var saveObject = CreateSaveObject();
            saveSource.Save(saveObject);
        }

        public void Load()
        {
            if (!TryLoadSaveData(saveSource.Load()))
            {
                // A save that exists but cannot be read must not be replaced by new data while a backup can be loaded.
                var backup = saveSource is IRecoverableSaveSource recoverableSource ? recoverableSource.RecoverFromBackup() : null;
                if (backup == null || !TryLoadSaveData(backup))
                {
                    Debug.LogError("Unable to load a save object, create the new one.");
                    saveData = new T();
                }
            }

            for (int i = 0; i < savableObjects.Count; i++)
            {
                savableObjects[i].Load(saveData);
            }

            IsLoaded = true;
        }

        private SaveObject Migrate(SaveObject saveObject)
        {
            if (migrations == null || saveObject == null || string.IsNullOrEmpty(saveObject.Data))
            {
                return saveObject;
            }

            foreach (var migration in migrations)
            {
                try
                {
                    Version version = Version.Parse(saveObject.Version);
                    Version migrateToVersion = Version.Parse(migration.MigrateToVersion);
                    if (version >= migrateToVersion)
                    {
                        continue;
                    }

                    saveObject.Data = migration.Migrate(saveObject.Data);
                    saveObject.Version = migration.MigrateToVersion;
                    Debug.Log($"Migration {version} -> {migrateToVersion} performed");
                }
                catch (Exception e)
                {
                    Debug.LogError($"Migration error {migration}: {e}");
                }
            }

            return saveObject;
        }

        // Returns false when a save exists, but its data cannot be loaded.
        private bool TryLoadSaveData(SaveObject saveObject)
        {
            if (saveObject == null)
            {
                saveData = new T();
                return true;
            }

            if (string.IsNullOrEmpty(saveObject.Data))
            {
                return false;
            }

            saveObject = Migrate(saveObject);
            if (!IsWellFormedJson(saveObject.Data))
            {
                return false;
            }

            try
            {
                var data = JsonConvert.DeserializeObject<T>(saveObject.Data, SerializerSettings);
                if (data == null)
                {
                    return false;
                }

                saveData = data;
                return true;
            }
            catch (Exception e)
            {
                Debug.LogError($"Unable to load a save object. ({e.Message})");
                return false;
            }
        }

        // The tolerant serializer settings skip member errors and turn truncated JSON into partial data, so the
        // syntax is validated separately: damaged text must be recovered from a backup, not loaded partially.
        private static bool IsWellFormedJson(string json)
        {
            try
            {
                JToken.Parse(json);
                return true;
            }
            catch (JsonReaderException e)
            {
                Debug.LogError($"Save data is not valid JSON ({e.Message}).");
                return false;
            }
        }

        private SaveObject CreateSaveObject()
        {
            string version = Application.version;
            return new SaveObject
            {
                Data = JsonConvert.SerializeObject(saveData, SerializerSettings),
                Version = version,
                Date = DateTime.Now.ToString(CultureInfo.InvariantCulture)
            };
        }
    }
}