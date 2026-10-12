using System;
using System.Collections.Generic;
using System.Reactive.Concurrency;
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
	public sealed class MemoryObservableDataPersister<T> : IObservableDataPersister<T>, IDataPersister<T>
	{
		private readonly IScheduler _replayScheduler;
		private readonly Subject<DataReaderLoadResult<T>> _update = new Subject<DataReaderLoadResult<T>>();
		private readonly IObservable<DataReaderLoadResult<T>> _getAndObserve;

		private DataReaderLoadResult<T> _currentValue;
		private readonly FastAsyncLock _lock = new FastAsyncLock();

		/// <summary>
		/// Constructor with a starting value
		/// </summary>
		public MemoryObservableDataPersister(IScheduler replayScheduler, T value, object correlationTag = null, IEqualityComparer<T> comparer = null)
		{
			_replayScheduler = replayScheduler;

			_currentValue = new DataReaderLoadResult<T>(this, value, true, correlationTag);
			Comparer = comparer;

			_getAndObserve = BuildGetAndObserve();
		}

		/// <summary>
		/// Constructor starting with an empty state.
		/// </summary>
		public MemoryObservableDataPersister(IScheduler replayScheduler, IEqualityComparer<T> comparer = null)
		{
			_replayScheduler = replayScheduler;

			_currentValue = new DataReaderLoadResult<T>(this, correlationTag: null);
			Comparer = comparer;

			_getAndObserve = BuildGetAndObserve();
		}

		/// <inheritdoc />
		public async Task<DataReaderLoadResult<T>> Load(CancellationToken ct)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Loading memory.");
			}

			using (await _lock.LockAsync(ct)) // not very useful, but will wait any ongoing update.
			{
				if (this.Log().IsEnabled(LogLevel.Information))
				{
					this.Log().Info($"Loaded memory.");
				}

				return _currentValue;
			}
		}

		/// <inheritdoc />
		public bool IsDataConstant => false;

		/// <inheritdoc />
		public IEqualityComparer<T> Comparer { get; }

		/// <inheritdoc />
		public async Task<DataPersisterUpdateResult<T>> Update(CancellationToken ct, DataPersisterUpdaterWithContext<T> updater, object correlationTag = null)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Updating memory.");
			}

			using (await _lock.LockAsync(ct))
			{
				var context = new DataPersisterTransactionContext<T>(_currentValue, correlationTag);

				DataPersisterUpdateResult<T> result;
				try
				{
					updater(context);

					if (this.Log().IsEnabled(LogLevel.Information))
					{
						this.Log().Info($"Updated memory.");
					}

					result = new DataPersisterUpdateResult<T>(context);

					_currentValue = result.Updated;

					if (result.IsUpdated)
					{
						_update.OnNext(_replayScheduler, result.Updated);
					}
				}
				catch (Exception ex)
				{
					if (this.Log().IsEnabled(LogLevel.Error))
					{
						this.Log().Error($"Could not update memory.", ex);
					}

					var error = ExceptionDispatchInfo.Capture(ex);

					result = new DataPersisterUpdateResult<T>(_currentValue, error, correlationTag);
				}

				return result;
			}
		}

		/// <inheritdoc />
		public async Task<DataPersisterUpdateResult<T>> Update(CancellationToken ct, DataPersisterAsyncUpdaterWithContext<T> asyncUpdater, object correlationTag = null)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Updating memory.");
			}

			using (await _lock.LockAsync(ct))
			{
				var context = new DataPersisterTransactionContext<T>(_currentValue, correlationTag);

				DataPersisterUpdateResult<T> result;
				try
				{
					await asyncUpdater(ct, context);

					if (this.Log().IsEnabled(LogLevel.Information))
					{
						this.Log().Info($"Updated memory.");
					}

					result = new DataPersisterUpdateResult<T>(context);

					_currentValue = result.Updated;

					if (result.IsUpdated)
					{
						_update.OnNext(_replayScheduler, result.Updated);
					}
				}
				catch (Exception ex)
				{
					if (this.Log().IsEnabled(LogLevel.Error))
					{
						this.Log().Error($"Could not update memory.", ex);
					}

					var error = ExceptionDispatchInfo.Capture(ex);

					result = new DataPersisterUpdateResult<T>(_currentValue, error, correlationTag);
				}

				return result;
			}
		}

		/// <inheritdoc />
		public IObservable<DataReaderLoadResult<T>> Observe() => _update;

		/// <inheritdoc />
		public IObservable<DataReaderLoadResult<T>> GetAndObserve() => _getAndObserve;

		private IObservable<DataReaderLoadResult<T>> BuildGetAndObserve() =>
			Observable.Create<DataReaderLoadResult<T>>(
				async (observer, ct) =>
				{
					using (await _lock.LockAsync(ct))
					{
						observer.OnNext(_replayScheduler, _currentValue);
						return _update.Subscribe(observer);
					}
				}
			)
			.ReplayOneRefCount(_replayScheduler);
	}
}
