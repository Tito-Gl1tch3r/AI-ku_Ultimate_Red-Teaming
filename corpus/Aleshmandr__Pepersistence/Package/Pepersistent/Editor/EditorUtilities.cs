using UnityEditor;
using UnityEngine;

namespace Pepersistence.Editor
{
    public static class EditorUtilities
    {
        [MenuItem("Edit/Pepersistence/Open Persistent Data Path")]
        public static void OpenPersistentDataPath()
        {
            EditorUtility.RevealInFinder(Application.persistentDataPath);
        }

        [MenuItem("Edit/Pepersistence/Clear All Saves")]
        public static void ClearLocalSavedData()
        {
            LocalSaveFilesManager.DeleteAllSaves();
        }
    }
}