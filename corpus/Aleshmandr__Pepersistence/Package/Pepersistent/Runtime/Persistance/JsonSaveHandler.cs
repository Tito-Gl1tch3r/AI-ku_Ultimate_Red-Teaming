using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using Newtonsoft.Json;
using UnityEngine;
using Debug = UnityEngine.Debug;

namespace Pepersistence
{
    public static class JsonSaveHandler
    {
        private const string SavePathFormat = "{0}/{1}.jsav";
        private const string TempFileSuffix = ".tmp";
        private const string BackupFileSuffix = ".bak";
        private const string CorruptedFileSuffix = ".corrupt";
        private const int PendingWritesTimeoutMilliseconds = 10000;
        private static readonly UTF8Encoding FileEncoding = new UTF8Encoding(false);

        // Guards the write queue; never held during file I/O.
        private static readonly object queueSync = new object();
        private static readonly Dictionary<string, PendingWrite> pendingWrites = new Dictionary<string, PendingWrite>();
        private static readonly Queue<string> readyPaths = new Queue<string>();
        private static long lastSequence;
        private static string inFlightPath;
        private static bool isWriting;
        private static bool isQuitting;

        // Owns the save files: every read, write, recovery and deletion runs under it, so a timed-out wait never lets
        // two operations touch the same files.
        private static readonly object fileSync = new object();
        private static readonly Dictionary<string, long> writtenSequences = new Dictionary<string, long>();
        private static readonly Dictionary<string, int> failureStreaks = new Dictionary<string, int>();
        private static readonly HashSet<string> untrustedMainPaths = new HashSet<string>();
        private static long discardedSequence;

        private enum LoadStatus
        {
            Loaded,
            NotFound,
            Unreadable,
            Corrupted
        }

        public static T LoadFromFile<T>(string fileName, string encryptionKey = null) where T : class
        {
            var path = GetSavePath(fileName);
            // A queued background write of this file must reach the storage before it is read.
            WaitForWritesOrWarn(path);
            lock (fileSync)
            {
                var status = TryLoad(path, encryptionKey, true, out T result);
                if (status == LoadStatus.Loaded)
                {
                    return result;
                }

                if (status == LoadStatus.Corrupted)
                {
                    SetAsideCorrupted(path);
                }

                return LoadFallback<T>(path, encryptionKey, status.ToString());
            }
        }

        /// <summary>
        /// Sets the save file aside as corrupted and loads its backup. Use it when the file is readable, but its content
        /// turned out to be invalid. Returns null when no backup can be loaded.
        /// </summary>
        public static T RecoverFromBackup<T>(string fileName, string encryptionKey = null) where T : class
        {
            var path = GetSavePath(fileName);
            WaitForWritesOrWarn(path);
            lock (fileSync)
            {
                if (File.Exists(path))
                {
                    SetAsideCorrupted(path);
                }

                return LoadFallback<T>(path, encryptionKey, "invalid content");
            }
        }

        public static void SaveToFile<T>(T data, string fileName, string encryptionKey = null)
        {
            var path = GetSavePath(fileName);
            if (TrySerialize(data, out var json))
            {
                SaveSerialized(path, json, encryptionKey);
            }
        }

        /// <summary>
        /// Serializes the data on the calling (main) thread and writes the file on a background thread.
        /// A newer save of the same file replaces a queued write that has not started yet.
        /// </summary>
        public static void SaveToFileInBackground<T>(T data, string fileName, string encryptionKey = null)
        {
            var path = GetSavePath(fileName);
            if (!TrySerialize(data, out var json))
            {
                return;
            }

#if UNITY_WEBGL && !UNITY_EDITOR
            SaveSerialized(path, json, encryptionKey);
#else
            bool quitting;
            var startWorker = false;
            lock (queueSync)
            {
                quitting = isQuitting;
                if (!quitting)
                {
                    startWorker = Enqueue(path, json, encryptionKey);
                }
            }

            if (quitting)
            {
                // The process may exit before a background write completes.
                SaveSerialized(path, json, encryptionKey);
            }
            else if (startWorker)
            {
                StartWorker();
            }
#endif
        }

        /// <summary>
        /// Blocks until queued background writes are on the storage, retrying writes that failed before.
        /// Returns false if the timeout expires first or a write still fails.
        /// </summary>
        public static bool WaitForPendingWrites(int millisecondsTimeout = Timeout.Infinite)
        {
            return WaitForWrites(null, millisecondsTimeout);
        }

        internal static void CompletePendingWrites()
        {
            if (!WaitForWrites(null, PendingWritesTimeoutMilliseconds))
            {
                Debug.LogWarning("Background save writes did not complete: they failed or timed out.");
            }
        }

        /// <summary>
        /// Drops queued writes and runs the deletion while no other save file operation can run.
        /// </summary>
        internal static void DiscardPendingWrites(Action deleteFiles)
        {
            long lastQueuedSequence;
            lock (queueSync)
            {
                pendingWrites.Clear();
                readyPaths.Clear();
                lastQueuedSequence = lastSequence;
            }

            lock (fileSync)
            {
                // A write taken by the worker before the reset must not recreate a deleted save.
                discardedSequence = Math.Max(discardedSequence, lastQueuedSequence);
                untrustedMainPaths.Clear();
                failureStreaks.Clear();
                deleteFiles();
            }
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void InitializeBackgroundWrites()
        {
            lock (queueSync)
            {
                isQuitting = false;
            }

            Application.quitting -= OnApplicationQuitting;
            Application.quitting += OnApplicationQuitting;
        }

        private static void OnApplicationQuitting()
        {
            lock (queueSync)
            {
                isQuitting = true;
            }

            CompletePendingWrites();
        }

        private static string GetSavePath(string fileName)
        {
            return string.Format(SavePathFormat, Application.persistentDataPath, fileName);
        }

        private static bool TrySerialize<T>(T data, out string json)
        {
            try
            {
                json = JsonConvert.SerializeObject(data);
                return true;
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                json = null;
                return false;
            }
        }

        private static void SaveSerialized(string path, string json, string encryptionKey)
        {
            long sequence;
            lock (queueSync)
            {
                sequence = ++lastSequence;
                // This save supersedes a queued background write of the same file.
                pendingWrites.Remove(path);
            }

            WriteFileExclusive(path, json, encryptionKey, sequence);
        }

        // Returns true when the caller must start the worker.
        private static bool Enqueue(string path, string json, string encryptionKey)
        {
            var isQueued = pendingWrites.TryGetValue(path, out var existing) && !existing.Failed;
            pendingWrites[path] = new PendingWrite(json, encryptionKey, ++lastSequence, false);
            if (!isQueued)
            {
                readyPaths.Enqueue(path);
            }

            if (isWriting)
            {
                return false;
            }

            isWriting = true;
            return true;
        }

        private static void StartWorker()
        {
            try
            {
                ThreadPool.QueueUserWorkItem(ProcessPendingWrites);
            }
            catch (Exception e)
            {
                // Without a worker thread the queued writes complete on the calling thread.
                Debug.LogException(e);
                ProcessPendingWrites(null);
            }
        }

        private static void ProcessPendingWrites(object state)
        {
            var completed = false;
            try
            {
                while (TryTakeReadyWrite(out var path, out var write))
                {
                    var written = WriteFileExclusive(path, write.Json, write.EncryptionKey, write.Sequence);
                    FinishWrite(path, write, written);
                }

                completed = true;
            }
            finally
            {
                if (!completed)
                {
                    // Waiters must not stay blocked on a worker that stopped unexpectedly.
                    lock (queueSync)
                    {
                        isWriting = false;
                        inFlightPath = null;
                        Monitor.PulseAll(queueSync);
                    }
                }
            }
        }

        private static bool TryTakeReadyWrite(out string path, out PendingWrite write)
        {
            lock (queueSync)
            {
                while (readyPaths.Count > 0)
                {
                    path = readyPaths.Dequeue();
                    if (pendingWrites.TryGetValue(path, out write) && !write.Failed)
                    {
                        pendingWrites.Remove(path);
                        inFlightPath = path;
                        return true;
                    }
                }

                isWriting = false;
                Monitor.PulseAll(queueSync);
                path = null;
                write = default;
                return false;
            }
        }

        private static void FinishWrite(string path, PendingWrite write, bool written)
        {
            lock (queueSync)
            {
                inFlightPath = null;
                if (!written && !pendingWrites.ContainsKey(path))
                {
                    // Keeps the newest snapshot for a retry on the next save or flush instead of losing it.
                    pendingWrites[path] = write.AsFailed();
                }

                Monitor.PulseAll(queueSync);
            }
        }

        private static bool WaitForWrites(string path, int millisecondsTimeout)
        {
            var stopwatch = Stopwatch.StartNew();
            bool startWorker;
            lock (queueSync)
            {
                startWorker = RetryFailedWrites(path);
            }

            if (startWorker)
            {
                StartWorker();
            }

            lock (queueSync)
            {
                while (HasUnfinishedWrite(path))
                {
                    var remaining = Timeout.Infinite;
                    if (millisecondsTimeout != Timeout.Infinite)
                    {
                        remaining = millisecondsTimeout - (int)stopwatch.ElapsedMilliseconds;
                        if (remaining <= 0)
                        {
                            return false;
                        }
                    }

                    Monitor.Wait(queueSync, remaining);
                }

                return !HasFailedWrite(path);
            }
        }

        private static void WaitForWritesOrWarn(string path)
        {
            if (!WaitForWrites(path, PendingWritesTimeoutMilliseconds))
            {
                Debug.LogWarning($"Background save writes of '{path}' did not complete: they failed or timed out.");
            }
        }

        // Returns true when the caller must start the worker.
        private static bool RetryFailedWrites(string path)
        {
            var retried = false;
            foreach (var failedPath in new List<string>(pendingWrites.Keys))
            {
                var write = pendingWrites[failedPath];
                if (write.Failed && (path == null || path == failedPath))
                {
                    pendingWrites[failedPath] = write.AsRetried();
                    readyPaths.Enqueue(failedPath);
                    retried = true;
                }
            }

            if (!retried || isWriting)
            {
                return false;
            }

            isWriting = true;
            return true;
        }

        private static bool HasUnfinishedWrite(string path)
        {
            if (path == null)
            {
                return isWriting;
            }

            return inFlightPath == path || pendingWrites.TryGetValue(path, out var write) && !write.Failed;
        }

        private static bool HasFailedWrite(string path)
        {
            foreach (var pair in pendingWrites)
            {
                if (pair.Value.Failed && (path == null || path == pair.Key))
                {
                    return true;
                }
            }

            return false;
        }

        // Returns false only when the write failed and should be retried.
        private static bool WriteFileExclusive(string path, string json, string encryptionKey, long sequence)
        {
            lock (fileSync)
            {
                if (sequence <= discardedSequence || writtenSequences.TryGetValue(path, out var writtenSequence) && sequence <= writtenSequence)
                {
                    // A newer save of this file is already on the storage, or the saves were deleted after this one was queued.
                    return true;
                }

                if (!TryWriteFile(path, json, encryptionKey, out var error))
                {
                    ReportWriteFailure(path, error);
                    return false;
                }

                writtenSequences[path] = sequence;
                if (failureStreaks.TryGetValue(path, out var failures))
                {
                    failureStreaks.Remove(path);
                    Debug.LogWarning($"Save file '{path}' was written after {failures} failed attempts.");
                }

                return true;
            }
        }

        private static bool TryWriteFile(string path, string json, string encryptionKey, out Exception error)
        {
            var tempPath = path + TempFileSuffix;
            var backupPath = path + BackupFileSuffix;
            try
            {
                if (!string.IsNullOrEmpty(encryptionKey))
                {
                    json = XorEncryption.EncryptDecrypt(json, encryptionKey);
                }

                // The temporary file must reach the storage before the swap; otherwise a crash or power loss can leave
                // a renamed save file without its contents.
                using (var stream = new FileStream(tempPath, FileMode.Create, FileAccess.Write, FileShare.None))
                {
                    using (var writer = new StreamWriter(stream, FileEncoding))
                    {
                        writer.Write(json);
                        writer.Flush();
                        stream.Flush(true);
                    }
                }

                // The previous save becomes the backup, so a complete save file exists at every step of the swap.
                if (File.Exists(path))
                {
                    if (untrustedMainPaths.Contains(path))
                    {
                        // The main file failed to load; the backup holds the last good save and must be kept.
                        File.Delete(path);
                    }
                    else
                    {
                        if (File.Exists(backupPath))
                        {
                            File.Delete(backupPath);
                        }

                        File.Move(path, backupPath);
                    }
                }

                File.Move(tempPath, path);
                untrustedMainPaths.Remove(path);
                error = null;
                return true;
            }
            catch (Exception e)
            {
                error = e;
                TryDelete(tempPath);
                return false;
            }
        }

        private static void ReportWriteFailure(string path, Exception error)
        {
            failureStreaks.TryGetValue(path, out var failures);
            failureStreaks[path] = ++failures;
            if (failures == 1)
            {
                Debug.LogException(error);
            }
            else
            {
                // Only the first failure of a streak is reported as an exception, so a full disk does not flood the logs.
                Debug.LogWarning($"Save file '{path}' failed to write again ({failures} attempts in a row): {error.Message}");
            }
        }

        // Loads the backup, then a complete temporary file left by an interrupted save.
        private static T LoadFallback<T>(string path, string encryptionKey, string reason) where T : class
        {
            var backupPath = path + BackupFileSuffix;
            var status = TryLoad(backupPath, encryptionKey, true, out T result);
            if (status != LoadStatus.Loaded)
            {
                backupPath = path + TempFileSuffix;
                // A temporary file is often incomplete, so its failures are expected and not reported.
                status = TryLoad(backupPath, encryptionKey, false, out result);
            }

            if (status != LoadStatus.Loaded)
            {
                return null;
            }

            if (File.Exists(path))
            {
                // The main file could not be loaded or set aside; the next save must not rotate it into the backup.
                untrustedMainPaths.Add(path);
            }

            Debug.LogWarning($"Save file '{path}' could not be loaded ({reason}), restored from '{backupPath}'.");
            return result;
        }

        private static LoadStatus TryLoad<T>(string path, string encryptionKey, bool reportFailures, out T result) where T : class
        {
            result = null;
            if (!File.Exists(path))
            {
                return LoadStatus.NotFound;
            }

            string json;
            try
            {
                json = File.ReadAllText(path);
            }
            catch (FileNotFoundException)
            {
                return LoadStatus.NotFound;
            }
            catch (Exception e)
            {
                if (reportFailures)
                {
                    Debug.LogException(e);
                }

                return LoadStatus.Unreadable;
            }

            try
            {
                if (!string.IsNullOrEmpty(encryptionKey))
                {
                    json = XorEncryption.EncryptDecrypt(json, encryptionKey);
                }

                result = JsonConvert.DeserializeObject<T>(json);
            }
            catch (Exception e)
            {
                if (reportFailures)
                {
                    Debug.LogException(e);
                }

                return LoadStatus.Corrupted;
            }

            if (result == null)
            {
                // Empty, whitespace-only or zero-filled files deserialize to null without an exception.
                if (reportFailures)
                {
                    Debug.LogError($"Save file '{path}' contains no data.");
                }

                return LoadStatus.Corrupted;
            }

            return LoadStatus.Loaded;
        }

        private static void SetAsideCorrupted(string path)
        {
            var corruptedPath = path + CorruptedFileSuffix;
            try
            {
                if (File.Exists(corruptedPath))
                {
                    File.Delete(corruptedPath);
                }

                File.Move(path, corruptedPath);
                Debug.LogWarning($"Corrupted save file '{path}' was moved to '{corruptedPath}'.");
            }
            catch (Exception e)
            {
                Debug.LogException(e);
            }
        }

        private static void TryDelete(string path)
        {
            try
            {
                if (File.Exists(path))
                {
                    File.Delete(path);
                }
            }
            catch (Exception e)
            {
                Debug.LogException(e);
            }
        }

        private struct PendingWrite
        {
            public readonly string Json;
            public readonly string EncryptionKey;
            public readonly long Sequence;
            public readonly bool Failed;

            public PendingWrite(string json, string encryptionKey, long sequence, bool failed)
            {
                Json = json;
                EncryptionKey = encryptionKey;
                Sequence = sequence;
                Failed = failed;
            }

            public PendingWrite AsFailed()
            {
                return new PendingWrite(Json, EncryptionKey, Sequence, true);
            }

            public PendingWrite AsRetried()
            {
                return new PendingWrite(Json, EncryptionKey, Sequence, false);
            }
        }
    }
}