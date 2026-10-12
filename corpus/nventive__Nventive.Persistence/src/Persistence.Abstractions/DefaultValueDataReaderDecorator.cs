using System;
using System.Collections.Generic;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace Nventive.Persistence
{
	/// <summary>
	/// Wrap an <see cref="IDataReader{T}"/> with a default value when the inner is empty.
	/// </summary>
	public class DefaultValueDataReaderDecorator<T> : IDataReader<T>
	{
		private readonly IDataReader<T> _inner;
		private readonly DataReaderLoadResult<T> _defaultValue;

		/// <summary>
		/// Constructor
		/// </summary>
		public DefaultValueDataReaderDecorator(IDataReader<T> inner, T defaultValue)
		{
			_inner = inner;
			_defaultValue = new DataReaderLoadResult<T>(this, defaultValue);
		}

		/// <inheritdoc />
		public async Task<DataReaderLoadResult<T>> Load(CancellationToken ct)
		{
			var result = await _inner.Load(ct);
			return result.IsValuePresent
				? new DataReaderLoadResult<T>(this, result) // clone the result for this datareader
				: _defaultValue;
		}

		/// <inheritdoc />
		public bool IsDataConstant => _inner.IsDataConstant;

		/// <inheritdoc />
		public IEqualityComparer<T> Comparer => _inner.Comparer;
	}
}
