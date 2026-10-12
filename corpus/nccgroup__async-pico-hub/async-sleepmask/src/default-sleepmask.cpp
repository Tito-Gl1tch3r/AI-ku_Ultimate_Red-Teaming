#include <Windows.h>
#include <base/helpers.h>

/**
 * For the debug build we want:
 *   a) Include the mock-up layer
 *   b) Undefine DECLSPEC_IMPORT since the mocked Beacon API
 *      is linked against the the debug build.
 */
#ifndef BUILD_OBJECTS_ONLY
//#undef DECLSPEC_IMPORT
//#define DECLSPEC_IMPORT
#include "base/mock.h"
#endif

#include <pico/pico.h>

extern "C" {
#include "beacon.h"
#include "sleepmask.h"

#include "sleepmask-vs.h"
#include "library\debug.cpp"
#include "library\utils.cpp"
#include "library\stdlib.cpp"
#include "library\masking.cpp"
#include "library\gate.h"

    /**
    * Sleepmask-VS entry point
    *
    * Note: To enable logging for Release builds set ENABLE_LOGGING to
    * 1 in debug.h.
    */
    void sleep_mask(PBEACON_INFO info, PFUNCTION_CALL functionCall) {
        /* invoke beacon gate */
        BeaconGateWrapper(info, functionCall);
    }

#ifdef BUILD_OBJECTS_ONLY

    DECLSPEC_IMPORT unsigned __int64 __fastcall NTDLL$__chkstk();

    unsigned __int64  chkstk_impl() {
        return NTDLL$__chkstk();
    }

    void free_impl(void* ptr) {
        DFR_LOCAL(msvcrt, free);
        free(ptr);
    }

#endif
}

// Define a main function for the debug build.
#ifndef BUILD_OBJECTS_ONLY
int main(int argc, char* argv[]) {
    /**
    * Mock how Beacon calls into Sleepmask
    */
    const bof::profile::Stage stage = 
    {
        .allocator = bof::profile::Allocator::VirtualAlloc,
        .obfuscate = bof::profile::Obfuscate::False,
        .useRWX = bof::profile::UseRWX::False,
        .module = "",
    };
    const bof::mock::MockSleepMaskConfig config = {
            .sleepTimeMs = 5000,
            .runForever = false,
    };

    bof::runMockedSleepMask(sleep_mask, stage, config);
    
    return 0;
}

#endif
