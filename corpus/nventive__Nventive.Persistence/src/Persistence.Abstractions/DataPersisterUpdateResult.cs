using System;
using System.Runtime.ExceptionServices;

namespace Nventive.Persistence
{
	/// <summary>
	/// Result of a Update method call.
	/// </summary>
	public class DataPersisterUpdateResult<T>
	{
		/// <summary>
		/// If the data has been updated by the persister.
		/// </summary>
		/// <remarks>
		/// Usually mean the transaction has been committed.
		/// </remarks>
		public bool IsUpdated { get; }

		/// <summary>
		/// Get the previous read, as passed to the update code.
		/// </summary>
		public DataReaderLoadResult<T> Previous { get; }

		/// <summary>
		/// Get the updated read, as the result of the update method.
		/// </summary>
		/// <remarks>
		/// **NEVER NULL**:
		/// Will be the same as Previous if not committed by the update.
		/// </remarks>
		public DataReaderLoadResult<T> Updated { get; }

		/// <summary>Constructor to build an update result from a context</summary>
		public DataPersisterUpdateResult(DataPersisterTransactionContext<T> context)
		{
			IsUpdated = context.IsCommitted;
			Previous = context.Read;
			Updated = context.IsCommitted
				? new DataReaderLoadResult<T>(Previous.Provider, context.CommittedValue, !context.IsRemoved, context.TransactionCorrelationTag)
				: context.Read;
		}

		/// <summary>Constructor to build an update result from an error</summary>
		public DataPersisterUpdateResult(DataReaderLoadResult<T> previous, ExceptionDispatchInfo error, object correlationTag)
		{
			Previous = previous;
			IsUpdated = false;
			Updated = new DataReaderLoadResult<T>(previous.Provider, error, correlationTag);
		}

		public DataPersisterUpdateResult(bool isUpdated, DataReaderLoadResult<T> previous, DataReaderLoadResult<T> updated)
		{
			IsUpdated = isUpdated;
			Previous = previous ?? throw new ArgumentNullException(nameof(previous));
			Updated = isUpdated ? (updated ?? throw new ArgumentNullException(nameof(updated))) : Previous;
		}

		/// <inheritdoc />
		public override string ToString()
		{
			return $"{Updated}, Updated={IsUpdated}";
		}
	}
}
