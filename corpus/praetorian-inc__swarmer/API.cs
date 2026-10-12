using System;
using System.Runtime.InteropServices;

namespace Swarmer
{
    public static class API
    {
        // Define ORHKEY as IntPtr since it's an opaque handle
        [DllImport("Offreg.dll", SetLastError = true)]
        public static extern uint ORCreateHive(out IntPtr phkResult);

        [DllImport("Offreg.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        public static extern uint OROpenHive(string lpHivePath, out IntPtr phkResult);

        [DllImport("Offreg.dll", SetLastError = true)]
        public static extern uint ORCloseHive(IntPtr Handle);

        [DllImport("Offreg.dll", SetLastError = true)]
        public static extern uint ORCloseKey(IntPtr Handle);

        [DllImport("Offreg.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        public static extern uint ORCreateKey(
            IntPtr Handle,
            string lpSubKey,
            string lpClass,
            uint dwOptions,
            IntPtr pSecurityDescriptor,
            out IntPtr phkResult,
            out uint pdwDisposition);

        [DllImport("Offreg.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        public static extern uint OROpenKey(
            IntPtr Handle,
            string lpSubKeyName,
            out IntPtr phkResult);

        [DllImport("Offreg.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        public static extern uint ORSetValue(
            IntPtr Handle,
            string lpValueName,
            uint dwType,
            byte[] lpData,
            uint cbData);

        [DllImport("Offreg.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        public static extern uint ORSaveHive(
            IntPtr Handle,
            string lpHivePath,
            uint dwOsMajorVersion,
            uint dwOsMinorVersion);

        [DllImport("Offreg.dll", SetLastError = true)]
        public static extern void ORGetVersion(out uint pdwMajorVersion, out uint pdwMinorVersion);

        // Keep RegLoadAppKeyW for initializing the registry file - ORCreateHive doesn't work
        [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        public static extern uint RegLoadAppKeyW(
            string lpFile,
            out IntPtr phkResult,
            uint samDesired,
            uint dwOptions,
            uint dwReserved);
        // Keep RegCloseKey for closing the handle from RegLoadAppKeyW
        [DllImport("advapi32.dll", SetLastError = true)]
        public static extern uint RegCloseKey(IntPtr hKey);

        // Constants
        public const uint ERROR_SUCCESS = 0;
        public const uint REG_NONE = 0;
        public const uint REG_SZ = 1;
        public const uint REG_EXPAND_SZ = 2;
        public const uint REG_BINARY = 3;
        public const uint REG_DWORD = 4;
        public const uint REG_DWORD_BIG_ENDIAN = 5;
        public const uint REG_LINK = 6;
        public const uint REG_MULTI_SZ = 7;
        public const uint REG_QWORD = 11;
        public const uint REG_OPTION_NON_VOLATILE = 0;
        public const uint KEY_ALL_ACCESS = 0xF003F;
        public const uint REG_PROCESS_APPKEY = 0x00000001;
    }
} 