using System;
using System.Collections.Generic;
using System.Linq;
using System.Reactive.Linq;
using System.Reactive.Subjects;
using System.Runtime.ExceptionServices;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using Uno.Extensions;
using Uno.Logging;
using Uno.Threading;

namespace Nventive.Persistence
{
	public sealed class SettingsStorageObservableDataPersisterAdapter<T> : IObservableDataPersister<T>, IDisposable
	{
		private readonly ISettingsStorage _storage;
		private readonly string _key;
		private readonly bool _concurrencyProtection;
		private readonly FastAsyncLock _lock = new FastAsyncLock();

		private readonly IEqualityComparer<T> _comparer;
		private readonly IDisposable _subscription;
		private readonly Subject<DataReaderLoadResult<T>> _subject = new Subject<DataReaderLoadResult<T>>();

		private DataReaderLoadResult<T> _lastValue; // store the last "read" value from storate to replay when appropriate

		public SettingsStorageObservableDataPersisterAdapter(
			ISettingsStorage storage,
			string key,
			IEqualityComparer<T> comparer = null,
			bool concurrencyProtection = true)
		{
			_storage = storage;
			_key = key;
			Comparer = comparer;
			_concurrencyProtection = concurrencyProtection;

			_comparer = comparer ?? EqualityComparer<T>.Default;

			_subscription = Observable.FromEventPattern<string>(
					h => storage.ValueChanged += h,
					h => storage.ValueChanged -= h
				)
				.Select(p => p.EventArgs)
				.Where(x => x == key)
				.SelectManyDisposePrevious(async (_, ct) => await ReadValue(ct, forceRead: true))
				.Subscribe();
		}

		/// <inheritdoc />
		public async Task<DataReaderLoadResult<T>> Load(CancellationToken ct)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Loading settings '{_key}'.");
			}

			var value = await ReadValue(ct);

			if (this.Log().IsEnabled(LogLevel.Information))
			{
				this.Log().Info($"Loaded settings '{_key}'.");
			}

			return value;
		}

		private async Task<DataReaderLoadResult<T>> ReadValue(CancellationToken ct, bool forceRead = false)
		{
			DataReaderLoadResult<T> updated = null;

			try
			{
				using (await _lock.LockAsync(ct))
				{
					updated = await InnerReadValue(ct, forceRead);
				}
			}
			catch (Exception ex)
			{
				if (this.Log().IsEnabled(LogLevel.Error))
				{
					this.Log().Error($"Could not load settings '{_key}'.", ex);
				}

				_lastValue = updated = new DataReaderLoadResult<T>(this, ExceptionDispatchInfo.Capture(ex), correlationTag: null);
			}

			if (updated != null)
			{
				_subject.OnNext(updated);
			}

			return _lastValue;
		}

		private async Task<DataReaderLoadResult<T>> InnerReadValue(CancellationToken ct, bool forceRead)
		{
			DataReaderLoadResult<T> updated = null;

			if (_lastValue != null && !forceRead)
			{
				if (this.Log().IsEnabled(LogLevel.Debug))
				{
					this.Log().Debug($"Reading settings '{_key}' using local memory.");
				}

				return updated;
			}

			var keys = await _storage.GetAllKeys(ct);

			if (keys.Contains(_key, StringComparer.OrdinalIgnoreCase))
			{
				if (this.Log().IsEnabled(LogLevel.Debug))
				{
					this.Log().Debug($"Reading settings '{_key}'.");
				}

				// key present
				var newValue = await _storage.GetValue<T>(ct, _key);

				if (_lastValue == null || !_lastValue.OptionValue.MatchSome(out var v) || !_comparer.Equals(v, newValue))
				{
					_lastValue = updated = new DataReaderLoadResult<T>(this, newValue, correlationTag: null);
				}
			}
			else
			{
				if (this.Log().IsEnabled(LogLevel.Debug))
				{
					this.Log().Debug($"No settings '{_key}' to read.");
				}

				// key absent
				if (_lastValue == null || _lastValue.IsValuePresent)
				{
					_lastValue = updated = new DataReaderLoadResult<T>(this, correlationTag: null);
				}
			}

			return updated;
		}

		/// <inheritdoc />
		public bool IsDataConstant => false;

		/// <inheritdoc />
		public IEqualityComparer<T> Comparer { get; }

		/// <inheritdoc />
		public Task<DataPersisterUpdateResult<T>> Update(
			CancellationToken ct,
			DataPersisterUpdaterWithContext<T> updater,
			object correlationTag = null)
		{
			// Route to async version, since the SettingStorage is always async anyway.
			return Update(ct, async (_, context) => updater(context), correlationTag);
		}

		/// <inheritdoc />
		public async Task<DataPersisterUpdateResult<T>> Update(
			CancellationToken ct,
			DataPersisterAsyncUpdaterWithContext<T> asyncUpdater,
			object correlationTag = null)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Updating settings '{_key}'.");
			}

			DataPersisterUpdateResult<T> result;

			while (true)
			{
				using (await _lock.LockAsync(ct))
				{
					var read = await InnerReadValue(ct, forceRead: false) ?? _lastValue;

					var context = new DataPersisterTransactionContext<T>(read, transactionCorrelationTag: correlationTag);

					try
					{
						await asyncUpdater(ct, context);

						if (_concurrencyProtection)
						{
							// ensure we have the last version from settings
							var newReadValue = await InnerReadValue(ct, forceRead: true) ?? _lastValue;

							if (!newReadValue.Equals(read))
							{
								if (this.Log().IsEnabled(LogLevel.Warning))
								{
									this.Log().Warn($"Could not update the value for type {typeof(T)} because the value read from the " +
										$"DataPersister BEFORE the update is different from the value read from the DataPersister AFTER the update. " +
										$"Either it was updated by an external source or it doesn't implement Equals properly. " +
										$"Trying again.");
								}

								continue; // Concurrency collision: the persisted value is different than previous version
							}
						}

						// Compute result
						result = new DataPersisterUpdateResult<T>(context);

						if (result.IsUpdated)
						{
							if (result.Updated.IsValuePresent)
							{
								await _storage.SetValue(ct, _key, result.Updated.Value);

								if (this.Log().IsEnabled(LogLevel.Information))
								{
									this.Log().Info($"Updated settings '{_key}'.");
								}
							}
							else
							{
								await _storage.ClearValue(ct, _key);

								if (this.Log().IsEnabled(LogLevel.Information))
								{
									this.Log().Info($"Deleted settings '{_key}'.");
								}
							}

							_lastValue = result.Updated;
						}
						else
						{
							if (this.Log().IsEnabled(LogLevel.Information))
							{
								this.Log().Info($"Updated settings '{_key}'.");
							}
						}
					}
					catch (Exception ex)
					{
						if (this.Log().IsEnabled(LogLevel.Error))
						{
							this.Log().Error($"Could not update settings '{_key}'.", ex);
						}

						result = new DataPersisterUpdateResult<T>(read, ExceptionDispatchInfo.Capture(ex), correlationTag);
					}
				}

				break;
			}

			if (result.IsUpdated)
			{
				_subject.OnNext(result.Updated);
			}

			return result;
		}

		public void Dispose()
		{
			_subscription.Dispose();
			_subject.Dispose();
		}

		public IObservable<DataReaderLoadResult<T>> Observe()
		{
			return _subject;
		}

		public IObservable<DataReaderLoadResult<T>> GetAndObserve()
		{
			return _subject.TryStartWith(ct => ReadValue(ct));
		}
	}
}
