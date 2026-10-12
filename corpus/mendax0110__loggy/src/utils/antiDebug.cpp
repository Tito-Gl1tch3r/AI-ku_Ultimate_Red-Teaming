#include "../../include/antiDebug.h"

/**
 * @brief This method will return the method of checking if a debugger is present, depening on the OS.
 * @return true, if a debugger is present.
 * @return false, if a debugger is not present.
 */
bool AntiDebug::isDebuggerPresent()
{
#if defined(__WIN32) || defined(_WIN64)
    return IsDebuggerPresent();
#endif
#if defined(__linux__)
    return ptrace(PTRACE_TRACEME, 0, 1, 0) == -1;
#endif
#if defined(__APPLE__)
    return checkDebuggerPresence();
#endif

    return false;
}

/**
 * @brief This method will check if a debugger is present on MacOS.
 * @return true, if a debugger is present.
 * @return false, if a debugger is not present.
 */
bool AntiDebug::checkDebuggerPresence()
{
#if defined(__APPLE__)
    int mib[4];
    struct kinfo_proc info;
    size_t size = sizeof(info);

    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PID;
    mib[3] = getpid();

    if (sysctl(mib, 4, &info, &size, NULL, 0) == 0)
    {
        if ((info.kp_proc.p_flag & P_TRACED) != 0 || info.kp_eproc.e_ppid == 1)
        {
            return true; 
        }
    }
    else
    {
        return false;
    }
#endif
    return false;
}

/**
 * @brief This method will check for hardware breakpoints on Windows.
 * @return true, if hardware breakpoints are present.
 * @return false, if hardware breakpoints are not present.
 */
bool AntiDebug::checkForHardwareBreakpointsWindows()
{
#if defined(__WIN32) || defined(_WIN64)
    CONTEXT context;
    memset(&context, 0, sizeof(CONTEXT));
    context.ContextFlags = CONTEXT_DEBUG_REGISTERS;

    if (GetThreadContext(GetCurrentThread(), &context))
    {
        if ((context.Dr0 != 0) || (context.Dr1 != 0) || (context.Dr2 != 0) || (context.Dr3 != 0))
        {
            return true;
        }
    }
    return false;
#endif
    return false;
}

/**
 * @brief This method will check for hardware breakpoints on MacOS.
 * @return true, if hardware breakpoints are present.
 * @return false, if hardware breakpoints are not present.
 */
bool AntiDebug::checkForHardwareBreakpointsMacOs()
{
#if defined(__APPLE__)
    auto info = kinfo_proc{};
    auto mib = (int[]){CTL_KERN, KERN_PROC, KERN_PROC_PID, getpid()};
    size_t size = sizeof(info);

    if (sysctl(mib, sizeof(mib) / sizeof(*mib), &info, &size, nullptr, 0) == 0)
    {
        return (info.kp_proc.p_flag & P_TRACED) != 0;
    }
    else
    {
        return false;
    }
#endif
    return false;
}

/**
 * @brief This method will check for hardware breakpoints on Linux.
 * @return true, if hardware breakpoints are present.
 * @return false, if hardware breakpoints are not present.
 */
bool AntiDebug::checkForHardwareBreakpointsLinux()
{
#if defined(__linux__)
    struct user_regs_struct regs;
    ptrace(PTRACE_GETREGS, getpid(), nullptr, &regs);

    if (regs.u_debugreg[0] || regs.u_debugreg[1] || regs.u_debugreg[2] || regs.u_debugreg[3])
    {
        return true;
    }
    else
    {
        return false;
    }
#endif
    return false;
}

/**
 * @brief This method will check for hardware breakpoints, depending on the OS.
 * @return true, if hardware breakpoints are present.
 * @return false, if hardware breakpoints are not present.
 */
bool AntiDebug::checkForHardwareBreakpoints()
{
#if defined(_WIN32) || defined(_WIN64)
    return checkForHardwareBreakpointsWindows();
#elif defined(__APPLE__)
    return checkForHardwareBreakpointsMacOs();
#elif defined(__linux__)
    return checkForHardwareBreakpointsLinux();
#else
    return false;
#endif
    return false;
}