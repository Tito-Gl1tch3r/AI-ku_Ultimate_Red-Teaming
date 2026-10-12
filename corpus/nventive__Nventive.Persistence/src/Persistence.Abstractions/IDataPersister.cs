using System;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace Nventive.Persistence
{
	/// <summary>
	/// Abstraction over the persistence of an entity ensuring transactional operations when possible.
	/// </summary>
	public interface IDataPersister<T> : IDataReader<T>
	{

		/// <summary>
		/// Atomic load + update with optional control
		/// </summary>
		/// <remarks>
		/// CONCURRENCY WARNING: Most implementations will have a lock ensuring no concurrent operation on this instance could
		/// be done at the same time, but since you can have more than one instance and/or many processes, there's no absolute
		/// protection against concurrent update.  That's why there's a retry mecanism: if a collision is detected, your updater
		/// will be called again with a more recent value.
		/// IMPORTANT: YOU MUST CALL context.Commit() or context.RemoveAndCommit() FOR THE SAVE/REMOVAL TO OCCUR.
		/// </remarks>
		/// <returns>
		/// The updated value reading context (if updated) or the currently saved value (if not updated)
		/// </returns>
		Task<DataPersisterUpdateResult<T>> Update(CancellationToken ct, DataPersisterUpdaterWithContext<T> updater, object correlationTag = null);

		/// <summary>
		/// Atomic load + update + save with optional control
		/// </summary>
		/// <remarks>
		/// CONCURRENCY WARNING: Most implementations will have a lock ensuring no concurrent operation on this instance could
		/// be done at the same time, but since you can have more than one instance and/or many processes, there's no absolute
		/// protection against concurrent update.  That's why there's a retry mecanism: if a collision is detected, your updater
		/// will be called again with a more recent value.
		/// IMPORTANT: YOU MUST CALL context.Commit() or context.RemoveAndCommit() FOR THE SAVE/REMOVAL TO OCCUR.
		/// </remarks>
		/// <returns>
		/// The updated value reading context (if updated) or the currently saved value (if not updated)
		/// </returns>
		Task<DataPersisterUpdateResult<T>> Update(CancellationToken ct, DataPersisterAsyncUpdaterWithContext<T> asyncUpdater, object correlationTag = null);
	}

	/// <summary>
	/// Callback delegate for the Update method (sync version).
	/// </summary>
	public delegate void DataPersisterUpdaterWithContext<T>(DataPersisterTransactionContext<T> transactionContext);

	/// <summary>
	/// Callback delegate for the Update method (async version).
	/// </summary>
	public delegate Task DataPersisterAsyncUpdaterWithContext<T>(CancellationToken ct, DataPersisterTransactionContext<T> transactionContext);
}
