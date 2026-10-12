using System;
using System.Collections.Generic;
using System.Reactive.Concurrency;
using System.Reactive.Linq;
using System.Reactive.Subjects;
using System.Threading;
using System.Threading.Tasks;
using Uno.Extensions;
using Uno.Threading;

namespace Nventive.Persistence
{
	/// <summary>
	/// A decorator for <see cref="IDataPersister{TEntity}"/> which adds ability to observe the "current" value through an <seealso cref="IObservable{T}"/> sequence.
	/// </summary>
	/// <remarks>
	/// IMPORTANT: The value `default(T)` will be observed when the state is empty.
	/// </remarks>
	public class ObservableDataPersisterDecorator<T> : IObservableDataPersister<T>
	{
		private readonly TimeSpan? _pollingInterval;
		private readonly IDataPersister<T> _inner;
		private readonly IScheduler _replayScheduler;

		private readonly FastAsyncLock _updateGate = new FastAsyncLock();
		private readonly Subject<DataReaderLoadResult<T>> _update = new Subject<DataReaderLoadResult<T>>();
		private readonly IObservable<DataReaderLoadResult<T>> _observe;
		private readonly IObservable<DataReaderLoadResult<T>> _getAndObserve;

		/// <summary>
		/// Creates a ObservableDataPersister2Decorator wrapping an IDataPersister2 which can be 
		/// an other decorator like DefaultValueDataPersister2Decorator that manages a default value
		/// </summary>
		/// <param name="inner">Decoratee</param>
		/// <param name="replayScheduler">Scheduler to use to replay the current value when using <see cref="ObservableDataPersisterDecorator{T}.GetAndObserve"/>.</param>
		/// <param name="pollingInterval">Frequency to poll the inner dataPersister for change (null=disabled)</param>
		public ObservableDataPersisterDecorator(IDataPersister<T> inner, IScheduler replayScheduler, TimeSpan? pollingInterval = null)
		{
			_pollingInterval = pollingInterval;
			if (inner is IObservableDataPersister<T>)
			{
				throw new InvalidOperationException("inner persister is already an ObservableDataPersister.");
			}

			_inner = inner.Validation().NotNull(nameof(inner));
			_replayScheduler = replayScheduler.Validation().NotNull(nameof(replayScheduler));

			_observe = BuildObserve(false);
			_getAndObserve = BuildObserve(true);
		}

		/// <inheritdoc />
		public async Task<DataReaderLoadResult<T>> Load(CancellationToken ct)
		{
			return await _inner.Load(ct);
		}

		/// <inheritdoc />
		public bool IsDataConstant { get; } = false;

		/// <inheritdoc />
		public IEqualityComparer<T> Comparer => _inner.Comparer;

		/// <inheritdoc />
		public async Task<DataPersisterUpdateResult<T>> Update(CancellationToken ct, DataPersisterUpdaterWithContext<T> updater, object correlationTag = null)
		{
			using (await _updateGate.LockAsync(ct))
			{
				var result = await _inner.Update(ct, updater, correlationTag: correlationTag);

				if (result.IsUpdated)
				{
					_update.OnNext(result.Updated);
				}

				return result;
			}
		}

		/// <inheritdoc />
		public async Task<DataPersisterUpdateResult<T>> Update(CancellationToken ct, DataPersisterAsyncUpdaterWithContext<T> asyncUpdater, object correlationTag = null)
		{
			using (await _updateGate.LockAsync(ct))
			{
				var result = await _inner.Update(ct, asyncUpdater, correlationTag: correlationTag);

				if (result.IsUpdated)
				{
					_update.OnNext(result.Updated);
				}

				return result;
			}
		}

		/// <inheritdoc />
		public IObservable<DataReaderLoadResult<T>> Observe() => _observe;

		/// <inheritdoc />
		public IObservable<DataReaderLoadResult<T>> GetAndObserve() => _getAndObserve;

		private IObservable<DataReaderLoadResult<T>> BuildObserve(bool withInitialGet)
		{
			return Observable
				.Create<DataReaderLoadResult<T>>(
					async (observer, ct) =>
					{
						DataReaderLoadResult<T> previous;
						IDisposable subscription;

						using (await _updateGate.LockAsync(ct))
						{
							if (withInitialGet)
							{
								previous = await _inner.Load(ct);
								observer.OnNext(_replayScheduler, previous);
							}
							else
							{
								previous = null;
							}

							var x = _update
								.Do(v => previous = v);

							var y = x.ObserveOn(_replayScheduler);

							var z = y.Subscribe(observer);

							// send updates to observer
							subscription = z;
						}

						while (_pollingInterval != null && !ct.IsCancellationRequested)
						{
							await Task.Delay(_pollingInterval.Value, ct);

							using (await _updateGate.LockAsync(ct))
							{
								var newValue = await _inner.Load(ct);

								if (!newValue.Equals(previous))
								{
									// Notify of new value
									observer.OnNext(_replayScheduler, newValue);
								}
								previous = newValue;
							}
						}

						return subscription;
					}
				)
				.ReplayOneRefCount(_replayScheduler);
		}
	}
}
