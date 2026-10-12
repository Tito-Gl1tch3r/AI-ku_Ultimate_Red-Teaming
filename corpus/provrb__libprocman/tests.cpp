/**
 * @file tests.cpp
 * @brief Main test runner for ProcessManager functionality
 */

#include <iostream> // std::cout, std::endl
#include <Windows.h> // SetConsoleColor, SetConsoleTextAttribute
#include <vector> // std::vector
#include <string> // std::string

 /**
  * @brief Test harness for ProcessManager validation
  */
class Tests {
public:
    /** @brief Initialize test runner and print header */
    Tests() {
        std::cout << "===== Running tests =====" << std::endl;
    }

    /** @brief Record a failed test and print red failure message */
    void Failed() {
        failedTestNames.push_back(currentTest);
        testsRan++;
        SetConsoleColor(FOREGROUND_RED | FOREGROUND_INTENSITY);
        std::cout << "[TEST] - " << currentTest << " FAILED" << std::endl;
        SetConsoleColor(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE);
    }

    /** @brief Record a passed test and print green success message */
    void Passed() {
        testsPassed++;
        testsRan++;
        passedTestNames.push_back(currentTest);
        SetConsoleColor(FOREGROUND_GREEN | FOREGROUND_INTENSITY);
        std::cout << "[TEST] - " << currentTest << " PASSED" << std::endl;
        SetConsoleColor(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE);
    }

    /** @brief Print test summary and reset state */
    void End() {
        SetConsoleColor(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE);
        std::cout << "===== Tests complete =====" << std::endl;

        std::cout << "\nPassed tests (" << testsPassed << "): " << std::endl << "    ";
        PrintTestNames(passedTestNames);

        std::cout << "\nFailed tests (" << failedTestNames.size() << "): " << std::endl << "    ";
        PrintTestNames(failedTestNames);

        Reset();
    }

    /** @brief Reset all test counters and stored names */
    void Reset() {
        testsPassed = 0;
        testsRan = 0;
        passedTestNames.clear();
        failedTestNames.clear();
        currentTest.clear();
    }

    /** @brief Set current test name */
    void SetTest(std::string testName) { currentTest = testName; }

    /** @brief Format and print test names with line breaks */
    void PrintTestNames(const std::vector<std::string>& testNames) {
        int i = 0;
        for ( const std::string& testName : testNames ) {
            i++;
            if ( i % 4 == 0 )
                std::cout << std::endl << "    ";
            std::cout << testName << ", ";
        }
        if ( testNames.size() == 0 )
            std::cout << "None." << std::endl;
    }

    /** @brief Print yellow warning about skipped privilege tests */
    void PrintPrivilegeWarning() {
        SetConsoleColor(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_INTENSITY);
        std::cout << "[WARNING] Skipping privilege tests - run as Administrator" << std::endl;
        SetConsoleColor(FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE);
    }

private:
    /** @brief Set console text color using Windows API */
    void SetConsoleColor(WORD color) {
        HANDLE hConsole = GetStdHandle(STD_OUTPUT_HANDLE);
        SetConsoleTextAttribute(hConsole, color);
    }

    int testsPassed = 0;
    int testsRan = 0;
    std::vector<std::string> passedTestNames;
    std::vector<std::string> failedTestNames;
    std::string currentTest;
};

#include "include/procman.hpp" // ProcessManager

/**
 * @brief Main test function for ProcessManager validation
 *
 * @return int Returns 0 on successful test execution
 *
 * @details
 * This function serves as the comprehensive test suite for the ProcessManager class.
 * It systematically verifies both basic and advanced functionality, including:
 * - Core object initialization
 * - Native function loading
 * - System call number verification
 * - Security context detection
 * - Privileged operations (when run with elevation)
 *
 * The test sequence follows this structure:
 * 1. Basic functionality tests (run in all contexts)
 * 2. Privileged operation tests (only run with admin rights)
 *
 * @section test_cases Test Cases
 *
 * @subsection basic_tests Basic Functionality
 * - ProcessManager initialization
 * - Library loading verification (ntdll)
 * - System call number validation (NtClose SSN)
 * - Anti-debugging detection
 * - Virtual machine detection
 *
 * @subsection privilege_tests Privileged Operations
 * - System token acquisition
 * - Security context elevation
 * - Trusted Installer token impersonation
 *
 * @note Privileged tests require administrator rights and will be skipped
 * with a warning message if not running elevated.
 *
 * @see ProcessManager
 * @see Tests
 */
int main() {
    Tests test; // Test class.
    
    /* Basic functionality tests for ProcessManager */
    test.SetTest("ProcessManager()");
    ProcessManager procman;
    procman.NativesLoaded() ? test.Passed() : test.Failed();

    test.SetTest("GetLoadedLib()");
    procman.GetLoadedLib("ntdll") ? test.Passed() : test.Failed();

    test.SetTest("GetFunctionAddress()");
    procman.GetSSN(procman.GetLoadedLib("ntdll"), "NtClose") == 15 ? test.Passed() : test.Failed(); // NtClose syscall number is 15 as of 2025-04

    test.SetTest("BeingDebugged()");
    procman.BeingDebugged() == false ? test.Passed() : test.Failed();

    test.SetTest("RunningInVirtualMachine()");
    procman.RunningInVirtualMachine() == false ? test.Passed() : test.Failed();

    /* Tests for ProcessManager that require Administrator */
    if ( procman.ElevatedPermissions() ) {
        test.SetTest("GetSystemToken()");
        procman.GetSystemToken() ? test.Passed() : test.Failed();

        test.SetTest("GetProcessSecurityContext() == SecurityContext::System");
        procman.GetProcessSecurityContext() == SecurityContext::System ? test.Passed() : test.Failed();

        test.SetTest("GetTrustedInstallerToken()");
        procman.GetTrustedInstallerToken() ? test.Passed() : test.Failed();

        test.SetTest("GetProcessSecurityContext() == SecurityContext::TrustedInstaller");
        procman.GetProcessSecurityContext() == SecurityContext::TrustedInstaller ? test.Passed() : test.Failed();
    }
    else
        test.PrintPrivilegeWarning();

    test.End();
    return 0;
}