using System;
using System.Collections.Generic;
using System.Linq;
using System.Reactive.Concurrency;

namespace Nventive.Persistence
{
	/// <summary>
	/// Extensions over <see cref="IDataPersister{TEntity}"/>.
	/// </summary>
	public static class DataPersisterExtensions
	{
		/// <summary>
		/// Decorates the given <see cref="IDataPersister{TEntity}"/> to a <see cref="ObservableDataPersisterDecorator{T}"/>.
		/// </summary>
		/// <param name="persister">Underlying persister</param>
		/// <param name="replayScheduler">Scheduler to use to replay the current value when using <see cref="ObservableDataPersisterDecorator{T}.GetAndObserve"/>.</param>
		/// <param name="pollingInterval">Frequency to poll the inner dataPersister for change (null=disabled)</param>
		public static IObservableDataPersister<T> ToObservablePersister<T>(this IDataPersister<T> persister, IScheduler replayScheduler, TimeSpan? pollingInterval = null)
		{
			return persister as IObservableDataPersister<T>
				?? new ObservableDataPersisterDecorator<T>(persister, replayScheduler, pollingInterval);
		}
	}
}
