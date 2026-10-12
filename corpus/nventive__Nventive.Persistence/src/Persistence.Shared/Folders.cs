using System;
using System.Diagnostics.Contracts;
using System.IO;

namespace Nventive.Persistence
{
	/// <summary>
	/// Helper class for getting system folders
	/// </summary>
	public static class Folders
	{
		/// <summary>
		/// Get the path to a folder where you can store data of the requested type.
		/// </summary>
		/// <returns>Path to the root of the folder on disk.</returns>
		[Pure]
		public static string GetFolder(FolderType folderType)
		{
			switch (folderType)
			{
				case FolderType.WorkingData:
					return GetWorkingDataRoot();
				case FolderType.BackedUpData:
					return GetBackupedDataRoot();
				case FolderType.Caching:
					return GetCachingRoot();
				case FolderType.Temporary:
					return GetTemporaryRoot();
				default:
					throw new InvalidOperationException("Unknown folder type " + folderType);
			}
		}

		/// <summary>
		/// Get a path where the data compiled as "Content" in the project is deployed.
		/// </summary>
		/// <remarks>
		/// For non-packaged application (like .NET/WPF), it's returning the folder of the app.
		/// YOU SHOULD TREAT THIS FOLDER AS READONLY.
		/// </remarks>
		public static string GetPackageFilePath(string filename)
		{
#if __ANDROID__
			return "file:///android_asset/" + filename;
#elif __IOS__
			var uri = new Uri(filename, UriKind.RelativeOrAbsolute);

			return Foundation.NSBundle.MainBundle
				.GetUrlForResource(Path.GetFileNameWithoutExtension(uri.LocalPath), Path.GetExtension(uri.LocalPath))
				.AbsoluteString;
#elif WINUI
			var folder = Windows.ApplicationModel.Package.Current.InstalledLocation.Path;
			return Path.Combine(folder, filename);
#elif __WASM__
			var folder = "/";
			return Path.Combine(folder, filename);
#else
			var folder = AppDomain.CurrentDomain.BaseDirectory ;
			return Path.Combine(folder, filename);
#endif
		}

		private static string GetCachingRoot()
		{
#if __ANDROID__
			var folder = Android.App.Application.Context.CacheDir.AbsolutePath;
#elif __IOS__
			string folder;
			if (UIKit.UIDevice.CurrentDevice.CheckSystemVersion(8, 0))
			{
				var url = Foundation.NSFileManager.DefaultManager.GetUrls(Foundation.NSSearchPathDirectory.CachesDirectory, Foundation.NSSearchPathDomain.User)[0];
				folder = url.Path;
			}
			else
			{
				var documents = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
				folder = Path.GetFullPath(Path.Combine(documents, "..", "Library", "Caches"));
				Directory.CreateDirectory(folder);
			}
#elif WINUI
			var folder = Windows.Storage.ApplicationData.Current.LocalCacheFolder.Path;
#else
			var folder = Path.GetTempPath();
#endif
			return folder;
		}

		private static string GetTemporaryRoot()
		{
#if __ANDROID__ || __IOS__
			var folder = Path.GetTempPath();
#elif WINUI
			var folder = Windows.Storage.ApplicationData.Current.TemporaryFolder.Path;
#else
			var folder = Path.GetTempPath();
#endif
			return folder;
		}

		private static string GetBackupedDataRoot()
		{
#if __ANDROID__
			var folder = Android.App.Application.Context.FilesDir.AbsolutePath;
#elif __IOS__
			var documents = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
			var folder = Path.GetFullPath(Path.Combine(documents, "..", "Library", "Data"));
			Directory.CreateDirectory(folder);
#elif WINUI
			var folder = Windows.Storage.ApplicationData.Current.LocalFolder.Path;
#elif __WASM__
			var folder = "/";
#else
			var folder = AppDomain.CurrentDomain.BaseDirectory;
#endif
			return folder;
		}

		private static string GetWorkingDataRoot()
		{
#if __ANDROID__
			var folder = Android.App.Application.Context.NoBackupFilesDir.AbsolutePath;
#elif __IOS__
			var documents = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
			var folder = Path.GetFullPath(Path.Combine(documents, "..", "Library", "Data"));
			Directory.CreateDirectory(folder);
#elif WINUI
			var folder = Windows.Storage.ApplicationData.Current.LocalCacheFolder.Path;
#elif __WASM__
			var folder = "/";
#else
			var folder = AppDomain.CurrentDomain.BaseDirectory;
#endif
			return folder;
		}
	}
}
