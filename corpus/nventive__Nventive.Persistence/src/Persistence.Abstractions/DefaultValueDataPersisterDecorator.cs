using System.Collections.Generic;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace Nventive.Persistence
{
	/// <summary>
	/// Decorates a <see cref="IDataPersister{TEntity}"/> which save / returns a custom default value
	/// instead of default(<typeparamref name="T"/>) when the value is non-existent in inner persister.	
	/// </summary>
	/// <typeparam name="T">Type of of the persisted entity</typeparam>
	public class DefaultValueDataPersisterDecorator<T> : IDataPersister<T>
	{
		private readonly IDataPersister<T> _inner;
		private readonly DefaultValueDataPersisterDecoratorMode _mode;
		private readonly T _customDefaultValue;

		private readonly IEqualityComparer<T> _comparer;

		/// <summary>
		/// Creates a decorator using the same default value for both read and write operations
		/// </summary>
		public DefaultValueDataPersisterDecorator(
			IDataPersister<T> inner,
			DefaultValueDataPersisterDecoratorMode mode,
			T customDefaultValue = default(T))
		{
			_inner = inner;
			_mode = mode;
			_customDefaultValue = customDefaultValue;

			_comparer = inner.Comparer ?? EqualityComparer<T>.Default;
		}

		private bool CheckMode(DefaultValueDataPersisterDecoratorMode mode)
		{
			return (_mode & mode) == mode;
		}

		/// <inheritdoc />
		public async Task<DataReaderLoadResult<T>> Load(CancellationToken ct)
		{
			var result = await _inner.Load(ct);

			return GetLocalRead(result);
		}

		private DataReaderLoadResult<T> GetLocalRead(DataReaderLoadResult<T> result, object correlationTag = null)
		{
			// Check for error condition
			if (result.IsError && CheckMode(DefaultValueDataPersisterDecoratorMode.ReadErrorToCustomDefault))
			{
				return new DataReaderLoadResult<T>(this, _customDefaultValue, correlationTag: correlationTag);
			}

			// Check for empty condition
			if (!result.IsValuePresent && CheckMode(DefaultValueDataPersisterDecoratorMode.ReadEmptyToCustomDefault))
			{
				return new DataReaderLoadResult<T>(this, _customDefaultValue, correlationTag: correlationTag);
			}

			// Check for value present condition where condition == default(T) -- using supplied EqualityComparer, obviously
			if (CheckMode(DefaultValueDataPersisterDecoratorMode.ReadDefaultToCustomDefault) && _comparer.Equals(result.Value, default(T)))
			{
				return new DataReaderLoadResult<T>(this, _customDefaultValue, correlationTag: correlationTag);
			}

			// The original result could be used "as-is"
			return new DataReaderLoadResult<T>(this, resultToClone: result);
		}

		/// <inheritdoc />
		public async Task<DataPersisterUpdateResult<T>> Update(CancellationToken ct, DataPersisterUpdaterWithContext<T> updater, object correlationTag = null)
		{
			DataReaderLoadResult<T> localRead = null;

			var result = await _inner.Update(
				ct,
				context =>
				{
					localRead = GetLocalRead(context.Read);

					var innerContext = new DataPersisterTransactionContext<T>(localRead, context.TransactionCorrelationTag);

					updater(innerContext);

					var innerResult = new DataPersisterUpdateResult<T>(innerContext);

					if (innerResult.IsUpdated)
					{
						var optionValue = innerResult.Updated.OptionValue;
						if (optionValue.MatchNone())
						{
							context.RemoveAndCommit();
						}
						else
						{
							T value = optionValue;

							if (CheckMode(DefaultValueDataPersisterDecoratorMode.WriteCustomDefaultToEmpty) && _comparer.Equals(value, _customDefaultValue))
							{
								context.RemoveAndCommit();
							}
							else if (CheckMode(DefaultValueDataPersisterDecoratorMode.WriteDefaultToEmpty) && _comparer.Equals(value, default(T)))
							{
								context.RemoveAndCommit();
							}
							else
							{
								context.Commit(value);
							}
						}
					}
				},
				correlationTag);

			var adjustedResult = GetLocalRead(result.Updated, correlationTag);
			return new DataPersisterUpdateResult<T>(result.IsUpdated, localRead, adjustedResult);
		}

		/// <inheritdoc />
		public async Task<DataPersisterUpdateResult<T>> Update(CancellationToken ct, DataPersisterAsyncUpdaterWithContext<T> asyncUpdater, object correlationTag = null)
		{
			DataReaderLoadResult<T> localRead = null;

			var result = await _inner.Update(
				ct,
				async (ct2, context) =>
				{
					localRead = GetLocalRead(context.Read);

					var innerContext = new DataPersisterTransactionContext<T>(localRead, context.TransactionCorrelationTag);

					await asyncUpdater(ct2, innerContext);

					var innerResult = new DataPersisterUpdateResult<T>(innerContext);

					if (innerResult.IsUpdated)
					{
						var optionValue = innerResult.Updated.OptionValue;
						if (optionValue.MatchNone())
						{
							context.RemoveAndCommit();
						}
						else
						{
							T value = optionValue;

							if (CheckMode(DefaultValueDataPersisterDecoratorMode.WriteCustomDefaultToEmpty) && _comparer.Equals(value, _customDefaultValue))
							{
								context.RemoveAndCommit();
							}
							else if (CheckMode(DefaultValueDataPersisterDecoratorMode.WriteDefaultToEmpty) && _comparer.Equals(value, default(T)))
							{
								context.RemoveAndCommit();
							}
							else
							{
								context.Commit(value);
							}
						}
					}
				},
				correlationTag);

			var adjustedResult = GetLocalRead(result.Updated, correlationTag);
			return new DataPersisterUpdateResult<T>(result.IsUpdated, localRead, adjustedResult);
		}

		/// <inheritdoc />
		public bool IsDataConstant { get; } = false;

		/// <inheritdoc />
		public IEqualityComparer<T> Comparer => _inner.Comparer;
	}
}
