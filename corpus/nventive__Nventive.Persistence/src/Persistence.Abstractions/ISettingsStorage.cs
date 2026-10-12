using System;
using System.Collections.Generic;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace Nventive.Persistence
{
	/// <summary>
	/// Represents a service that can store and retrieve user settings. Normally used in 
	/// conjunction with an <see cref="ISettingsService"/>.
	/// </summary>
	public interface ISettingsStorage
	{
		/// <summary>
		/// Clears any value saved under that name, and removes that name from the existing keys.
		/// </summary>
		/// <param name="ct">A cancellation token.</param>
		/// <param name="name">The name of the value to clear.</param>
		Task ClearValue(CancellationToken ct, string name);

		/// <summary>
		/// Gets a value saved under that name. If that value does not exist, throws a <seealso cref="KeyNotFoundException"/>.
		/// </summary>
		/// <param name="ct">A cancellation token.</param>
		/// <param name="name">The name of the value to get.</param>
		Task<T> GetValue<T>(CancellationToken ct, string name);

		/// <summary>
		/// Saves a value under that name. If the value already exists, it is overwritten.
		/// </summary>
		/// <param name="name">The name of the value to save under.</param>
		/// <param name="value">The new value.</param>
		Task SetValue<T>(CancellationToken ct, string name, T value);

		/// <summary>
		/// Gets an array of all keys that currently have a value saved under their name.
		/// </summary>
		/// <param name="ct">A cancellation token.</param>
		/// <returns></returns>
		Task<string[]> GetAllKeys(CancellationToken ct);

		/// <summary>
		/// Observes if any key gets assigned a new value, or gets cleared.
		/// </summary>
		/// <returns></returns>
		event EventHandler<string> ValueChanged;
	}
}
