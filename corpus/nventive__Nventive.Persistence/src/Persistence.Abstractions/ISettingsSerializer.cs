using System;
using System.Collections.Generic;
using System.Text;

namespace Nventive.Persistence
{
	public interface ISettingsSerializer
	{
		/// <summary>
		/// Creates a serialized representation of an object.
		/// </summary>
		/// <param name="value">The object to serialize.</param>
		/// <param name="valueType">The type to use to serialize the object. <paramref name="value"/> must be convertible to this type.</param>
		/// <returns>The serialized representation of <paramref name="value"/>.</returns>
		string ToString(object value, Type valueType);

		/// <summary>
		/// Creates an instance of <paramref name="targetType"/> from a serialized representation.
		/// </summary>
		/// <param name="source">A serialized representation of a <paramref name="targetType"/>.</param>
		/// <param name="targetType">The type to use to deserialize the <paramref name="source"/>.</param>
		/// <returns>The instance of <paramref name="targetType"/> deserialized from the <see cref="source"/>.</returns>
		object FromString(string source, Type targetType);
	}
}
