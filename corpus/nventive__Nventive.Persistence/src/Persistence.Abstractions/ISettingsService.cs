using System;
using System.Collections.Generic;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Uno;

namespace Nventive.Persistence
{
	/// <summary>
	/// Represents a service that can store user settings.
	/// </summary>
	public interface ISettingsService
	{
		/// <summary>
		/// Removes any settings stored under the provided key.
		/// </summary>
		/// <param name="ct">A cancellation token.</param>
		/// <param name="key">The key to clear.</param>
		/// <returns></returns>
		Task ClearValue(CancellationToken ct, string key);

		/// <summary>
		/// Gets the value stored under the provided key, calling the default selector
		/// if the key is not found.
		/// </summary>
		/// <typeparam name="TValue">The returned value type. This type must be serializable.</typeparam>
		/// <param name="ct">A cancellation token.</param>
		/// <param name="key">The key to get the value for.</param>
		/// <param name="defaultSelector">A selector for getting the default value if the key is not found.</param>
		/// <returns></returns>
		/// <remarks>When the default selector is called, this default value is not stored.</remarks>
		Task<TValue> GetValue<TValue>(CancellationToken ct, string key, FuncAsync<TValue> defaultSelector = null);

		/// <summary>
		/// Gets and observes the value for the specified key, starting with the default
		/// selector if the key is not found.
		/// </summary>
		/// <typeparam name="TValue">The returned value type. This type must be serializable.</typeparam>
		/// <param name="key">The key to get and observe the value for.</param>
		/// <param name="defaultSelector">A selector for getting the initial default value if the key is not found.</param>
		/// <returns></returns>
		/// <remarks>When the default selector is called, this default value is not stored.</remarks>
		IObservable<TValue> GetAndObserveValue<TValue>(string key, FuncAsync<TValue> defaultSelector = null);

		/// <summary>
		/// Adds or updates the value for the specified key.
		/// </summary>
		/// <typeparam name="TValue">The updated value type. This type must be serializable.</typeparam>
		/// <param name="ct">A cancellation token.</param>
		/// <param name="key">The key to save the value under.</param>
		/// <param name="value">The value to save under the provided key.</param>
		/// <returns></returns>
		Task SetValue<TValue>(CancellationToken ct, string key, TValue value);
	}
}
