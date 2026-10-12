using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using Uno.Extensions;
using Uno.Logging;
using Uno.Threading;

namespace Nventive.Persistence
{
	public class InMemorySettingsStorage : ISettingsStorage, IDisposable
	{
		private readonly FastAsyncLock _lock = new FastAsyncLock();
		private readonly Dictionary<string, object> _values = new Dictionary<string, object>();

		/// <inheritdoc />
		public async Task ClearValue(CancellationToken ct, string name)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Clearing value for key '{name}'.");
			}

			using (await _lock.LockAsync(ct))
			{
				_values.Remove(name);
			}

			ValueChanged?.Invoke(this, name);

			if (this.Log().IsEnabled(LogLevel.Information))
			{
				this.Log().Info($"Cleared value for key '{name}'.");
			}
		}

		/// <inheritdoc />
		public async Task<T> GetValue<T>(CancellationToken ct, string name)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Getting value for key '{name}'.");
			}

			using (await _lock.LockAsync(ct))
			{
				if (_values.ContainsKey(name))
				{
					var value = (T)_values[name];

					if (this.Log().IsEnabled(LogLevel.Information))
					{
						this.Log().Info($"Retrieved value for key '{name}'.");
					}

					return value;
				}

				if (this.Log().IsEnabled(LogLevel.Information))
				{
					this.Log().Info($"Retrieved default value for key '{name}'.");
				}

				return default(T);
			}
		}

		/// <inheritdoc />
		public async Task SetValue<T>(CancellationToken ct, string name, T value)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug(() => $"Setting value for key '{name}'.");
			}

			using (await _lock.LockAsync(ct))
			{
				_values[name] = value;
			}

			if (this.Log().IsEnabled(LogLevel.Information))
			{
				this.Log().Info($"Value for key '{name}' set.");
			}

			ValueChanged?.Invoke(this, name);
		}

		/// <inheritdoc />
		public async Task<string[]> GetAllKeys(CancellationToken ct)
		{
			using (await _lock.LockAsync(ct))
			{
				return _values.Keys.ToArray();
			}
		}

		public event EventHandler<string> ValueChanged;

		/// <inheritdoc />
		public void Dispose()
		{
			ValueChanged = null;
		}
	}
}
