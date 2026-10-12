using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;

namespace Simbad.Platform.Persistence.Sqlite
{
    internal static class Bootstrap
    {
        public static void LoadSqliteDll()
        {
            var assembly = Assembly.GetExecutingAssembly();
            var libraryName = GetLibraryName();

            if (libraryName == null)
            {
                return;
            }

            var path = Path.Combine(Path.GetDirectoryName(assembly.Location), libraryName);

            if (!File.Exists(path))
            {
                var resourceName = GetResourceName();
                WriteDll(path, resourceName);
            }
        }

        private static void WriteDll(string path, string resourceName)
        {
            File.WriteAllBytes(path, ExtractResource(resourceName));
        }

        private static byte[] ExtractResource(string resourceName)
        {
            using (var resFilestream = Assembly.GetExecutingAssembly().GetManifestResourceStream(resourceName))
            {
                if (resFilestream == null) return null;

                var result = new byte[resFilestream.Length];
                resFilestream.Read(result, 0, result.Length);

                return result;
            }
        }

        private static string GetLibraryName()
        {
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                return "sqlite3.dll";
            }

            return null;
        }

        private static string GetResourceName()
        {
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                var suffix = IntPtr.Size == 8 ? "x64" : "x86";
                return $"Simbad.Platform.Persistence.Sqlite.sqlite.win.{suffix}.sqlite3.dll";
            }

            return null;
        }
    }
}