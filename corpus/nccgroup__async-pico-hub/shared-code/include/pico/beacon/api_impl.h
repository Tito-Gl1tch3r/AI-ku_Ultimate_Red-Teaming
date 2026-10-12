#pragma once
#include <Windows.h>
#include <stdio.h>
#include <pico/core/vector.h>
#include <pico/utils.h>
#include <pico/pico.h>
#include <pico/beacon/impl/admin.h>

namespace pic::global {
    pic::AsyncContext* global_async_data = nullptr;
    pic::ThreadContext* global_thread_context = nullptr;
}

namespace pic {
    void init(pic::ThreadContext* ctx) {
        pic::global::global_thread_context = ctx;
        pic::global::global_async_data = ctx->async;
    }
}

extern "C" {
    enum MessageType {
        CALLBACK_OUTPUT = 0x0,
        CALLBACK_ERROR = 0x0d,
        CALLBACK_WAKEUP = 0xff
    };

    void BeaconPrintf(MessageType type, const char* format, ...)
    {
        DFR_LOCAL(MSVCRT, vsnprintf);
        DFR_LOCAL(KERNELBASE, OutputDebugStringA);
        DFR_ALIAS(NTDLL, RtlEnterCriticalSection, EnterCriticalSection);
        DFR_ALIAS(NTDLL, RtlLeaveCriticalSection, LeaveCriticalSection);
        DFR_ALIAS(NTDLL, RtlWakeConditionVariable, WakeConditionVariable);

        va_list args;
        va_start(args, format);

        // First pass: get required size
        va_list args_copy;
        va_copy(args_copy, args);
        //DBG_PRINT("Before first vnsprintf");
        int len = vsnprintf(nullptr, 0, format, args_copy);
        //DBG_PRINT("After first vnsprintf");

        va_end(args_copy);

        if (len < 0) {
            va_end(args);
            return;
        }

        pic::vector<char> buffer(len + 1);

        // Second pass: format string
        //DBG_PRINT("Before second vnsprintf");
        vsnprintf(buffer.begin(), buffer.capacity(), format, args);
        //DBG_PRINT("After second vnsprintf");
        va_end(args);

        EnterCriticalSection(&pic::global::global_async_data->mutex);
        pic::global::global_async_data->output->push_back({ type, buffer.begin() });
        LeaveCriticalSection(&pic::global::global_async_data->mutex);
        WakeConditionVariable(&pic::global::global_async_data->cv);
    }

    BOOL toWideChar(char* src, wchar_t* dst, int max)
    {
        DFR_LOCAL(KERNELBASE, MultiByteToWideChar);
        if (!src || !dst || max <= 0)
            return FALSE;

        // Convert max (bytes)  number of wchar_t elements
        int maxChars = max / sizeof(wchar_t);

        if (maxChars <= 0)
            return FALSE;

        // Use system default ANSI code page
        int result = MultiByteToWideChar(
            CP_ACP,        // default Windows ANSI code page
            0,             // flags
            src,
            -1,            // null-terminated input
            dst,
            maxChars
        );

        if (result == 0)
            return FALSE;

        return TRUE;
    }

    HANDLE BeaconGetStopJobEvent() {
        return pic::global::global_thread_context->stop_event;
    }

    void BeaconWakeup() {
        BeaconPrintf(CALLBACK_WAKEUP, "");
    }

    using chkstk_t =
        unsigned __int64(__fastcall*)();

    DFR_VALUE(NTDLL, __chkstk, chkstk_t, nullptr);

    unsigned __int64  chkstk_impl() {
        return NTDLL$__chkstk();
    }

    void free_impl(void* ptr) {
        DFR_LOCAL(msvcrt, free);
        free(ptr);
    }

}

