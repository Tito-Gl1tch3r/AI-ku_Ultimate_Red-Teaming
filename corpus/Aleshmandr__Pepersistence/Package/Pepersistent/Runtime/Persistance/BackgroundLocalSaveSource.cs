using UnityEngine.Scripting;

namespace Pepersistence
{
    /// <summary>
    /// Local save source that keeps disk I/O off the calling thread: saves are serialized immediately and written
    /// to the storage on a background thread.
    /// </summary>
    public class BackgroundLocalSaveSource : ISaveSource, IRecoverableSaveSource
    {
        private readonly string savePath;
        private readonly string encryptionKey;

        [Preserve]
        public BackgroundLocalSaveSource() : this("save", null)
        {}

        public BackgroundLocalSaveSource(string savePath, string encryptionKey)
        {
            this.savePath = savePath;
            this.encryptionKey = encryptionKey;
        }

        public SaveObject Load()
        {
            return JsonSaveHandler.LoadFromFile<SaveObject>(savePath, encryptionKey);
        }

        public SaveObject RecoverFromBackup()
        {
            return JsonSaveHandler.RecoverFromBackup<SaveObject>(savePath, encryptionKey);
        }

        public void Save(SaveObject save)
        {
            JsonSaveHandler.SaveToFileInBackground(save, savePath, encryptionKey);
        }
    }
}