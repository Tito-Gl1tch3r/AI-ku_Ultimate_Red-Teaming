using System;
using System.Collections.Generic;
using System.IO;
using Uno.Extensions;

namespace Nventive.Persistence
{
	public static class UnoDataPersister
	{
		/// <summary>
		/// Helper method to create an <see cref="IDataPersister{T}"/> over a file with a default value using a file packaged with the app.
		/// </summary>
		/// <param name="folderType">Type of folder where you want to open/store the file.</param>
		/// <param name="filename">Filename - can also be a relative path to the folder specified in previous parameter.</param>
		/// <param name="serializer">Serializer to use to persist & read the file content.</param>
		/// <param name="settings">The settings to use for the persister.</param>
		/// <param name="comparer">Comparer to use for handling the value</param>
		public static IDataPersister<T> CreateFromPackageFile<T>(
			Uno.FuncAsync<Stream, T> read,
			Uno.ActionAsync<T, Stream> write,
			string filename,
			FolderType folderType = FolderType.BackedUpData,
			FileDataPersisterSettings settings = null,
			IEqualityComparer<T> comparer = null)
			where T : IVersionable
		{
			return new VersionableDataPersister<T>(
				innerDataPersister: CreateFromFile<T>(folderType, filename, read, write, settings: settings, comparer: comparer),
				referenceDataReader: UnoDataReader.CreateFromPackageFile<T>(filename, read, comparer: comparer));
		}

		/// <summary>
		/// Helper method to create an <see cref="IDataPersister{T}"/> over a file.
		/// </summary>
		/// <param name="folderType">Type of folder where you want to open/store the file.</param>
		/// <param name="filename">Filename - can also be a relative path to the folder specified in previous parameter.</param>
		/// <param name="serializer">Serializer to use to persist & read the file content.</param>
		/// <param name="settings">The settings to use for the persister.</param>
		/// <param name="comparer">Comparer to use for handling the value</param>
		public static IDataPersister<T> CreateFromFile<T>(
			FolderType folderType,
			string filename,
			Uno.FuncAsync<Stream, T> read,
			Uno.ActionAsync<T, Stream> write,
			FileDataPersisterSettings settings = null,
			IEqualityComparer<T> comparer = null)
		{
			filename.Validation().NotNullOrEmpty(nameof(filename));

			string folder = Folders.GetFolder(folderType);

			var fullFilename = Path.Combine(folder, filename);

			return new LockedFileDataPersister<T>(fullFilename, read, write, settings: settings, comparer: comparer);
		}
	}
}
