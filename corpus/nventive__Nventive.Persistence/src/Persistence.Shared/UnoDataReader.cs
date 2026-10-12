using System.Collections.Generic;
using System.IO;

namespace Nventive.Persistence
{
	/// <summary>
	/// Helper class for creating <see cref="IDataReader"/>
	/// </summary>
	public static class UnoDataReader
	{
		/// <summary>
		/// Create an <see cref="IDataReader"/> from a file in the application package.
		/// </summary>
		public static IDataReader<T> CreateFromPackageFile<T>(
			string filename,
			Uno.FuncAsync<Stream, T> read,
			IEqualityComparer<T> comparer = null
		)
		{
			var filePath = Folders.GetPackageFilePath(filename);

			return new FileDataReader<T>(filePath, read, fileIsUnmodifiable: true, comparer: comparer);
		}

		public static IDataReader<T> CreateFromFile<T>(
			FolderType folderType,
			string filename,
			Uno.FuncAsync<Stream, T> read,
			IEqualityComparer<T> comparer = null)
		{
			string folder = Folders.GetFolder(folderType);

			var fullFilename = Path.Combine(folder, filename);

			return new FileDataReader<T>(fullFilename, read, fileIsUnmodifiable: true, comparer: comparer);
		}
	}
}
