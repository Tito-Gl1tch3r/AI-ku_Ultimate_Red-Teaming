using System;
using System.Collections.Generic;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace Nventive.Persistence
{
	public static class DataReaderExtensions
	{
		/// <summary>
		/// Load with a fallback default value when the value doesn't exists.
		/// </summary>
		public static async Task<T> Load<T>(this IDataReader<T> reader, CancellationToken ct, T defaultValue = default(T))
		{
			var context = await reader.Load(ct);
			return context.IsValuePresent ? context.Value : defaultValue;
		}

		/// <summary>
		/// Decorates the given <see cref="IDataPersister{TEntity}"/> to a <see cref="IDataPersister{TEntity}"/> which replaces default(<typeparamref name="T"/>) by <paramref name="defaultValue"/>.
		/// </summary>
		/// <param name="reader">Underlying reader.</param>
		/// <param name="defaultValue">The default value to use when the persister consider the value as non-existent.</param>
		public static IDataReader<T> WithDefaultValue<T>(this IDataReader<T> reader, T defaultValue)
		{
			return new DefaultValueDataReaderDecorator<T>(reader, defaultValue);
		}

		/// <summary>
		/// If you want to treat any loading exception as default value, use this extension method.
		/// </summary>
		public static async Task<DataReaderLoadResult<T>> SafeLoad<T>(
			this IDataReader<T> persister,
			CancellationToken ct,
			T defaultValueOnException = default(T),
			Action<Exception> exceptionCatcher = null)
		{
			try
			{
				return await persister.Load(ct);
			}
			catch (OperationCanceledException)
			{
				throw;
			}
			catch (Exception ex)
			{
				exceptionCatcher?.Invoke(ex);

				return new DataReaderLoadResult<T>(persister, defaultValueOnException, correlationTag: null);
			}
		}

		/// <summary>
		/// If you want to treat any loading exception as default value, use this extension method.
		/// </summary>
		public static async Task<T> SafeLoadOrDefault<T>(
			this IDataReader<T> persister,
			CancellationToken ct,
			T defaultValueOnException = default(T),
			Action<Exception> exceptionCatcher = null)
		{
			try
			{
				return await Load(persister, ct);
			}
			catch (OperationCanceledException)
			{
				throw;
			}
			catch (Exception ex)
			{
				exceptionCatcher?.Invoke(ex);
				return defaultValueOnException;
			}
		}
	}
}
