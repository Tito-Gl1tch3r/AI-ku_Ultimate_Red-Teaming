using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.ExceptionServices;
using System.Threading;
using System.Threading.Tasks;
using Uno.Extensions;
using Uno.Logging;

namespace Nventive.Persistence
{
	/// <summary>
	/// Implementation of IDataReader over a file on disk.
	/// </summary>
	/// <remarks>
	/// The file is opened in shared readonly mode. If you need a writeable version, use LockedFileDataPersister.
	/// </remarks>
	public class FileDataReader<T> : IDataReader<T>
	{
		private readonly string _filename;
		private readonly Uno.FuncAsync<Stream, T> _read;
		private bool _isRead;
		private DataReaderLoadResult<T> _value;

		/// <summary>
		/// Constructor using a callback to read stream from file.
		/// </summary>
		public FileDataReader(string filename, Uno.FuncAsync<Stream, T> read, bool fileIsUnmodifiable = false, IEqualityComparer<T> comparer = null)
		{
			_filename = filename.Validation().NotNull(nameof(filename));
			_read = read.Validation().NotNull(nameof(read));
			IsDataConstant = fileIsUnmodifiable;
			Comparer = comparer;
		}

		/// <inheritdoc />
		public async Task<DataReaderLoadResult<T>> Load(CancellationToken ct)
		{
			if (IsDataConstant && _isRead)
			{
				return _value; // already read
			}
			try
			{
				using (var stream = File.Open(_filename, FileMode.Open, FileAccess.Read, FileShare.Read))
				{
					var entity = await _read(ct, stream);
					var result = new DataReaderLoadResult<T>(this, entity, correlationTag: null);

					if (IsDataConstant && !ct.IsCancellationRequested)
					{
						// Save value for future .Load() calls, because the file can't be modified.
						_value = result;
						_isRead = true;
					}

					return result;
				}
			}
			catch (FileNotFoundException ex)
			{
				return LogAndReturnDefault(ex);
			}
			catch (Exception ex)
			{
				return new DataReaderLoadResult<T>(this, ExceptionDispatchInfo.Capture(ex), correlationTag: null);
			}
		}

		private DataReaderLoadResult<T> LogAndReturnDefault(Exception ex)
		{
			this.Log().WarnIfEnabled(() => $"Error opening file [{_filename}]", ex);
			return new DataReaderLoadResult<T>(this, correlationTag: null);
		}

		/// <inheritdoc />
		public bool IsDataConstant { get; }

		public IEqualityComparer<T> Comparer { get; }
	}
}
