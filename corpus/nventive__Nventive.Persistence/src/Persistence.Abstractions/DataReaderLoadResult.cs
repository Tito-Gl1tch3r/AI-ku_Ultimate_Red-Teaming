using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.ExceptionServices;
using Uno;

namespace Nventive.Persistence
{
	/// <summary>
	/// Represent the result of a _Read_ operation.
	/// </summary>
	/// <typeparam name="T">
	/// Type of the value
	/// </typeparam>
	public class DataReaderLoadResult<T> : IEquatable<DataReaderLoadResult<T>>
	{
		private readonly T _value;
		private readonly IEqualityComparer<T> _comparer;

		/// <summary>
		/// Initialize a `DataReaderLoadResult` from a <paramref name="value"/> and custom <paramref name="isValuePresent"/>.
		/// </summary>
		public DataReaderLoadResult(IDataReader<T> provider, T value, bool isValuePresent, object correlationTag)
		{
			Provider = provider ?? throw new ArgumentNullException(nameof(provider));
			_value = value;
			IsValuePresent = isValuePresent;
			CorrelationTag = correlationTag;
			IsError = false;

			_comparer = provider.Comparer ?? EqualityComparer<T>.Default;
		}

		/// <summary>
		/// Initialize a `DataReaderLoadResult` from a <paramref name="value"/> (considered as present)
		/// </summary>
		public DataReaderLoadResult(IDataReader<T> provider, T value, object correlationTag)
		{
			Provider = provider ?? throw new ArgumentNullException(nameof(provider));
			_value = value;
			IsValuePresent = true;
			CorrelationTag = correlationTag;
			IsError = false;

			_comparer = provider.Comparer ?? EqualityComparer<T>.Default;
		}

		/// <summary>
		/// Initialize a `DataReaderLoadResult` from a captured <paramref name="exceptionInfo"/>.
		/// </summary>
		public DataReaderLoadResult(IDataReader<T> provider, ExceptionDispatchInfo exceptionInfo, object correlationTag)
		{
			Provider = provider ?? throw new ArgumentNullException(nameof(provider));
			IsError = true;
			ExceptionInfo = exceptionInfo ?? throw new ArgumentNullException(nameof(exceptionInfo));
			_value = default(T);
			IsValuePresent = false;
			CorrelationTag = correlationTag;

			_comparer = provider.Comparer ?? EqualityComparer<T>.Default;
		}

		/// <summary>
		/// Initialize a `DataReaderLoadResult` as empty (non-present value).
		/// </summary>
		public DataReaderLoadResult(IDataReader<T> provider, object correlationTag)
		{
			Provider = provider ?? throw new ArgumentNullException(nameof(provider));
			_value = default(T);
			IsValuePresent = false;
			CorrelationTag = correlationTag;
			IsError = false;

			_comparer = provider.Comparer ?? EqualityComparer<T>.Default;
		}

		/// <summary>
		/// Initialize a `DataReaderLoadResult` from another one (from another provider)
		/// </summary>
		public DataReaderLoadResult(IDataReader<T> provider, DataReaderLoadResult<T> resultToClone)
		{
			Provider = provider ?? throw new ArgumentNullException(nameof(provider));
			_value = resultToClone._value;
			IsValuePresent = resultToClone.IsValuePresent;
			CorrelationTag = resultToClone.CorrelationTag;
			ExceptionInfo = resultToClone.ExceptionInfo;
			IsError = false;

			_comparer = provider.Comparer ?? EqualityComparer<T>.Default;
		}

		/// <summary>
		/// The read value
		/// </summary>
		/// <remarks>
		/// This value should now be used if <see cref="IsValuePresent"/> is false.
		/// *IMPORTANT: WILL THROW AN EXCEPTION IF <see cref="IsError"/> is `true`*.
		/// </remarks>
		public T Value
		{
			get
			{
				RethrowExceptionOnError();
				return _value;
			}
		}

		/// <summary>
		/// _Option_ version of the value.
		/// </summary>
		/// <remarks>
		/// Will be `Option.None` when <see cref="IsValuePresent"/> is `false`.
		/// *IMPORTANT: WILL THROW AN EXCEPTION IF <see cref="IsError"/> is `true`*.
		/// </remarks>
		public Option<T> OptionValue
		{
			get
			{
				RethrowExceptionOnError();

				return IsValuePresent ? Option.Some(_value) : Option.None<T>();
			}
		}

		/// <summary>
		/// Will throw an exception if <see cref="IsError"/> is `true`.
		/// </summary>
		public void RethrowExceptionOnError()
		{
			if (IsError)
			{
				ExceptionInfo.Throw();
			}
		}

		/// <summary>
		/// Get the source <see cref="IDataReader{T}"/> for this result
		/// </summary>
		public IDataReader<T> Provider { get; }

		/// <summary>
		/// If the value exists.
		/// </summary>
		/// <remarks>
		/// `False` means the _container_ doesn't exists.
		/// By example, for a file would mean the file doesn't exist on disk.
		/// </remarks>
		public bool IsValuePresent { get; }

		/// <summary>
		/// _DispatchInfo_ of the exception.  Used to rethrow the exception.
		/// </summary>
		/// <remarks>
		/// This is for persister/decorator implementation, should not be used
		/// from application code.
		/// </remarks>
		[EditorBrowsable(EditorBrowsableState.Advanced)]
		public ExceptionDispatchInfo ExceptionInfo { get; }

		/// <summary>
		/// This is the exception caught, if any
		/// </summary>
		public Exception Exception => ExceptionInfo?.SourceException;

		/// <summary>
		/// If the result of the read operation is an error (exception).
		/// </summary>
		public bool IsError { get; }

		/// <summary>
		/// Application-specific correlation tag for the READ/CURRENT value.
		/// </summary>
		/// <remarks>
		/// Best-effort on DataPersister to correlate values with updates.
		/// This data is not expected to be persisted/serialized and is runtime only.
		/// </remarks>
		public object CorrelationTag { get; protected set; }

		/// <summary>
		/// Get the value, with a fallback to a default value when non-present.
		/// *IMPORTANT: WILL THROW AN EXCEPTION IF `IsError` is `true`*.
		/// </summary>
		/// <param name="defaultValue">Custom default value</param>
		/// <returns></returns>
		public T GetValueOrDefault(T defaultValue = default(T))
		{
			RethrowExceptionOnError();
			return IsValuePresent ? Value : defaultValue;
		}

		internal int GetDataLoadResultHashCode()
		{
			if (IsValuePresent)
			{
				return Value?.GetHashCode() ?? 0;
			}
			if (IsError)
			{
				return Exception?.GetHashCode() ?? 0;
			}
			return 0;
		}

		/// <inheritdoc />
		public override string ToString()
		{
			if (IsValuePresent)
			{
				return OptionValue?.ToString() ?? "<null>";
			}
			if (IsError)
			{
				return $"Exception:{Exception.Message}";
			}
			return "--no value present--";
		}

		/// <inheritdoc />
		public bool Equals(DataReaderLoadResult<T> other)
		{
			if (ReferenceEquals(null, other))
			{
				return false;
			}
			if (ReferenceEquals(this, other))
			{
				return true;
			}

			return (!IsValuePresent || _comparer.Equals(_value, other._value))
				&& IsValuePresent == other.IsValuePresent
				&& IsError == other.IsError;
		}

		/// <inheritdoc />
		public override bool Equals(object obj)
		{
			return Equals(obj as DataReaderLoadResult<T>);
		}

		/// <inheritdoc />
		public override int GetHashCode()
		{
			unchecked
			{
				var hashCode = IsValuePresent ? _comparer.GetHashCode(_value) : -1;
				hashCode = ExceptionInfo != null ? hashCode * 397 ^ ExceptionInfo.SourceException.GetHashCode() : hashCode;
				return hashCode;
			}
		}
	}
}
