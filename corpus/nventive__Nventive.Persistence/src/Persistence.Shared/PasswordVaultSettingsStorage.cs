#if __ANDROID__ || __IOS__ || WINUI
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Windows.Security.Credentials;
using Uno.Extensions;
using Uno.Logging;
using Microsoft.Extensions.Logging;

namespace Nventive.Persistence
{
	/// <summary>
	/// Allows saving settings as passwords in the <see cref="PasswordVault"/>. This service has limitations, 
	/// as no more than 10 entries can be added by a single application in the Credential Locker. Prfer the 
	/// use of <see cref="ApplicationDataContainerSecureSettingsStorage"/>.
	/// </summary>
	public class PasswordVaultSettingsStorage : ISettingsStorage, IDisposable
	{
		private readonly ISettingsSerializer _serializer;
		private readonly string _appToken;
		private readonly PasswordVault _passwordVault = new PasswordVault();

		/// <summary>
		/// Creates a new <see cref="PasswordVaultSettingsStorage"/>.
		/// </summary>
		/// <param name="serializer">A serializer for transforming values back and forth to strings.</param>
		public PasswordVaultSettingsStorage(ISettingsSerializer serializer, string appToken)
		{
			_serializer = serializer;
			_appToken = appToken;
		}

		/// <inheritdoc/>
		public async Task ClearValue(CancellationToken ct, string name)
		{
			try
			{
				if (this.Log().IsEnabled(LogLevel.Debug))
				{
					this.Log().Debug($"Clearing value for key '{name}'.");
				}

				var credential = _passwordVault
					.RetrieveAll()
					.FirstOrDefault(c => c.UserName.Equals(name, StringComparison.OrdinalIgnoreCase));

				if (credential != null)
				{
					_passwordVault.Remove(credential);
					ValueChanged?.Invoke(this, name);
				}
			}
			catch
			{
				// Any error is ignored and the value is considered "absent".
			}

			if (this.Log().IsEnabled(LogLevel.Information))
			{
				this.Log().Info($"Cleared value for key '{name}'.");
			}
		}

		/// <inheritdoc/>
		public async Task<string[]> GetAllKeys(CancellationToken ct)
		{
			return _passwordVault
				.RetrieveAll()
				.Select(c => c.UserName)
				.ToArray();
		}

		/// <inheritdoc/>
		public async Task<T> GetValue<T>(CancellationToken ct, string name)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Getting value for key '{name}'.");
			}

			var credential = _passwordVault
				.RetrieveAll()
				.FirstOrDefault(c => c.UserName.Equals(name, StringComparison.OrdinalIgnoreCase));

			if (credential == null)
			{
				if (this.Log().IsEnabled(LogLevel.Information))
				{
					this.Log().Info($"Retrieved default value for key '{name}'.");
				}

				return default(T);
			}

			credential.RetrievePassword();

			var value = (T)_serializer.FromString(credential.Password, typeof(T));

			if (this.Log().IsEnabled(LogLevel.Information))
			{
				this.Log().Info($"Retrieved value for key '{name}'.");
			}

			return value;
		}

		public event EventHandler<string> ValueChanged;

		/// <inheritdoc/>
		public async Task SetValue<T>(CancellationToken ct, string name, T value)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Setting value for key '{name}'.");
			}

			var data = _serializer.ToString(value, typeof(T));
			_passwordVault.Add(new PasswordCredential(_appToken, name, data));

			ValueChanged?.Invoke(this, name);

			if (this.Log().IsEnabled(LogLevel.Information))
			{
				this.Log().Info($"Value for key '{name}' set.");
			}
		}

		/// <inheritdoc/>
		public void Dispose()
		{
			ValueChanged = null;
		}
	}
}
#endif
