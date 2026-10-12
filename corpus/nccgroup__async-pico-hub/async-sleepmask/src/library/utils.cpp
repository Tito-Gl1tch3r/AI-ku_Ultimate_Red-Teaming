#include <windows.h>

// Include bof-vs header files.
#include "beacon.h"
#include "base/helpers.h"
#include "sleepmask.h"

// Include sleepmask-vs specific header files.
#include "..\debug.h"
#include "..\sleepmask-vs.h"

/**
* Find a specific region within the ALLOCATED_MEMORY structure
* 
* @param allocatedMemory A pointer to a ALLOCATED_MEMORY structure
* @param purpose An enum to indicate the desired memory region
* @return A pointer to the desired ALLOCATED_MEMORY_REGION structure
*/
PALLOCATED_MEMORY_REGION FindRegionByPurpose(PALLOCATED_MEMORY allocatedMemory, ALLOCATED_MEMORY_PURPOSE purpose) {
    for (int i = 0; i < sizeof(allocatedMemory->AllocatedMemoryRegions) / sizeof(ALLOCATED_MEMORY_REGION); i++) {
        if (allocatedMemory->AllocatedMemoryRegions[i].Purpose == purpose) {
            return &allocatedMemory->AllocatedMemoryRegions[i];
        }
    }
    return NULL;
}

/**
* Configures system calls for use in BeaconGate.
*
* @param A pointer to a BEACON_SYSCALLS structure.
*/
void InitializeSysCalls(PBEACON_SYSCALLS* pSysCallInfo) {
    if (!pSysCallInfo) {
        goto Cleanup;
    }

    // [0] Setup required sys call structs.
    static BEACON_SYSCALLS sysCallInfo;
    _memset(&sysCallInfo, 0, sizeof(BEACON_SYSCALLS));

    // [1] Attempt to retrieve sys call info..
    if (!BeaconGetSyscallInformation(&sysCallInfo, sizeof(BEACON_SYSCALLS), TRUE)) {
        DLOGF("SLEEPMASK: Failed to configure sytem call info.\n");
        goto Cleanup;
    }

    // [2] Print syscall info back to Beacon if logging is enabled.
#if ENABLE_LOGGING
    PrintSyscallInfo(&sysCallInfo);
#endif

    // [3] Configure global state.
    *pSysCallInfo = &sysCallInfo;
    DLOGF("SLEEPMASK: Successfully configured sys call info.\n");

Cleanup:
    return;
}
