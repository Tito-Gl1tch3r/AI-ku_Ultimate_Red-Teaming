#if __ANDROID__
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Java.Security;
using Javax.Crypto;
using Microsoft.Extensions.Logging;
using Uno.Extensions;
using Uno.Logging;
using Uno.Threading;

namespace Nventive.Persistence
{
	/// <summary>
	/// Allows saving settings in a secure storage using Android's <see cref="KeyStore"/>.
	/// </summary>
	/// <remarks>You can use this service as a parameter to the <see cref="SettingsService2"/> main service.</remarks>
	public class KeyStoreSettingsStorage : ISettingsStorage, IDisposable
	{
		// It is not an issue if this password becomes public, as it's simply added encryption
		// above the app-level encryption.
		private const string DefaultPrivatePassword = "95407C28724B42F78A035C55987FDB21C7C2CB53529148B5A3021B715447E593";
		private const string DefaultFileName = "KeyStoreSettingsStorage";

		private readonly ISettingsSerializer _serializer;
		private readonly string _fileName;
		private readonly char[] _rootPassword;
		private readonly KeyStore.PasswordProtection _protection;

		private Lazy<KeyStore> _keyStoreSelector;

		// When changing and saving the KeyStore, we must protect parallel changes.
		private readonly FastAsyncLock _changeKeyStoreLock = new FastAsyncLock();

		private static readonly Encoding _utf8 = new UTF8Encoding(false);

		/// <summary>
		/// Creates a new <see cref="KeyStoreSettingsStorage"/> using a specific filename as the destination storage.
		/// </summary>
		/// <param name="serializer">A serializer for transforming values back and forth to strings.</param>
		/// <param name="fileName">The destination file for the encypted data.</param>
		/// <param name="rootPassword">A password added above the OS-level encryption.</param>
		public KeyStoreSettingsStorage(ISettingsSerializer serializer, string fileName, string rootPassword = DefaultPrivatePassword)
		{
			_serializer = serializer;
			_fileName = fileName;
			_rootPassword = rootPassword.ToCharArray();
			_protection = new KeyStore.PasswordProtection(_rootPassword);

			SetUpKeyStoreSelector();
		}

		/// <summary>
		/// Creates a new <see cref="KeyStoreSettingsStorage"/> using the context's default file storage location.
		/// </summary>
		/// <param name="serializer">A serializer for transforming values back and forth to strings.</param>
		/// <param name="context">The Android application context.</param>
		/// <param name="rootPassword">A password added above the OS-level encryption.</param>
		public KeyStoreSettingsStorage(ISettingsSerializer serializer, Android.Content.Context context, string rootPassword = DefaultPrivatePassword)
			: this(serializer, context.GetFileStreamPath(DefaultPrivatePassword).AbsolutePath, rootPassword)
		{
		}

		/// <inheritdoc />
		public async Task ClearValue(CancellationToken ct, string name)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Clearing value for key '{name}'.");
			}

			var keyStore = _keyStoreSelector.Value;

			using (await _changeKeyStoreLock.LockAsync(ct))
			{
				keyStore.DeleteEntry(name);
				SaveKeyStore(keyStore);
			}

			ValueChanged?.Invoke(this, name);

			if (this.Log().IsEnabled(LogLevel.Information))
			{
				this.Log().Info($"Cleared value for key '{name}'.");
			}
		}

		/// <inheritdoc />
		public async Task<string[]> GetAllKeys(CancellationToken ct)
		{
			var aliases = _keyStoreSelector.Value.Aliases();

			var result = new List<string>();

			while (aliases.HasMoreElements)
			{
				var item = aliases.NextElement().ToString();
				result.Add(item);
			}

			return result.ToArray();
		}

		/// <inheritdoc />
		public async Task<T> GetValue<T>(CancellationToken ct, string name)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Getting value for key '{name}'.");
			}

			var entry = _keyStoreSelector.Value.GetEntry(name, _protection) as KeyStore.SecretKeyEntry;

			if (entry == null)
			{
				throw new KeyNotFoundException(name);
			}

			var bytes = entry.SecretKey.GetEncoded();
			var value = (T)_serializer.FromString(_utf8.GetString(bytes), typeof(T));

			if (this.Log().IsEnabled(LogLevel.Information))
			{
				this.Log().Info($"Retrieved value for key '{name}'.");
			}

			return value;
		}

		public event EventHandler<string> ValueChanged;

		/// <inheritdoc />
		public async Task SetValue<T>(CancellationToken ct, string name, T value)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Setting value for key '{name}'.");
			}

			var secret = new SecretKey(_serializer.ToString(value, typeof(T)));
			var entry = new KeyStore.SecretKeyEntry(secret);
			var keyStore = _keyStoreSelector.Value;

			using (await _changeKeyStoreLock.LockAsync(ct))
			{
				keyStore.SetEntry(name, entry, _protection);
				SaveKeyStore(keyStore);
			}

			ValueChanged?.Invoke(this, name);

			if (this.Log().IsEnabled(LogLevel.Information))
			{
				this.Log().Info($"Value for key '{name}' set.");
			}
		}

		/// <inheritdoc />
		public void Dispose()
		{
			ValueChanged = null;
		}

		private void SetUpKeyStoreSelector()
		{
			_keyStoreSelector = new Lazy<KeyStore>(LoadKeyStore);
		}

		private KeyStore LoadKeyStore()
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Loading keystore.");
			}

			var keyStore = KeyStore.GetInstance(KeyStore.DefaultType);

			try
			{
				if (System.IO.File.Exists(_fileName))
				{
					if (this.Log().IsEnabled(LogLevel.Debug))
					{
						this.Log().Debug($"Keystore file exists. Loading it.");
					}

					using (var stream = System.IO.File.OpenRead(_fileName))
					{
						keyStore.Load(stream, _rootPassword);
					}
				}
				else
				{
					if (this.Log().IsEnabled(LogLevel.Debug))
					{
						this.Log().Debug($"Keystore file doesn't exist. Loading an empty store.");
					}

					keyStore.Load(null, _rootPassword);
				}
			}
			catch (Exception error)
			{
				if (this.Log().IsEnabled(LogLevel.Error))
				{
					this.Log().Error("Could not load keystore file. Loading an empty store.", error);
				}

				keyStore.Load(null, _rootPassword);
			}

			if (this.Log().IsEnabled(LogLevel.Information))
			{
				this.Log().Info($"Keystore loaded.");
			}

			return keyStore;
		}

		private void SaveKeyStore(KeyStore keyStore)
		{
			using (var stream = System.IO.File.OpenWrite(_fileName))
			{
				keyStore.Store(stream, _rootPassword);
			}
		}

		private class SecretKey : Java.Lang.Object, ISecretKey
		{
			private readonly string _data;

			public SecretKey(string data)
			{
				_data = data;
			}

			public string Algorithm => "RAW";

			public string Format => "RAW";

			public byte[] GetEncoded()
			{
				return _utf8.GetBytes(_data);
			}
		}
	}
}
#endif
