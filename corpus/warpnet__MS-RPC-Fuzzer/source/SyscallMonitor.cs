// SyscallMonitor.cs - Real-time ETW monitor for MS-RPC Fuzzer canary detection.
// Replaces Process Monitor by subscribing to kernel File and Registry ETW providers
// and filtering events whose payloads contain the fuzzer canary string.
//
// Requires administrator privileges (ETW real-time trace sessions).
//
// Loaded via Add-Type in SyscallMonitor.ps1.

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

/// <summary>Represents a single kernel event whose payload contained the canary.</summary>
public class SyscallEvent
{
    public DateTime  Timestamp   { get; set; }
    public int       ProcessId   { get; set; }
    public string    ProcessName { get; set; }
    public int       ThreadId    { get; set; }
    public string    Provider    { get; set; }
    public string    Operation   { get; set; }
    public int       EventId     { get; set; }
    public string    Path        { get; set; }
    public string    UserSid      { get; set; }
    public string    UserName     { get; set; }
    public string    RpcServer     { get; set; }
    public string    RpcServerPath { get; set; }
    public string    RpcInterface  { get; set; }
    public string    RpcProcedure  { get; set; }
    public string    Endpoint      { get; set; }
    /// <summary>True when the RPC server appended an extension (e.g. ".dll") to the canary path.</summary>
    public bool      PathRewritten { get; set; }
}

/// <summary>
/// Starts an ETW real-time trace session, enables the Microsoft-Windows-Kernel-File and
/// Microsoft-Windows-Kernel-Registry providers, and captures every event whose payload
/// contains a given canary string (UTF-16 LE scan).
/// </summary>
public class SyscallMonitor : IDisposable
{
    // ──────────────────────────── constants ────────────────────────────

    private const uint  EVENT_TRACE_REAL_TIME_MODE      = 0x00000100;
    private const uint  WNODE_FLAG_TRACED_GUID           = 0x00020000;
    private const uint  PROCESS_TRACE_MODE_REAL_TIME     = 0x00000100;
    private const uint  PROCESS_TRACE_MODE_EVENT_RECORD  = 0x10000000;
    private const uint  EVENT_TRACE_CONTROL_STOP         = 1;
    private const byte  TRACE_LEVEL_VERBOSE              = 5;
    private const int   ERROR_SUCCESS                    = 0;

    // Provider GUIDs
    private static readonly Guid FileProviderGuid =
        new Guid("EDD08927-9CC4-4E65-B970-C2560FB5C289");
    private static readonly Guid RegistryProviderGuid =
        new Guid("70EB4F03-C1DE-4F73-A051-33D13D5413BD");

    // ─── EVENT_TRACE_PROPERTIES layout (x64) ──────────────────────────
    // WNODE_HEADER (48 bytes) followed by properties fields.
    // Total fixed size: 120 bytes.  Session name appended after offset 120.
    private const int ETP_WNODE_BUFFERSIZE   = 0;    // Wnode.BufferSize
    private const int ETP_WNODE_CLIENTCTX    = 40;   // Wnode.ClientContext (1 = QPC)
    private const int ETP_WNODE_FLAGS        = 44;   // Wnode.Flags
    private const int ETP_BUFFERSIZE         = 48;   // BufferSize (KB)
    private const int ETP_MINBUFFERS         = 52;
    private const int ETP_MAXBUFFERS         = 56;
    private const int ETP_LOGFILEMODE        = 64;
    private const int ETP_FLUSHTIMER         = 68;
    private const int ETP_LOGFILENAMEOFFSET  = 112;
    private const int ETP_LOGGERNAMEOFFSET   = 116;
    private const int ETP_FIXED_SIZE         = 120;

    // ─── EVENT_TRACE_LOGFILEW layout (x64) ────────────────────────────
    // Calculated from nested structs: EVENT_TRACE (88 B), TRACE_LOGFILE_HEADER (280 B).
    private const int LOGFILE_LOGGERNAME_OFFSET         = 8;
    private const int LOGFILE_PROCESSTRACEMODE_OFFSET   = 28;
    private const int LOGFILE_EVENTRECORDCALLBACK_OFFSET= 424;
    private const int LOGFILE_STRUCT_SIZE                = 448;

    // ─── EVENT_RECORD field offsets (x64) ─────────────────────────────
    private const int ER_THREADID        = 8;
    private const int ER_PROCESSID       = 12;
    private const int ER_TIMESTAMP       = 16;
    private const int ER_PROVIDERID      = 24;
    private const int ER_EVENTID         = 40;
    private const int ER_OPCODE          = 45;
    private const int ER_USERDATALENGTH  = 86;
    private const int ER_USERDATA        = 96;

    // ─── TRACE_EVENT_INFO offsets (for TDH) ───────────────────────────
    private const int TEI_TASKNAME    = 68;
    private const int TEI_OPCODENAME  = 72;

    // ──────────────────────────── P/Invoke ─────────────────────────────

    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern int StartTraceW(
        out ulong sessionHandle,
        [MarshalAs(UnmanagedType.LPWStr)] string sessionName,
        IntPtr properties);

    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern int ControlTraceW(
        ulong sessionHandle,
        [MarshalAs(UnmanagedType.LPWStr)] string sessionName,
        IntPtr properties,
        uint controlCode);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern int EnableTraceEx2(
        ulong sessionHandle,
        ref Guid providerId,
        uint controlCode,
        byte level,
        ulong matchAnyKeyword,
        ulong matchAllKeyword,
        uint timeout,
        IntPtr enableParameters);

    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern ulong OpenTraceW(IntPtr logfile);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern int ProcessTrace(
        [In] ulong[] handleArray,
        uint handleCount,
        IntPtr startTime,
        IntPtr endTime);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern int CloseTrace(ulong traceHandle);

    [DllImport("tdh.dll")]
    private static extern int TdhGetEventInformation(
        IntPtr pEvent,
        uint tdhContextCount,
        IntPtr pTdhContext,
        IntPtr pBuffer,
        ref int pBufferSize);

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    private delegate void EventRecordCallbackDelegate(IntPtr eventRecord);

    // ─── Process token / SID lookup ───────────────────────────────────

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr OpenProcess(uint dwDesiredAccess, bool bInherit, int dwProcessId);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool OpenProcessToken(IntPtr processHandle, uint desiredAccess, out IntPtr tokenHandle);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool GetTokenInformation(
        IntPtr tokenHandle, int tokenInfoClass,
        IntPtr tokenInfo, int tokenInfoLength, out int returnLength);

    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool LookupAccountSidW(
        string lpSystemName, IntPtr sid,
        StringBuilder lpName, ref int cchName,
        StringBuilder lpDomain, ref int cchDomain,
        out int peUse);

    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool ConvertSidToStringSidW(IntPtr sid, out IntPtr stringSid);

    [DllImport("kernel32.dll")]
    private static extern bool CloseHandle(IntPtr handle);

    [DllImport("kernel32.dll")]
    private static extern IntPtr LocalFree(IntPtr hMem);

    private const uint PROCESS_QUERY_LIMITED_INFORMATION = 0x1000;
    private const uint TOKEN_QUERY = 0x0008;
    private const int  TokenUser   = 1;   // TOKEN_INFORMATION_CLASS

    // ─── Human-readable event ID maps ─────────────────────────────────

    private static readonly Dictionary<int, string> FileOps = new Dictionary<int, string>
    {
        { 10, "NameCreate"  }, { 11, "NameDelete"  }, { 12, "Create"      },
        { 14, "Read"        }, { 15, "Write"       }, { 16, "SetInfo"     },
        { 17, "Rename"      }, { 18, "DirEnum"     }, { 19, "Flush"       },
        { 20, "QueryInfo"   }, { 22, "FSCTL"       }, { 23, "OpEnd"       },
        { 24, "DirNotify"   }, { 25, "DeletePath"  }, { 26, "RenamePath"  },
        { 27, "CreateNew"   }, { 30, "Close"       },
    };

    private static readonly Dictionary<int, string> RegOps = new Dictionary<int, string>
    {
        {  1, "CreateKey"      }, {  2, "OpenKey"         }, {  3, "DeleteKey"       },
        {  4, "QueryKey"       }, {  5, "SetValue"        }, {  6, "DeleteValue"     },
        {  7, "QueryValue"     }, {  8, "EnumKey"         }, {  9, "EnumValueKey"    },
        { 10, "QueryMultiVal"  }, { 11, "SetKeyInfo"      }, { 12, "Flush"           },
        { 13, "KcbCreate"      }, { 14, "KcbDelete"       }, { 15, "VirtualizeKey"   },
        { 16, "Close"          },
    };

    // ─── High-privilege SIDs that trigger alerts ────────────────────────

    private static readonly HashSet<string> HighPrivSids = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
    {
        "S-1-5-18",  // NT AUTHORITY\SYSTEM
        "S-1-5-19",  // NT AUTHORITY\LOCAL SERVICE
        "S-1-5-20",  // NT AUTHORITY\NETWORK SERVICE
    };

    // ──────────────────────────── fields ───────────────────────────────

    private readonly string  _sessionName;
    private string           _canary;
    private byte[]           _canaryBytes;          // UTF-16 LE
    private ulong            _sessionHandle;
    private ulong            _traceHandle = ulong.MaxValue;
    private Thread           _processThread;
    private EventRecordCallbackDelegate _callbackDelegate;   // prevent GC
    private readonly ConcurrentBag<SyscallEvent> _events = new ConcurrentBag<SyscallEvent>();
    private readonly ConcurrentQueue<SyscallEvent> _highPrivAlerts = new ConcurrentQueue<SyscallEvent>();
    private readonly Dictionary<int, string> _procNameCache = new Dictionary<int, string>();
    private readonly Dictionary<int, (string sid, string name)> _procUserCache =
        new Dictionary<int, (string, string)>();
    private bool             _disposed;
    private string           _startError;           // propagated to caller
    private int              _lastExportedIndex;    // tracks incremental export position

    // Call registry: maps each unique canary value → origin metadata.
    // Populated by RegisterCall() from the fuzzer before each RPC invocation.
    private readonly ConcurrentDictionary<string, (string server, string serverPath, string iface, string proc, string endpoint)> _callRegistry =
        new ConcurrentDictionary<string, (string, string, string, string, string)>();

    // ──────────────────────────── public API ───────────────────────────

    public SyscallMonitor(string sessionName = "RpcFuzzerSyscallMonitor")
    {
        _sessionName = sessionName;
    }

    /// <summary>Start capturing kernel events that contain <paramref name="canary"/>.</summary>
    public void Start(string canary)
    {
        if (string.IsNullOrEmpty(canary))
            throw new ArgumentException("Canary must not be null or empty.", nameof(canary));

        _canary      = canary;
        _canaryBytes = Encoding.Unicode.GetBytes(canary);

        // Stop any stale session left by a previous crash.
        StopExistingSession();

        // Create the real-time trace session.
        StartSession();

        // Enable kernel providers.
        Guid fileGuid = FileProviderGuid;
        Guid regGuid  = RegistryProviderGuid;
        EnableProvider(ref fileGuid);
        EnableProvider(ref regGuid);

        // Open the trace and spin up the processing thread.
        _callbackDelegate = new EventRecordCallbackDelegate(OnEventRecord);
        _startError = null;

        _processThread = new Thread(ProcessingLoop)
        {
            IsBackground = true,
            Name = "SyscallMonitor-ETW"
        };
        _processThread.Start();

        // Give the thread a moment to open the trace; check for errors.
        Thread.Sleep(500);
        if (_startError != null)
            throw new InvalidOperationException(_startError);
    }

    /// <summary>Stop the trace session and return all captured events (sorted by time).</summary>
    public SyscallEvent[] Stop()
    {
        Cleanup();
        return _events.ToArray().OrderBy(e => e.Timestamp).ToArray();
    }

    /// <summary>Snapshot of events captured so far (sorted by time).</summary>
    public SyscallEvent[] GetEvents()
    {
        return _events.ToArray().OrderBy(e => e.Timestamp).ToArray();
    }

    /// <summary>
    /// Returns only the events captured since the last call to TakeNewEvents().
    /// Used for incremental export so JSON files are updated after every RPC call.
    /// </summary>
    public SyscallEvent[] TakeNewEvents()
    {
        var all = _events.ToArray().OrderBy(e => e.Timestamp).ToArray();
        if (_lastExportedIndex >= all.Length)
            return Array.Empty<SyscallEvent>();
        var slice = new SyscallEvent[all.Length - _lastExportedIndex];
        Array.Copy(all, _lastExportedIndex, slice, 0, slice.Length);
        _lastExportedIndex = all.Length;
        return slice;
    }

    /// <summary>Discard all captured events without stopping the session.</summary>
    public void Clear()
    {
        while (_events.TryTake(out _)) { }
        _lastExportedIndex = 0;
    }

    public int EventCount => _events.Count;

    /// <summary>
    /// Register a canary value produced for a specific RPC call.  The fuzzer calls this
    /// before each Method.Invoke so that captured syscall events can be attributed back
    /// to the originating procedure.
    /// </summary>
    public void RegisterCall(string rpcServer, string rpcServerPath, string rpcInterface, string procedure, string endpoint, string canaryValue)
    {
        if (!string.IsNullOrEmpty(canaryValue))
            _callRegistry[canaryValue] = (rpcServer, rpcServerPath, rpcInterface, procedure, endpoint);
    }

    /// <summary>
    /// Drain and return all high-privilege syscall alerts queued since the last call.
    /// The fuzzer calls this after each RPC invocation for real-time console output.
    /// </summary>
    public SyscallEvent[] TakeAlerts()
    {
        var list = new List<SyscallEvent>();
        while (_highPrivAlerts.TryDequeue(out var evt))
            list.Add(evt);
        return list.ToArray();
    }

    public void Dispose()
    {
        if (!_disposed)
        {
            _disposed = true;
            Cleanup();
        }
    }

    // ──────────────────────────── session lifecycle ────────────────────

    private IntPtr AllocProperties()
    {
        int nameBytes = (_sessionName.Length + 1) * 2;
        int totalSize = ETP_FIXED_SIZE + nameBytes;
        totalSize = (totalSize + 7) & ~7;   // align to 8

        IntPtr ptr = Marshal.AllocHGlobal(totalSize);
        ZeroMem(ptr, totalSize);

        Marshal.WriteInt32(ptr, ETP_WNODE_BUFFERSIZE,  totalSize);
        Marshal.WriteInt32(ptr, ETP_WNODE_CLIENTCTX,   1);              // QPC
        Marshal.WriteInt32(ptr, ETP_WNODE_FLAGS,       (int)WNODE_FLAG_TRACED_GUID);
        Marshal.WriteInt32(ptr, ETP_LOGGERNAMEOFFSET,  ETP_FIXED_SIZE);
        Marshal.WriteInt32(ptr, ETP_LOGFILENAMEOFFSET, 0);

        return ptr;
    }

    private void StopExistingSession()
    {
        IntPtr props = AllocProperties();
        try  { ControlTraceW(0, _sessionName, props, EVENT_TRACE_CONTROL_STOP); }
        finally { Marshal.FreeHGlobal(props); }
    }

    private void StartSession()
    {
        IntPtr props = AllocProperties();
        try
        {
            Marshal.WriteInt32(props, ETP_BUFFERSIZE,   64);  // 64 KB per buffer
            Marshal.WriteInt32(props, ETP_MINBUFFERS,   8);
            Marshal.WriteInt32(props, ETP_MAXBUFFERS,   64);
            Marshal.WriteInt32(props, ETP_LOGFILEMODE,  (int)EVENT_TRACE_REAL_TIME_MODE);
            Marshal.WriteInt32(props, ETP_FLUSHTIMER,   1);   // flush every 1 s

            int rc = StartTraceW(out _sessionHandle, _sessionName, props);
            if (rc != ERROR_SUCCESS)
                throw new System.ComponentModel.Win32Exception(rc,
                    "StartTraceW failed (are you running as Administrator?)");
        }
        finally { Marshal.FreeHGlobal(props); }
    }

    private void EnableProvider(ref Guid guid)
    {
        int rc = EnableTraceEx2(
            _sessionHandle,
            ref guid,
            1,                          // EVENT_CONTROL_CODE_ENABLE_PROVIDER
            TRACE_LEVEL_VERBOSE,
            0xFFFFFFFFFFFFFFFF,         // match any keyword
            0, 0, IntPtr.Zero);

        if (rc != ERROR_SUCCESS)
            throw new System.ComponentModel.Win32Exception(rc,
                $"EnableTraceEx2 failed for provider {guid}");
    }

    // ──────────────────────────── processing thread ───────────────────

    private void ProcessingLoop()
    {
        IntPtr logfilePtr   = IntPtr.Zero;
        IntPtr sessionNamePtr = IntPtr.Zero;
        try
        {
            logfilePtr    = Marshal.AllocHGlobal(LOGFILE_STRUCT_SIZE + 64);
            sessionNamePtr = Marshal.StringToHGlobalUni(_sessionName);

            ZeroMem(logfilePtr, LOGFILE_STRUCT_SIZE + 64);

            // LoggerName
            Marshal.WriteIntPtr(logfilePtr, LOGFILE_LOGGERNAME_OFFSET, sessionNamePtr);

            // ProcessTraceMode
            Marshal.WriteInt32(logfilePtr, LOGFILE_PROCESSTRACEMODE_OFFSET,
                unchecked((int)(PROCESS_TRACE_MODE_REAL_TIME | PROCESS_TRACE_MODE_EVENT_RECORD)));

            // EventRecordCallback
            IntPtr cbPtr = Marshal.GetFunctionPointerForDelegate(_callbackDelegate);
            Marshal.WriteIntPtr(logfilePtr, LOGFILE_EVENTRECORDCALLBACK_OFFSET, cbPtr);

            _traceHandle = OpenTraceW(logfilePtr);
            if (_traceHandle == ulong.MaxValue)
            {
                int err = Marshal.GetLastWin32Error();
                _startError = $"OpenTraceW failed with Win32 error {err}";
                return;
            }

            // Blocks until CloseTrace is called from another thread.
            ProcessTrace(new ulong[] { _traceHandle }, 1, IntPtr.Zero, IntPtr.Zero);
        }
        catch (Exception ex)
        {
            _startError = ex.Message;
        }
        finally
        {
            if (sessionNamePtr != IntPtr.Zero) Marshal.FreeHGlobal(sessionNamePtr);
            if (logfilePtr     != IntPtr.Zero) Marshal.FreeHGlobal(logfilePtr);
        }
    }

    // ──────────────────────────── event callback ──────────────────────

    private void OnEventRecord(IntPtr er)
    {
        try
        {
            ushort udLen = (ushort)Marshal.ReadInt16(er, ER_USERDATALENGTH);
            IntPtr udPtr = Marshal.ReadIntPtr(er, ER_USERDATA);
            if (udLen == 0 || udPtr == IntPtr.Zero) return;

            // Read raw payload.
            byte[] ud = new byte[udLen];
            Marshal.Copy(udPtr, ud, 0, udLen);

            // Fast canary scan (UTF-16 LE).
            if (!BytesContain(ud, _canaryBytes)) return;

            // ── matched! extract metadata ──

            int    pid      = Marshal.ReadInt32(er, ER_PROCESSID);
            int    tid      = Marshal.ReadInt32(er, ER_THREADID);
            long   ts       = Marshal.ReadInt64(er, ER_TIMESTAMP);
            ushort eventId  = (ushort)Marshal.ReadInt16(er, ER_EVENTID);

            byte[] guidBuf  = new byte[16];
            Marshal.Copy(er + ER_PROVIDERID, guidBuf, 0, 16);
            Guid provider   = new Guid(guidBuf);

            string provName, opName;
            if (provider == FileProviderGuid)
            {
                provName = "File";
                if (!FileOps.TryGetValue(eventId, out opName)) opName = $"FileOp_{eventId}";
            }
            else if (provider == RegistryProviderGuid)
            {
                provName = "Registry";
                if (!RegOps.TryGetValue(eventId, out opName)) opName = $"RegOp_{eventId}";
            }
            else return;

            // Try TDH for a richer operation name.
            string tdhName = TryGetTdhOpName(er);
            if (tdhName != null) opName = tdhName;

            // Extract the Unicode string that contains the canary.
            string path = ExtractCanaryString(ud);

            var user   = ResolveProcessUser(pid);
            var origin = ResolveRpcOrigin(path);

            var evt = new SyscallEvent
            {
                Timestamp     = DateTime.FromFileTimeUtc(ts).ToLocalTime(),
                ProcessId     = pid,
                ProcessName   = ResolveProcName(pid),
                ThreadId      = tid,
                Provider      = provName,
                Operation     = opName,
                EventId       = eventId,
                Path          = path,
                UserSid       = user.sid,
                UserName      = user.name,
                RpcServer     = origin.server,
                RpcServerPath = origin.serverPath,
                RpcInterface  = origin.iface,
                RpcProcedure  = origin.proc,
                Endpoint      = origin.endpoint,
                PathRewritten = origin.stripped,
            };

            _events.Add(evt);

            // Queue an alert if the syscall ran under a high-privilege identity.
            if (user.sid != null && HighPrivSids.Contains(user.sid))
                _highPrivAlerts.Enqueue(evt);
        }
        catch { /* never throw inside ETW callback */ }
    }

    // ──────────────────────────── helpers ──────────────────────────────

    private string TryGetTdhOpName(IntPtr er)
    {
        try
        {
            int bufSize = 0;
            TdhGetEventInformation(er, 0, IntPtr.Zero, IntPtr.Zero, ref bufSize);
            if (bufSize == 0) return null;

            IntPtr buf = Marshal.AllocHGlobal(bufSize);
            try
            {
                if (TdhGetEventInformation(er, 0, IntPtr.Zero, buf, ref bufSize) != 0)
                    return null;

                int opcOff  = Marshal.ReadInt32(buf, TEI_OPCODENAME);
                int taskOff = Marshal.ReadInt32(buf, TEI_TASKNAME);

                if (opcOff  > 0) return Marshal.PtrToStringUni(buf + opcOff);
                if (taskOff > 0) return Marshal.PtrToStringUni(buf + taskOff);
                return null;
            }
            finally { Marshal.FreeHGlobal(buf); }
        }
        catch { return null; }
    }

    /// <summary>
    /// Locates the canary inside the raw payload bytes and extracts the surrounding
    /// null-terminated UTF-16 string (typically a file path or registry key).
    /// </summary>
    private string ExtractCanaryString(byte[] ud)
    {
        int pos = BytesIndexOf(ud, _canaryBytes);
        if (pos < 0) return _canary;

        // Walk backwards to the start of the UTF-16 string.
        int start = pos;
        while (start >= 2)
        {
            if (start % 2 == 0 && ud[start - 2] == 0 && ud[start - 1] == 0)
                break;
            start -= 2;
        }
        if (start % 2 != 0) start++;

        // Walk forwards to the null terminator.
        int end = pos + _canaryBytes.Length;
        while (end + 1 < ud.Length)
        {
            if (ud[end] == 0 && ud[end + 1] == 0) break;
            end += 2;
        }

        int len = end - start;
        if (len <= 0 || len > 4096) return _canary;
        return Encoding.Unicode.GetString(ud, start, len);
    }

    private string ResolveProcName(int pid)
    {
        lock (_procNameCache)
        {
            if (_procNameCache.TryGetValue(pid, out string cached))
                return cached;
        }
        string name;
        try   { name = Process.GetProcessById(pid).ProcessName + ".exe"; }
        catch { name = $"PID:{pid}"; }

        lock (_procNameCache) { _procNameCache[pid] = name; }
        return name;
    }

    /// <summary>
    /// Opens the process token for <paramref name="pid"/>, reads TOKEN_USER,
    /// converts the SID to a string and resolves DOMAIN\User via LookupAccountSid.
    /// Results are cached per PID.
    /// </summary>
    private (string sid, string name) ResolveProcessUser(int pid)
    {
        lock (_procUserCache)
        {
            if (_procUserCache.TryGetValue(pid, out var cached))
                return cached;
        }

        string sidStr  = null;
        string account = null;

        IntPtr hProc  = IntPtr.Zero;
        IntPtr hToken = IntPtr.Zero;
        IntPtr pInfo  = IntPtr.Zero;
        try
        {
            hProc = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, false, pid);
            if (hProc == IntPtr.Zero) goto done;

            if (!OpenProcessToken(hProc, TOKEN_QUERY, out hToken)) goto done;

            // First call: get required buffer size.
            GetTokenInformation(hToken, TokenUser, IntPtr.Zero, 0, out int needed);
            if (needed == 0) goto done;

            pInfo = Marshal.AllocHGlobal(needed);
            if (!GetTokenInformation(hToken, TokenUser, pInfo, needed, out _)) goto done;

            // TOKEN_USER: first field is a SID_AND_ATTRIBUTES whose first member is PSID.
            IntPtr pSid = Marshal.ReadIntPtr(pInfo);

            // SID -> string
            if (ConvertSidToStringSidW(pSid, out IntPtr pStr))
            {
                sidStr = Marshal.PtrToStringUni(pStr);
                LocalFree(pStr);
            }

            // SID -> DOMAIN\User
            int cchName   = 256;
            int cchDomain = 256;
            var sbName    = new StringBuilder(cchName);
            var sbDomain  = new StringBuilder(cchDomain);
            if (LookupAccountSidW(null, pSid, sbName, ref cchName, sbDomain, ref cchDomain, out _))
            {
                account = sbDomain.Length > 0
                    ? $"{sbDomain}\\{sbName}"
                    : sbName.ToString();
            }
        }
        catch { /* best effort */ }
        finally
        {
            if (pInfo  != IntPtr.Zero) Marshal.FreeHGlobal(pInfo);
            if (hToken != IntPtr.Zero) CloseHandle(hToken);
            if (hProc  != IntPtr.Zero) CloseHandle(hProc);
        }

        done:
        var result = (sidStr ?? "Unknown", account ?? "Unknown");
        lock (_procUserCache) { _procUserCache[pid] = result; }
        return result;
    }

    /// <summary>
    /// Finds the registered RPC call whose unique canary value appears in
    /// <paramref name="path"/>.  Returns null components if no match.
    /// Also handles the case where the RPC server appends an extension like
    /// ".dll" to our canary string — we strip known extensions from path
    /// segments and retry the match.
    /// </summary>
    private static readonly string[] _stripExtensions = { ".dll", ".exe", ".sys", ".drv" };

    private (string server, string serverPath, string iface, string proc, string endpoint, bool stripped) ResolveRpcOrigin(string path)
    {
        if (path == null) return (null, null, null, null, null, false);

        // Direct match: the registered canary is a substring of the path.
        foreach (var kvp in _callRegistry)
        {
            if (path.Contains(kvp.Key))
                return (kvp.Value.server, kvp.Value.serverPath, kvp.Value.iface, kvp.Value.proc, kvp.Value.endpoint, false);
        }

        // Retry after stripping known extensions that the RPC server may have appended.
        foreach (var ext in _stripExtensions)
        {
            if (path.IndexOf(ext, StringComparison.OrdinalIgnoreCase) < 0) continue;
            string stripped = path;
            int idx;
            while ((idx = stripped.IndexOf(ext, StringComparison.OrdinalIgnoreCase)) >= 0)
                stripped = stripped.Remove(idx, ext.Length);

            foreach (var kvp in _callRegistry)
            {
                if (stripped.Contains(kvp.Key))
                    return (kvp.Value.server, kvp.Value.serverPath, kvp.Value.iface, kvp.Value.proc, kvp.Value.endpoint, true);
            }
        }

        return (null, null, null, null, null, false);
    }

    // ──────────────────────────── byte scan ────────────────────────────

    private static bool BytesContain(byte[] haystack, byte[] needle)
        => BytesIndexOf(haystack, needle) >= 0;

    private static int BytesIndexOf(byte[] haystack, byte[] needle)
    {
        if (needle.Length == 0 || haystack.Length < needle.Length) return -1;
        int limit = haystack.Length - needle.Length;
        byte first = needle[0];
        for (int i = 0; i <= limit; i++)
        {
            if (haystack[i] != first) continue;
            bool ok = true;
            for (int j = 1; j < needle.Length; j++)
            {
                if (haystack[i + j] != needle[j]) { ok = false; break; }
            }
            if (ok) return i;
        }
        return -1;
    }

    // ──────────────────────────── cleanup ──────────────────────────────

    private void Cleanup()
    {
        if (_traceHandle != ulong.MaxValue)
        {
            CloseTrace(_traceHandle);           // unblocks ProcessTrace
            _traceHandle = ulong.MaxValue;
        }
        _processThread?.Join(5000);
        _processThread = null;

        if (_sessionHandle != 0)
        {
            StopExistingSession();
            _sessionHandle = 0;
        }
    }

    private static void ZeroMem(IntPtr ptr, int size)
    {
        byte[] z = new byte[size];
        Marshal.Copy(z, 0, ptr, size);
    }
}

/// <summary>
/// Helper to invoke RPC methods with a timeout so that hung calls do not block the fuzzer.
/// </summary>
public static class RpcInvokeHelper
{
    public static object InvokeWithTimeout(
        System.Reflection.MethodInfo method,
        object instance,
        object[] args,
        int timeoutMs)
    {
        Exception captured = null;
        object result = null;

        var thread = new Thread(() =>
        {
            try { result = method.Invoke(instance, args); }
            catch (System.Reflection.TargetInvocationException tie)
            {
                captured = tie.InnerException ?? tie;
            }
            catch (Exception ex) { captured = ex; }
        });
        thread.IsBackground = true;
        thread.Start();

        if (!thread.Join(timeoutMs))
        {
            throw new TimeoutException(
                $"RPC call to {method.Name} timed out after {timeoutMs / 1000}s");
        }

        if (captured != null)
            System.Runtime.ExceptionServices.ExceptionDispatchInfo.Capture(captured).Throw();

        return result;
    }
}
