#if __IOS__
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Foundation;
using Microsoft.Extensions.Logging;
using Security;
using Uno.Extensions;
using Uno.Logging;
using Uno.Threading;

namespace Nventive.Persistence
{
	/// <summary>
	/// Allows saving settings in a secure storage using iOS' keychain.
	/// </summary>
	/// <remarks>You can use this service as a parameter to the <see cref="SettingsService2"/> main service.</remarks>
	public class KeychainSettingsStorage : ISettingsStorage, IDisposable
	{
		private const string AllKeysAccountName = "Internal_AllKeys_Account";
		private const string WasKeychainValidatedName = "Keychain_was_validated";
		private const string DefaultKeychainService = "_KeychainSettingsStorage_";

		private readonly ISettingsSerializer _serializer;

		private readonly FastAsyncLock _clearKeychain = new FastAsyncLock();
		private readonly string _keychainService;

		/// <summary>
		/// Creates a new <see cref="KeychainSettingsStorage"/>.
		/// </summary>
		/// <param name="serializer">A serializer for transforming values back and forth to strings.</param>
		public KeychainSettingsStorage(ISettingsSerializer serializer)
		{
			_serializer = serializer;
			_keychainService = DefaultKeychainService;
		}

		/// <summary>
		/// Creates a new <see cref="KeychainSettingsStorage"/>.
		/// </summary>
		/// <param name="serializer">A serializer for transforming values back and forth to strings.</param>
		/// <param name="keychainService">Keychain service name.</param>
		public KeychainSettingsStorage(ISettingsSerializer serializer, string keychainService)
		{
			_serializer = serializer;
			_keychainService = keychainService;
		}

		/// <inheritdoc/>
		public async Task ClearValue(CancellationToken ct, string name)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Clearing value for key '{name}'.");
			}

			await CheckConsistencyWithFileStorage(ct);

			await ClearValueWithoutValidation(ct, name);

			if (this.Log().IsEnabled(LogLevel.Information))
			{
				this.Log().Info($"Cleared value for key '{name}'.");
			}
		}

		private async Task ClearValueWithoutValidation(CancellationToken ct, string name)
		{
			using (var keys = this.ChangeKeys())
			{
				keys.Remove(name);

				var record = this.GetRecord(name);
				SecKeyChain.Remove(record);

				keys.Commit();
			}
		}

		// This public method is not part of the interface because it is very specific to KeychainSettingsStorage;
		// other implementations of the ISettingsStorage interface will not need to offer this because they did not have this bug.

		/// <summary>
		/// Update the dictionary of stored values by checking each of the keys passed in parameter
		/// Use this method to fix devices affected by bug 101331
		/// Will use a setting from a quick, non-secure persister in order to only make this check on the
		/// keychain once.
		/// </summary>
		/// <param name="possibleKeys">List of keys which may possibly be stored by the application</param>
		/// <param name="quickDataPersister">Data persister to check that SanitizeKeys is only executed once. Should be fast
		///  (to run this check quickly) and need not be secure.</param>
		public async Task SanitizeKeys(CancellationToken ct, IEnumerable<string> possibleKeys, IDataPersister<bool> quickDataPersister)
		{
			var isAlreadySanitized = await quickDataPersister.Load(ct);

			if (isAlreadySanitized.IsValuePresent)
			{
				return;
			}

			var keysInUse = GetKeysInUse(possibleKeys);

			using (var storedKeys = this.ChangeKeys())
			{
				storedKeys.SaveKeys(keysInUse.ToArray());

				await quickDataPersister.Update(ct, context => context.Commit(true));
			}
		}

		/// <summary>
		/// Out of a set of possible storage keys, return those for which there actually is a value.
		/// </summary>
		/// <param name="possibleKeys">List of all possible storage keys used by this service for the current app</param>
		/// <returns></returns>
		private IEnumerable<string> GetKeysInUse(IEnumerable<string> possibleKeys)
		{
			foreach (var key in possibleKeys)
			{
				var record = this.GetRecord(key);

				var data = SecKeyChain.QueryAsRecord(record, out var status);

				if (status == SecStatusCode.Success)
				{
					yield return key;
				}
			}
		}

		/// <inheritdoc/>
		public async Task<T> GetValue<T>(CancellationToken ct, string name)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Getting value for key '{name}'.");
			}

			await CheckConsistencyWithFileStorage(ct);

			var record = this.GetRecord(name);

			var data = SecKeyChain.QueryAsRecord(record, out var status);

			if (status == SecStatusCode.Success)
			{
				var value = this.Deserialize<T>(data.ValueData);

				if (this.Log().IsEnabled(LogLevel.Information))
				{
					this.Log().Info($"Retrieved value for key '{name}'.");
				}

				return value;
			}

			throw new KeyNotFoundException(name);
		}

		/// <inheritdoc/>
		public async Task SetValue<T>(CancellationToken ct, string name, T value)
		{
			if (this.Log().IsEnabled(LogLevel.Debug))
			{
				this.Log().Debug($"Setting value for key '{name}'.");
			}

			await CheckConsistencyWithFileStorage(ct);

			var data = this.Serialize<T>(value);

			using (var keys = this.ChangeKeys())
			{
				var record = this.GetRecord(name);

				SecKeyChain.QueryAsRecord(record, out var status);

				if (status == SecStatusCode.Success)
				{
					keys.Update(name);

					// Only fields that change must be provided. Even "SecKind" must be ignored.
					var updated = new SecRecord
					{
						ValueData = data
					};

					status = SecKeyChain.Update(record, updated);

					if (status != SecStatusCode.Success)
					{
						throw new SecurityException(status);
					}
				}
				else if (status == SecStatusCode.ItemNotFound || status == SecStatusCode.MissingEntitlement)
				{
					keys.Add(name);
					record.ValueData = data;

					status = SecKeyChain.Add(record);

					if (status != SecStatusCode.Success)
					{
						if (status == SecStatusCode.Param)
						{
							if (this.Log().IsEnabled(LogLevel.Error))
							{
								this.Log().Error(
								   "Failed to save to the iOS KeyChain. " +
								   "Make sure an Entitlements.plist file has been provided in the Bundle Signing properties of your project."
							   );
							}
						}

						throw new SecurityException(status);
					}
				}

				keys.Commit();
			}

			if (this.Log().IsEnabled(LogLevel.Information))
			{
				this.Log().Info($"Value for key '{name}' set.");
			}
		}

		/// <inheritdoc/>
		public async Task<string[]> GetAllKeys(CancellationToken ct)
		{
			await CheckConsistencyWithFileStorage(ct);

			return await GetAllKeysWithoutValidation(ct);
		}

		/// <inheritdoc/>
		public async Task<string[]> GetAllKeysWithoutValidation(CancellationToken ct)
		{
			var record = this.GetRecord(AllKeysAccountName);

			var data = SecKeyChain.QueryAsRecord(record, out var status);

			return status == SecStatusCode.Success ? this.Deserialize<string[]>(data.ValueData) : new string[0];
		}

		/// <inheritdoc/>
		public void Dispose()
		{
			ValueChanged = null;
		}

		private SecRecord GetRecord(string name)
		{
			return new SecRecord(SecKind.GenericPassword)
			{
				Account = name,
				Label = name,
				Service = _keychainService
			};
		}

		private bool _hasConsistencyBeenChecked = false;

		public event EventHandler<string> ValueChanged;

		/// <summary>
		/// Because iOS does not guarantee the Keychain is wiped when the app is uninstalled,
		/// and we don't want inconsistencies, we wipe the keychain ourselves when we detect the
		/// app has been reinstalled
		/// </summary>
		private async Task CheckConsistencyWithFileStorage(CancellationToken ct)
		{
			if (_hasConsistencyBeenChecked == false)
			{
				using (await _clearKeychain.LockAsync(ct))
				{
					if (_hasConsistencyBeenChecked == false)
					{
						var record = GetRecord(WasKeychainValidatedName);
						SecKeyChain.QueryAsRecord(record, out var status);

						// Was the keychain ever validated before?
						if (status != SecStatusCode.Success)
						{
							// Was never validated before: this is first-time use.
							// The settings should be initialized
							record.ValueData = this.Serialize<bool>(true);
							SecKeyChain.Add(record);

							NSUserDefaults.StandardUserDefaults.SetBool(true, WasKeychainValidatedName);
						}
						else
						{
							// Was validated before: check whether the file-stored setting was wiped.
							// If so: wipe the keychain as well to maintain consistency
							if (NSUserDefaults.StandardUserDefaults[WasKeychainValidatedName] == null)
							{
								var keys = await GetAllKeysWithoutValidation(ct);
								foreach (var key in keys)
								{
									await ClearValueWithoutValidation(ct, key);
								}

								NSUserDefaults.StandardUserDefaults.SetBool(true, WasKeychainValidatedName);
							}
						}

						_hasConsistencyBeenChecked = true;
					}
				}
			}
		}

		private T Deserialize<T>(NSData data)
		{
			return (T)_serializer.FromString(NSString.FromData(data, NSStringEncoding.UTF8), typeof(T));
		}

		private NSData Serialize<T>(T value)
		{
			return NSData.FromString(
				_serializer.ToString(value, typeof(T)),
				NSStringEncoding.UTF8);
		}

		private SingleKeyOperation ChangeKeys()
		{
			var record = this.GetRecord(AllKeysAccountName);

			var data = SecKeyChain.QueryAsRecord(record, out var status);

			var keys = new string[0];

			if (status == SecStatusCode.Success)
			{
				keys = this.Deserialize<string[]>(data.ValueData);
			}
			else
			{
				record.ValueData = this.Serialize<string[]>(keys);
				SecKeyChain.Add(record);
			}

			return new SingleKeyOperation(keys, record, this);
		}

		private class SingleKeyOperation : IDisposable
		{
			private readonly string[] _originalKeys;
			private readonly SecRecord _record;
			private readonly KeychainSettingsStorage _parent;

			private string _updatedKey;

			public SingleKeyOperation(string[] keys, SecRecord record, KeychainSettingsStorage parent)
			{
				_originalKeys = keys;
				_record = record;
				_parent = parent;
			}

			public void Add(string key)
			{
				this.SetAffectedKey(key);

				var keys = _originalKeys
					.Concat(key)
					.Distinct(StringComparer.Ordinal)
					.ToArray();

				this.SaveKeys(keys);
			}

			public void Remove(string key)
			{
				this.SetAffectedKey(key);

				var keys = _originalKeys
					.Except(StringComparer.Ordinal, key)
					.ToArray();

				this.SaveKeys(keys);
			}

			public void Update(string key)
			{
				this.SetAffectedKey(key);

				// Nothing to persist.
			}

			public void Commit()
			{
				if (_updatedKey.HasValue())
				{
					_parent.ValueChanged?.Invoke(_parent, _updatedKey);

					// Simply forget about the affected key, thus nothing will happen when we get disposed.
					_updatedKey = null;
				}
			}

			public void Dispose()
			{
				if (_updatedKey.HasValue())
				{
					// Commit wasn't called.
					this.SaveKeys(_originalKeys);
				}
			}

			private void SetAffectedKey(string key)
			{
				if (_updatedKey != null)
				{
					throw new NotSupportedException("This transactional updater only supports changing one key.");
				}

				_updatedKey = key;
			}

			public void SaveKeys(string[] keys)
			{
				// Only fields that change must be provided. Even "SecKind" must be ignored.
				var newRecord = new SecRecord
				{
					ValueData = _parent.Serialize(keys)
				};

				var status = SecKeyChain.Update(_record, newRecord);
				if (status != SecStatusCode.Success)
				{
					throw new SecurityException(status);
				}
			}
		}
	}
}
#endif
