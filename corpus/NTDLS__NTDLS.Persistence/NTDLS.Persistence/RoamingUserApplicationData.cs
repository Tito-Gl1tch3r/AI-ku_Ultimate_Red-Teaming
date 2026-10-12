using Newtonsoft.Json;

namespace NTDLS.Persistence
{
    /// <summary>
    /// Reads/writes to the directory that serves as a common repository for application-specific data for the current roaming user.
    /// </summary>
    public class RoamingUserApplicationData
    {
        /// <summary>
        /// Json serializes an object and saves it to the disk.
        /// </summary>
        public static void SaveToDisk<T>(string applicationName, T obj, IEncryptionProvider? encryptionProvider = null)
            => PathPersistence.SaveToDisk<T>(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), applicationName, obj, encryptionProvider);

        /// <summary>
        /// Json serializes an object and saves it to the disk.
        /// </summary>
        public static void SaveToDisk<T>(string applicationName, T obj, JsonSerializerSettings settings, IEncryptionProvider? encryptionProvider = null)
            => PathPersistence.SaveToDisk<T>(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), applicationName, obj, settings, encryptionProvider);

        /// <summary>
        /// Loads the object from disk, deserializes it ans returns the object.
        /// </summary>
        public static T? LoadFromDisk<T>(string applicationName, IEncryptionProvider? encryptionProvider = null)
            => PathPersistence.LoadFromDisk<T>(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), applicationName, encryptionProvider);

        /// <summary>
        /// Loads the object from disk, deserializes it ans returns the object.
        /// </summary>
        public static T LoadFromDisk<T>(string applicationName, T defaultResult, IEncryptionProvider? encryptionProvider = null)
            => PathPersistence.LoadFromDisk(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), applicationName, defaultResult, encryptionProvider);

        /// <summary>
        /// Deletes a persistent file from the disk
        /// </summary>
        public static void DeleteFromDisk(string applicationName, Type objectType)
            => PathPersistence.DeleteFromDisk(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), applicationName, objectType);
    }
}
