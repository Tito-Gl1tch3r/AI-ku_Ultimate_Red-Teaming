using System;
using System.Collections.Generic;
using System.IO;

namespace Nventive.Persistence
{
	/// <summary>
	/// Helper class for creating <see cref="IDataPersister{T}"/>
	/// </summary>
	public static class DataPersister
	{
		/// <summary>
		/// Helper method to create an <see cref="IDataPersister{T}"/> over a file.
		/// </summary>
		/// <param name="folderType">Type of folder where you want to open/store the file.</param>
		/// <param name="filename">Filename - can also be a relative path to the folder specified in previous parameter.</param>
		/// <param name="serializer">Serializer to use to persist & read the file content.</param>
		/// <param name="settings">The settings to use for the persister.</param>
		/// <param name="comparer">Comparer to use for handling the value</param>
		public static IDataPersister<T> CreateFromFile<T>(
			string filePath,
			Uno.FuncAsync<Stream, T> read,
			Uno.ActionAsync<T, Stream> write,
			FileDataPersisterSettings settings = null,
			IEqualityComparer<T> comparer = null)
		{
			return new LockedFileDataPersister<T>(filePath, read, write, settings: settings, comparer: comparer);
		}
	}
}
