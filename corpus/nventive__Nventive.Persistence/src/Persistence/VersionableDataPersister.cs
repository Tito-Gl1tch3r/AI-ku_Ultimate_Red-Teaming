using System;
using System.Collections.Generic;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Uno;

namespace Nventive.Persistence
{
	/// <summary>
	/// A <see cref="IDataPersister{TEntity}"/> which validate the version of the saved value, and overrides it if a newer version is available.
	/// </summary>
	public class VersionableDataPersister<T> : IDataPersister<T>
		where T : IVersionable
	{
		private readonly IDataPersister<T> _innerDataPersister;
		private readonly IDataReader<T> _referenceDataReader;
		private readonly FuncAsync<DataReaderLoadResult<T>> _loadReferenceValue;

		/// <summary>
		/// Ctor
		/// </summary>
		/// <param name="innerDataPersister">Data persister to use for normal read/write operations.</param>
		/// <param name="referenceDataReader">Data persister to use for the reference value (read only).</param>
		public VersionableDataPersister(
			IDataPersister<T> innerDataPersister,
			IDataReader<T> referenceDataReader)
		{
			_innerDataPersister = innerDataPersister;
			_referenceDataReader = referenceDataReader;

			_loadReferenceValue = referenceDataReader.IsDataConstant
				? Funcs.CreateAsyncMemoized(async ct => await referenceDataReader.Load(ct))
				: async ct => await referenceDataReader.Load(ct);
		}

		/// <inheritdoc />
		public async Task<DataReaderLoadResult<T>> Load(CancellationToken ct)
		{
			var referenceValue = await _loadReferenceValue(ct);
			var localValue = await _innerDataPersister.Load(ct);

			var useReference = ShouldUseReferenceValue(referenceValue, localValue);

			var result = useReference ? referenceValue : localValue;

			return new DataReaderLoadResult<T>(this, result); // clone it for this datapersister
		}

		/// <inheritdoc />
		public bool IsDataConstant => false;

		/// <inheritdoc />
		public IEqualityComparer<T> Comparer => _innerDataPersister.Comparer ?? _referenceDataReader.Comparer;

		/// <inheritdoc />
		public Task<DataPersisterUpdateResult<T>> Update(CancellationToken ct, DataPersisterAsyncUpdaterWithContext<T> asyncUpdater, object correlationTag = null)
		{
			return _innerDataPersister
				.Update(ct,
					async (ct2, context) =>
					{
						var referenceValue = await _loadReferenceValue(ct2);
						var useReference = ShouldUseReferenceValue(referenceValue, context.Read);

						if (useReference)
						{
							var innerContext = new DataPersisterTransactionContext<T>(referenceValue, correlationTag);
							await asyncUpdater(ct2, innerContext);

							if (innerContext.IsCommitted)
							{
								if (innerContext.IsRemoved)
								{
									context.RemoveAndCommit();
								}
								else
								{
									context.Commit(innerContext.CommittedValue);
								}
							}
						}
						else
						{
							// use context normally
							await asyncUpdater(ct2, context);
						}
					}, correlationTag);
		}

		/// <inheritdoc />
		public Task<DataPersisterUpdateResult<T>> Update(CancellationToken ct, DataPersisterUpdaterWithContext<T> updater, object correlationTag = null)
		{
			return _innerDataPersister
				.Update(ct,
					async (ct2, context) =>
					{
						var referenceValue = await _loadReferenceValue(ct2);
						var useReference = ShouldUseReferenceValue(referenceValue, context.Read);

						if (useReference)
						{
							var innerContext = new DataPersisterTransactionContext<T>(referenceValue, correlationTag);
							updater(innerContext);

							if (innerContext.IsCommitted)
							{
								if (innerContext.IsRemoved)
								{
									context.RemoveAndCommit();
								}
								else
								{
									context.Commit(innerContext.CommittedValue);
								}
							}
						}
						else
						{
							// use context normally
							updater(context);
						}
					},
					correlationTag);
		}

		private static bool ShouldUseReferenceValue(DataReaderLoadResult<T> reference, DataReaderLoadResult<T> local)
		{
			if (!reference.IsValuePresent)
			{
				return false;
			}

			if (!local.IsValuePresent || local.Value?.Version != reference.Value?.Version)
			{
				return true;
			}

			return false;
		}
	}
}
