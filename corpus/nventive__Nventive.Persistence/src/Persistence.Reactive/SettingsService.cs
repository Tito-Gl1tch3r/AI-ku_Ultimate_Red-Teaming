using System;
using System.Collections.Generic;
using System.Reactive;
using System.Reactive.Concurrency;
using System.Reactive.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Uno;

namespace Nventive.Persistence
{
	/// <summary>
	/// Service for accessing user settings stored with an implementation of an <see cref="ISettingsStorage"/>.
	/// </summary>
	public class SettingsService : ISettingsService
	{
		private readonly ISettingsStorage _storage;
		private readonly IScheduler _backgroundScheduler;

		/// <summary>
		/// Creates a new instance of a SettingsServiceEx using a specific <see cref="ISettingsStorage"/>
		/// implementation.
		/// </summary>
		/// <param name="storage">The <see cref="ISettingsStorage"/> that will actually store the settings.</param>
		/// <param name="backgroundScheduler">A background scheduler.</param>
		public SettingsService(ISettingsStorage storage, IScheduler backgroundScheduler)
		{
			_storage = storage;
			_backgroundScheduler = backgroundScheduler;
		}

		/// <inheritdoc />
		public Task ClearValue(CancellationToken ct, string key)
		{
			return _storage.ClearValue(ct, key);
		}

		/// <inheritdoc />
		public IObservable<TValue> GetAndObserveValue<TValue>(string key, FuncAsync<TValue> defaultSelector = null)
		{
			return Observable.FromEventPattern<string>(
					h => _storage.ValueChanged += h,
					h => _storage.ValueChanged -= h
				)
				.Select(p => p.EventArgs)
				.Where(changedKey => changedKey.Equals(key, StringComparison.Ordinal))
				.Select(_ => Unit.Default)
				.StartWith(_backgroundScheduler, Unit.Default)
				.SelectManyDisposePrevious((_, ct) => this.GetValue<TValue>(ct, key, defaultSelector));
		}

		/// <inheritdoc />
		public async Task<TValue> GetValue<TValue>(CancellationToken ct, string key, FuncAsync<TValue> defaultSelector = null)
		{
			try
			{
				return await _storage.GetValue<TValue>(ct, key);
			}
			catch (KeyNotFoundException)
			{
				if (defaultSelector != null)
				{
					return await defaultSelector(ct);
				}
				else
				{
					return default(TValue);
				}
			}
		}

		/// <inheritdoc />
		public Task SetValue<TValue>(CancellationToken ct, string key, TValue value)
		{
			return _storage.SetValue<TValue>(ct, key, value);
		}
	}
}
