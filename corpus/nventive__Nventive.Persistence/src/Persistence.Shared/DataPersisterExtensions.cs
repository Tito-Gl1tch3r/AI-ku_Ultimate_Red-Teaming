using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace Nventive.Persistence
{
	/// <summary>
	/// Extensions over <see cref="IDataPersister{TEntity}"/>.
	/// </summary>
	public static class DataPersisterExtensions
	{
		public delegate T DataPersisterUpdater<T>(T entity);
		public delegate Task<T> DataPersisterAsyncUpdater<T>(CancellationToken ct, T entity);

		/// <summary>
		/// Atomic load + update
		/// </summary>
		/// <remarks>If the updated value is the same instance as the provided instance, nothing is committed.</remarks>
		/// <remarks>
		/// It's atomic for the process: there's a lock ensuring no concurrent operation on this instance could
		/// be done at the same time.
		/// </remarks>
		public static async Task<T> Update<T>(
			this IDataPersister<T> dataPersister,
			CancellationToken ct,
			DataPersisterUpdater<T> updater,
			T defaultValue = default(T),
			bool removeOnUpdateToDefaultValue = false,
			object correlationTag = null)
		{
			var resultContext = await dataPersister.Update(
				ct,
				context =>
				{
					var readValue = context.Read.GetValueOrDefault(defaultValue);
					var result = updater(readValue);
					if (Equals(result, readValue))
					{
						// nothing changed, no action on context
						return;
					}
					if (removeOnUpdateToDefaultValue && Equals(result, defaultValue))
					{
						// Set as removed
						context.RemoveAndCommit();
					}
					else
					{
						// Set the value and commit it
						context.Commit(result);
					}
				},
				correlationTag);

			return resultContext.Updated.GetValueOrDefault(defaultValue);
		}

		/// <summary>
		/// Atomic load + update + save
		/// </summary>
		/// <remarks>If the updated value is the same instance as the provided instance, nothing is committed.</remarks>
		/// <remarks>
		/// It's atomic for the process: there's a lock ensuring no concurrent operation on this instance could
		/// be done at the same time.
		/// </remarks>
		public static async Task<T> Update<T>(
			this IDataPersister<T> dataPersister,
			CancellationToken ct,
			DataPersisterAsyncUpdater<T> asyncUpdater,
			T defaultValue = default(T),
			bool removeOnUpdateToDefaultValue = false,
			object correlationTag = null)
		{
			var resultContext = await dataPersister.Update(
				ct,
				async (ct2, context) =>
				{
					var readValue = context.Read.GetValueOrDefault(defaultValue);
					var result = await asyncUpdater(ct2, readValue);
					if (Equals(result, readValue))
					{
						// nothing changed, no action on context
						return;
					}
					if (removeOnUpdateToDefaultValue && Equals(result, defaultValue))
					{
						// Set as removed
						context.RemoveAndCommit();
					}
					else
					{
						// Set the value and commit it
						context.Commit(result);
					}
				},
				correlationTag);

			return resultContext.Updated.GetValueOrDefault(defaultValue);
		}

		/// <summary>
		/// Decorates the given <see cref="IDataPersister{TEntity}"/> to a <see cref="IDataPersister{TEntity}"/>
		/// which replaces default value by a custom default value, following a specified mode.
		/// </summary>
		public static IDataPersister<T> DecorateWithDefaultValue<T>(
			this IDataPersister<T> persister,
			T customDefaultValue = default(T),
			DefaultValueDataPersisterDecoratorMode mode = DefaultValueDataPersisterDecoratorMode.All)
		{
			return new DefaultValueDataPersisterDecorator<T>(persister, mode, customDefaultValue);
		}
	}
}
