#include <windows.h>
#include <bcrypt.h>
#include <errno.h>

extern int WINAPI WinMain(HINSTANCE, HINSTANCE, LPSTR, int);

void WinMainCRTStartup(void)
{
    int ret = WinMain(NULL, NULL, NULL, SW_SHOWDEFAULT);
    ExitProcess((UINT)ret);
}

int atexit(void (*fn)(void)) { (void)fn; return 0; }

void __main(void) {}

#include <time.h>
int getntptimeofday(struct timespec *tp, const void *tz)
{
    (void)tz;
    if (tp) {
        FILETIME ft;
        GetSystemTimeAsFileTime(&ft);
        ULONGLONG t = ((ULONGLONG)ft.dwHighDateTime << 32) | ft.dwLowDateTime;
        t -= 116444736000000000ULL;
        tp->tv_sec  = (time_t)(t / 10000000ULL);
        tp->tv_nsec = (long)((t % 10000000ULL) * 100);
    }
    return 0;
}

static errno_t _rand_s_impl(unsigned int *r)
{
    if (!r) return EINVAL;
    BCryptGenRandom(NULL, (PUCHAR)r, sizeof(*r), BCRYPT_USE_SYSTEM_PREFERRED_RNG);
    return 0;
}
errno_t rand_s(unsigned int *r) { return _rand_s_impl(r); }
errno_t (*__imp_rand_s)(unsigned int *) = _rand_s_impl;

#include <time.h>
errno_t _gmtime64_s(struct tm *_Tm, const __int64 *_Time)
{
    if (!_Tm || !_Time) return EINVAL;
    time_t t = (time_t)*_Time;
    struct tm *r = gmtime(&t);
    if (!r) return EINVAL;
    *_Tm = *r;
    return 0;
}
errno_t (*__imp__gmtime64_s)(struct tm *, const __int64 *) = _gmtime64_s;
static HMODULE WINAPI _gmha_impl(LPCSTR n) { (void)n; return NULL; }
HMODULE (WINAPI *__imp_GetModuleHandleA)(LPCSTR) = _gmha_impl;
