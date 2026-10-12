using System;
using System.IO;
using System.Text.RegularExpressions;
using UnityEngine;

namespace Pepersistence
{
    public static class LocalSaveFilesManager
    {
        // Includes the temporary, backup and corrupted copies, otherwise a cleared save would be restored from its backup.
        private const string SaveFilesFilter = @"^.*sav(\.(tmp|bak|corrupt))?$";

        public static void DeleteAllSaves()
        {
            // Queued background writes are dropped, so they cannot recreate a deleted save.
            JsonSaveHandler.DiscardPendingWrites(DeleteSaveFiles);
        }

        private static void DeleteSaveFiles()
        {
            // Get the path to the persistent data directory
            string dataPath = Application.persistentDataPath;

            // Check if the directory exists
            if (Directory.Exists(dataPath))
            {
                // Get all files in the directory
                string[] files = Directory.GetFiles(dataPath);
                if (files.Length == 0)
                {
                    Debug.Log("No saves found");
                    return;
                }

                // Delete files that match the pattern
                foreach (var file in files)
                {
                    if (Regex.IsMatch(Path.GetFileName(file), SaveFilesFilter))
                    {
                        try
                        {
                            File.Delete(file);
                            Debug.Log($"Save deleted: {file}");
                        }
                        catch (Exception ex)
                        {
                            Debug.LogError($"Error deleting save file {file}: {ex.Message}");
                        }
                    }
                }
            }
            else
            {
                Debug.LogError("Persistent data directory does not exist.");
            }
        }
    }
}