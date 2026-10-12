using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Uno.Threading;

namespace Nventive.Persistence
{
	/// <summary>
	/// The <see cref="SimpleMigrationDataPersister{TLegacy, TCurrent}"/> is an implementation of <see cref="IDataPersister{TCurrent}"/>
	/// that allows to migrate persisted data from a legacy data structure to an updated data structure.
	/// </summary>
	/// <typeparam name="TLegacy">The legacy data structure.</typeparam>
	/// <typeparam name="TCurrent">The updated data structure.</typeparam>
	public class SimpleMigrationDataPersister<TLegacy, TCurrent> : IDataPersister<TCurrent>
	{
		private readonly FastAsyncLock _lock = new FastAsyncLock();

		private readonly Func<IDataPersister<TLegacy>> _legacyPersister;
		private readonly Func<IDataPersister<TCurrent>> _currentPersister;
		private readonly Func<TLegacy, TCurrent> _migrator;
		private readonly Action<DataPersisterTransactionContext<TLegacy>> _postMigrationAction;

		private bool _hasMigrated;

		/// <summary>
		/// The <see cref="SimpleMigrationDataPersister{TLegacy, TCurrent}"/> constructor.
		/// </summary>
		/// <param name="legacyDataPersister">A <see cref="IDataPersister{TLegacy}"/> capable of reading the legacy data structure.</param>
		/// <param name="currentDataPersister">A <see cref="IDataPersister{TCurrent}"/> capable of persisting the updated data structure.</param>
		/// <param name="migrator">A method capable of migrating from the old data structure to the updated data structure.</param>
		/// <param name="postMigrationAction">
		/// An optional action that will be executed after the data is migrated, on the legacy data persister.
		/// If the postMigrationAction is not provided, <see cref="DataPersisterTransactionContext{TLegacy}"/>.RemoveAndCommit() will be executed after the migration has occurred.
		/// </param>
		public SimpleMigrationDataPersister(
			Func<IDataPersister<TLegacy>> legacyDataPersister,
			Func<IDataPersister<TCurrent>> currentDataPersister,
			Func<TLegacy, TCurrent> migrator,
			Action<DataPersisterTransactionContext<TLegacy>> postMigrationAction = null
		)
		{
			_legacyPersister = legacyDataPersister;
			_currentPersister = currentDataPersister;
			_migrator = migrator;

			_postMigrationAction = postMigrationAction ?? (context => context.RemoveAndCommit());
		}

		public bool IsDataConstant => false;

		public IEqualityComparer<TCurrent> Comparer => _currentPersister().Comparer;

		public async Task<DataReaderLoadResult<TCurrent>> Load(CancellationToken ct)
		{
			using (await _lock.LockAsync(ct))
			{
				if (!_hasMigrated)
				{
					await LoadMigrated(ct);
				}

				return await _currentPersister().Load(ct);
			}
		}

		public async Task<DataPersisterUpdateResult<TCurrent>> Update(CancellationToken ct, DataPersisterUpdaterWithContext<TCurrent> updater, object correlationTag = null)
		{
			using (await _lock.LockAsync(ct))
			{
				if (!_hasMigrated)
				{
					await LoadMigrated(ct);
				}

				return await _currentPersister().Update(ct, updater, correlationTag);
			}
		}

		public async Task<DataPersisterUpdateResult<TCurrent>> Update(CancellationToken ct, DataPersisterAsyncUpdaterWithContext<TCurrent> asyncUpdater, object correlationTag = null)
		{
			using (await _lock.LockAsync(ct))
			{
				if (!_hasMigrated)
				{
					await LoadMigrated(ct);
				}

				return await _currentPersister().Update(ct, asyncUpdater, correlationTag);
			}
		}

		/// <summary>
		/// This method is only be executed once.
		/// If the legacy data persister does not harvest a value, nothing happens, regardless of the current data persister's value.
		/// If legacy has a value :
		/// - If the current data persister does not have a value, the legacy value is migrated to the current data persister, and the legacy value is destroyed.
		/// - If the current data persister has a value, the legacy value is destroyed.
		/// </summary>
		private async Task LoadMigrated(CancellationToken ct)
		{
			var currentResult = await _currentPersister().Load(ct);
			var legacyResult = await _legacyPersister().Load(ct);

			if (!currentResult.IsValuePresent && legacyResult.IsValuePresent)
			{
				// Migrates the legacy value.
				var currentValue = _migrator(legacyResult.Value);

				// Updates the current persister with the migrated value
				await _currentPersister().Update(ct, context => context.Commit(currentValue));
			}

			if (legacyResult.IsValuePresent)
			{
				// Execute the deletion action after we harvested what we wanted.
				await _legacyPersister().Update(ct, context => _postMigrationAction(context));
			}

			// This logic only has to execute once, so we set a gate to make sure we don't reexecute it.
			_hasMigrated = true;
		}
	}
}
