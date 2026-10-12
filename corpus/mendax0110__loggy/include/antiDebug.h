#include <iostream>

#if defined(__WIN32) || defined(_WIN64)
#include <windows.h>
#include <winternl.h>
#endif

#if defined(__linux__)
#include <sys/ptrace.h>
#include <sys/types.h>
#endif

#if defined(__APPLE__)
#include <sys/types.h>
#include <sys/sysctl.h>
#include <print>
#endif

class AntiDebug
{
public:

    bool isDebuggerPresent();
    bool checkDebuggerPresence();
    bool checkForHardwareBreakpointsWindows();
    bool checkForHardwareBreakpointsLinux();
    bool checkForHardwareBreakpointsMacOs();
    bool checkForHardwareBreakpoints();
};