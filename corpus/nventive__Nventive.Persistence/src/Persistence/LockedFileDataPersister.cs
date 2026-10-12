using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.ExceptionServices;
using System.Threading;
using System.Threading.Tasks;
using Uno.Extensions;
using Uno.Logging;
using Uno.Threading;
using System.Diagnostics;
using Microsoft.Extensions.Logging;
using Uno.Disposables;

namespace Nventive.Persistence
{
	/// <summary>
	/// This is an implementation of <see cref="IDataPersister{T}"/> base on System.IO namespace. [IMPORTANT: see remarks]
	/// </summary>
	/// <remarks>
	/// Designed to work on a filesystem not supporting transactions natively.
	/// IMPORTANT: do NOT use this if you can accessing this file from another method, because
	/// a custom mecanism is done to ensure transactional operations and accessing it from
	/// elsewhere could break this protection.
	/// ALSO IMPORTANT: All concurrent access to this file SHOULD be done throught the same implementation of this class
	/// or the behavior could become unpredictible and even get deadlocks.
	/// </remarks>
	[DebuggerDisplay("{DebuggerFilename}")]
	public sealed partial class LockedFileDataPersister<T> : IDataPersister<T>, IDisposable
	{
		/*
		 * -- TRANSACTIONAL MECANISM --
		 * 
		 * This class is using a manual transactional file access. Because it's
		 * designed to work on any file system, any operating system, this class
		 * won't rely on any external transaction system.
		 * 
		 * FILES ON DISK:
		 *   - COMMITTED: <filename> - last committed version of the file
		 *   - NEW: <filename>.new - an ongoing transaction file
		 *   - LOCK: <filename>.lck - an active lock from a process for a transaction.  This file is opened in exclusive mode during all the writing process.
		 *   - OLD: <filename>.old - last committed file renamed to let the ongoing becoming the new committed.
		 * 		 
		 * PROCESS FOR UPDATE OPERATION:
		 * 
		 * 1) Lock the file (see LOCKING PROCESS below)
		 * 2) Read the COMMITTED file
		 * 3) Call code updater (update callback func)
		 * 4) If the context is not committed, go to step 9
		 * 5) Save the result in the NEW file, flush & close the file.
		 * 6) Rename the COMMITTED as OLD file (atomic operation in OS)  -- STARTING HERE THE CHANGE IS DURABLE
		 * 7) Rename the NEW as COMMITTED file (atomic operation in OS)
		 * 8) Delete the OLD file
		 * 9) Close & delete the LOCK file
		 * 
		 * PROCESS FOR READ OPERATION:
		 * 
		 * 1) Lock the file (see LOCKING PROCESS below)
		 * 2) Read the COMMITTED file (update only)
		 * 3) Close & delete the LOCK file
		 * 
		 * LOCKING PROCESS:
		 * 1) Try to open the LOCK file in exclusive mode (even if it exists) & keep the file opened until the end of the operation, wait & retry as needed
		 * 2) If all files (OLD, COMMITTED and NEW exists), Delete the OLD and rename the COMMITTED as OLD  --- that's an odd situation who should be reported
		 * 3) If both OLD and NEW exists, rename the NEW as COMMITTED  -- This is a FORWARD resolution (previous change was completed - rolling forward)
		 * 4) If both OLD and COMMITTED exists, delete the OLD
		 * 5) Delete any existing NEW file (uncompleted)  -- This is a BACKWARD resolution (previous change was uncompleted - rolling back)
		 * 
		 */

		private readonly string _committedFile;
		private readonly string _oldFile;
		private readonly string _newFile;
		private readonly string _lockFile;
		private readonly Uno.FuncAsync<Stream, T> _read;
		private readonly Uno.ActionAsync<T, Stream> _write;
		private readonly FileDataPersisterSettings _settings;

		private readonly FastAsyncLock _lock = new FastAsyncLock();

		private FileStream _openedFileStream = null;
		private DataReaderLoadResult<T> _persistedData;

		private string DebuggerFilename => Path.GetFileName(_committedFile);

#region Constructors

		private LockedFileDataPersister()
		{
		}

		/// <summary>
		/// Constructor with callbacks for read & write operations.
		/// </summary>
		public LockedFileDataPersister(
			string fullFilename,
			Uno.FuncAsync<Stream, T> read,
			Uno.ActionAsync<T, Stream> write,
			FileDataPersisterSettings settings = null,
			IEqualityComparer<T> comparer = null) : this()
		{
			_committedFile = new FileInfo(fullFilename.Validation().NotNull(nameof(fullFilename))).FullName;
			_read = read;
			_write = write;
			_settings = settings ?? FileDataPersisterSettings.Default;
			Comparer = comparer;

			// Create other working file names
			_oldFile = _committedFile + ".old";
			_newFile = _committedFile + ".new";
			_lockFile = _committedFile + ".lck";
		}
#endregion

#region Implementation if IDataPersister<T>

		/// <inheritdoc />
		public async Task<DataReaderLoadResult<T>> Load(CancellationToken ct)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Loading file '{DebuggerFilename}'.");
			}

			using (await _lock.LockAsync(ct))
			{
				if (_openedFileStream != null && _persistedData != null)
				{
					if (this.Log().IsEnabled(LogLevel.Information))
					{
						this.Log().Info($"Loaded file '{DebuggerFilename}' from the local memory.");
					}

					// The file is opened and we already have a "cached" version of the data
					return _persistedData;
				}

				// 1) Lock the file (see LOCKING PROCESS below)
				using (await GetFileLock(ct))
				{
					if (!File.Exists(_committedFile))
					{
						if (this.Log().IsEnabled(LogLevel.Information))
						{
							this.Log().Info($"Loaded empty file '{DebuggerFilename}' because it doesn't exist.");
						}

						// The file doesn't exist
						return new DataReaderLoadResult<T>(this, correlationTag: null);
					}

					// 2) Read the COMMITTED file (update only)
					try
					{
						try
						{
							var stream = OpenReadingStream();

							if (_settings.ExclusiveMode)
							{
								stream = new UndisposableStream(stream);
							}

							var entity = await _read(ct, stream);

							if (this.Log().IsEnabled(LogLevel.Information))
							{
								this.Log().Info($"Loaded file '{DebuggerFilename}' from the file system.");
							}

							return _persistedData = new DataReaderLoadResult<T>(this, entity, correlationTag: null);
						}
						finally
						{
							CloseReadingStream();
						}
					}
					catch (FileNotFoundException)
					{
						if (this.Log().IsEnabled(LogLevel.Information))
						{
							this.Log().Info($"Loaded empty file '{DebuggerFilename}' because it doesn't exist.");
						}

						return new DataReaderLoadResult<T>(this, correlationTag: null); // empty version
					}
					catch (Exception ex)
					{
						if (this.Log().IsEnabled(LogLevel.Error))
						{
							this.Log().Error($"Could not load file '{DebuggerFilename}'.", ex);
						}

						var exceptionInfo = ExceptionDispatchInfo.Capture(ex);
						return new DataReaderLoadResult<T>(this, exceptionInfo);
					}

					// 3) Close & delete the LOCK file
				}
			}
		}

		/// <inheritdoc />
		public bool IsDataConstant { get; } = false;

		/// <inheritdoc />
		public IEqualityComparer<T> Comparer { get; }

		/// <inheritdoc />
		public Task<DataPersisterUpdateResult<T>> Update(CancellationToken ct, DataPersisterUpdaterWithContext<T> updater, object correlationTag = null)
		{
			// Reuse the same logic as the async version
			return Update(ct, async (_, c) => updater(c), correlationTag);
		}

		/// <inheritdoc />
		public async Task<DataPersisterUpdateResult<T>> Update(CancellationToken ct, DataPersisterAsyncUpdaterWithContext<T> asyncUpdater, object correlationTag = null)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Updating file '{DebuggerFilename}'.");
			}

			using (await _lock.LockAsync(ct))
			{
				// 1) Lock the file (see LOCKING PROCESS below)
				using (await GetFileLock(ct))
				{
					// 2) Read the COMMITTED file
					var data = default(T);
					bool exists = false;
					DataReaderLoadResult<T> readData = null;
					try
					{
						if (_openedFileStream != null)
						{
							if (_persistedData != null)
							{
								if (this.Log().IsEnabled(LogLevel.Debug))
								{
									this.Log().Debug($"Loaded file '{DebuggerFilename}' from the local memory.");
								}

								readData = _persistedData;
								exists = true;
							}
						}

						if (readData == null)
						{
							if (File.Exists(_committedFile))
							{
								try
								{
									var stream = OpenReadingStream();
									if (_settings.ExclusiveMode)
									{
										stream = new UndisposableStream(stream);
									}

									data = await _read(ct, stream);
									exists = true;

									if (this.Log().IsEnabled(LogLevel.Debug))
									{
										this.Log().Debug($"Loaded file '{DebuggerFilename}' from the file system.");
									}
								}
								finally
								{
									CloseReadingStream();
								}
							}
							else
							{
								if (this.Log().IsEnabled(LogLevel.Debug))
								{
									this.Log().Debug($"Loaded empty file '{DebuggerFilename}' because it doesn't exist.");
								}
							}

							readData = new DataReaderLoadResult<T>(this, data, exists, correlationTag: null);
						}
					}
					catch (FileNotFoundException)
					{
						if (this.Log().IsEnabled(LogLevel.Debug))
						{
							this.Log().Debug($"Loaded empty file '{DebuggerFilename}' because it doesn't exist.");
						}

						readData = new DataReaderLoadResult<T>(this, correlationTag: null); // empty
					}
					catch (Exception ex)
					{
						if (this.Log().IsEnabled(LogLevel.Error))
						{
							this.Log().Error($"Could not load file '{DebuggerFilename}' for update.", ex);
						}

						var exceptionInfo = ExceptionDispatchInfo.Capture(ex);
						readData = new DataReaderLoadResult<T>(this, exceptionInfo, correlationTag: null);
					}

					var control = new DataPersisterTransactionContext<T>(readData, correlationTag);

					DataPersisterUpdateResult<T> result;
					try
					{
						// 3) Call code updater (update callback func)
						await asyncUpdater(ct, control);

						if (!control.IsCommitted)
						{
							if (this.Log().IsEnabled(LogLevel.Information))
							{
								this.Log().Info($"Returning uncommited update of file '{DebuggerFilename}'.");
							}

							// 4) If the context is not committed, go to step 9
							return new DataPersisterUpdateResult<T>(control);
						}

						CloseReadingStream(force: true); // we know here the cached value is not valid anymore.

						// x) Alternate flow if the updater ask for a delete
						if (control.IsRemoved)
						{
							if (exists)
							{
								File.Delete(_committedFile);
							}
							else
							{
								control.Reset(); // no update done
							}

							if (this.Log().IsEnabled(LogLevel.Information))
							{
								this.Log().Info($"Deleted file '{DebuggerFilename}'.");
							}

							return new DataPersisterUpdateResult<T>(control);
						}

						// 5) Save the result in the NEW file, flush & close the file.
						using (var stream = File.OpenWrite(_newFile))
						{
							await _write(ct, control.CommittedValue, stream);
						}

						if (File.Exists(_committedFile))
						{
							// 6) Rename the COMMITTED as OLD file (atomic operation in OS)  -- STARTING HERE THE CHANGE IS DURABLE
							File.Move(_committedFile, _oldFile);

							// 7) Rename the NEW as COMMITTED file (atomic operation in OS)
							File.Move(_newFile, _committedFile);

							// 8) Delete the OLD file
							File.Delete(_oldFile);
						}
						else
						{
							// 6-7-8) Rename the NEW as COMMITTED file (atomic operation in OS)
							File.Move(_newFile, _committedFile);
						}

						result = new DataPersisterUpdateResult<T>(control);

						if (_settings.ExclusiveMode)
						{
							OpenReadingStream();
							_persistedData = result.Updated;
						}

						if (this.Log().IsEnabled(LogLevel.Information))
						{
							this.Log().Info($"Updated file '{DebuggerFilename}'.");
						}
					}
					catch (Exception ex)
					{
						if (this.Log().IsEnabled(LogLevel.Error))
						{
							this.Log().Error($"Could not update file '{DebuggerFilename}'.", ex);
						}

						var error = ExceptionDispatchInfo.Capture(ex);
						result = new DataPersisterUpdateResult<T>(readData, error, correlationTag);
					}

					return result;
				} // 9) Close & delete the LOCK file
			}
		}

#endregion

		private Stream OpenReadingStream()
		{
			if (_openedFileStream != null && _openedFileStream.CanRead)
			{
				// Already opened, we just seek to beginning for next read.
				_openedFileStream.Seek(0, SeekOrigin.Begin);
				return _openedFileStream;
			}

			return _openedFileStream = new FileStream(
				_committedFile,
				FileMode.Open,
				FileAccess.ReadWrite,
				_settings.ExclusiveMode ? FileShare.None : FileShare.Read);
		}

		private void CloseReadingStream(bool force = false)
		{
			// When exclusive mode is activated, the stream will stay opened in exclusive mode
			// to prevent any external change to it. As long the file is opened, we know the
			// in-memory cached version is valid.
			if (!_settings.ExclusiveMode || force)
			{
				_openedFileStream?.Dispose();

				_openedFileStream = null;
				_persistedData = null;
			}
		}

		// Implementation of the LOCKING PROCESS
		private async Task<IDisposable> GetFileLock(CancellationToken ct)
		{
			FileStream file = null;

			// 1) Try to open the LOCK file in exclusive mode (even if it exists) &keep the file opened until the end of the operation, wait & retry as needed
			ushort tryNo = 1;
			while (!ct.IsCancellationRequested && tryNo++ < _settings.NumberOfRetries)
			{
				try
				{
					file = File.Open(_lockFile, FileMode.OpenOrCreate, FileAccess.Write, FileShare.None);
					break;
				}
				catch (Exception ex)
				{
					if (this.Log().IsEnabled(LogLevel.Warning))
					{
						this.Log().Warn($"Unable to open lock file '{_lockFile}', try #{tryNo}", ex);
					}

					await Task.Delay(tryNo * _settings.RetryDelay, ct);
				}
			}

			if (ct.IsCancellationRequested)
			{
				return Disposable.Empty;
			}

			if (file == null)
			{
				// unable to lock file
				throw new InvalidOperationException("Failed to lock the target file.");
			}

			var oldExists = File.Exists(_oldFile);
			var committedExists = File.Exists(_committedFile);
			var newExists = File.Exists(_newFile);

			// 2) If all files (OLD, COMMITTED and NEW exists), Delete the OLD and rename the COMMITTED as OLD  ---that's an odd situation who should be reported
			if (oldExists && committedExists && newExists)
			{
				if (this.Log().IsEnabled(LogLevel.Warning))
				{
					this.Log().Warn($"An inconsistent state of the file is found. Make sure all code accessing the '{_committedFile}' file is using the {nameof(LockedFileDataPersister<T>)} accessor.");
				}
				
				File.Delete(_oldFile);
				File.Move(_committedFile, _oldFile);
				committedExists = false;
			}

			// 3) If both OLD and NEW exists, rename the NEW as COMMITTED  --This is a FORWARD resolution (previous change was completed - rolling forward)
			if (oldExists && newExists)
			{
				if (this.Log().IsEnabled(LogLevel.Warning))
				{
					this.Log().Warn($"Rolling forward previous transaction on file '{_committedFile}'.");
				}

				File.Move(_newFile, _committedFile);
				newExists = false;
				committedExists = true;
			}
			// 4) If both OLD and COMMITTED exists, delete the OLD
			if (oldExists && committedExists)
			{
				File.Delete(_oldFile);
			}

			// 5) Delete any existing NEW file (uncompleted)-- This is a BACKWARD resolution (previous change was uncompleted - rolling back)
			if (newExists)
			{
				if (this.Log().IsEnabled(LogLevel.Warning))
				{
					this.Log().Warn($"Rolling back previous transaction on file '{_committedFile}'.");
				}

				File.Delete(_newFile);
			}

			// Return a disposable who will close & delete the lock file
			return Disposable
				.Create(() =>
				{
					file.Dispose();
					File.Delete(_lockFile);
				});
		}

		public void Dispose()
		{
			CloseReadingStream(force: true);
		}
	}
}
