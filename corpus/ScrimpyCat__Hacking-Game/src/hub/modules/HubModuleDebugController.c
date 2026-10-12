/*
 *  Copyright (c) 2020, Stefan Johnson
 *  All rights reserved.
 *
 *  Redistribution and use in source and binary forms, with or without modification,
 *  are permitted provided that the following conditions are met:
 *
 *  1. Redistributions of source code must retain the above copyright notice, this list
 *     of conditions and the following disclaimer.
 *  2. Redistributions in binary form must reproduce the above copyright notice, this
 *     list of conditions and the following disclaimer in the documentation and/or other
 *     materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
 * FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
 * OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include "HubModuleDebugController.h"
#include "HubArchInstruction.h"

#define T size_t
#include <CommonC/Extrema.h>

#define Tbuffer PTYPE(uint8_t *)
#include <CommonC/Memory.h>

#define Tbuffer PTYPE(uint16_t *)
#include <CommonC/Memory.h>

#define Tbuffer PTYPE(uint32_t *)
#include <CommonC/Memory.h>

#define CC_GENERIC_PRESERVE_HEADER
#define CC_GENERIC_TEMPLATE <CommonC/DataMemoryTemplate.h>

#define Tmemory CCData
#define Tbuffer PTYPE(uint8_t *)
#include <CommonC/Memory.h>

#define Tmemory CCData
#define Tbuffer PTYPE(uint16_t *)
#include <CommonC/Memory.h>

#define Tmemory CCData
#define Tbuffer PTYPE(uint32_t *)
#include <CommonC/Memory.h>

#define HK_HUB_MODULE_DEBUG_CONTROLLER_QUERY_PORT_MASK HK_HUB_MODULE_DEBUG_CONTROLLER_QUERY_PORT

#define HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_MAX 100

#define HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_DATA_CHUNK_DEFAULT_SIZE 8

#if DEBUG
size_t HKHubModuleDebugControllerEventBufferMax = HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_MAX;
#undef HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_MAX
#define HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_MAX HKHubModuleDebugControllerEventBufferMax
#define HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_SKIP_FLAG ~(UINT64_MAX >> 1)
typedef uint64_t HKHubModuleDebugControllerEventBufferIndex;
#else
#if HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_MAX <= (UINT8_MAX >> 1)
#define HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_SKIP_FLAG ~(UINT8_MAX >> 1)
typedef uint8_t HKHubModuleDebugControllerEventBufferIndex;
#elif HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_MAX <= (UINT16_MAX >> 1)
#define HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_SKIP_FLAG ~(UINT16_MAX >> 1)
typedef uint16_t HKHubModuleDebugControllerEventBufferIndex;
#elif HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_MAX <= (UINT32_MAX >> 1)
#define HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_SKIP_FLAG ~(UINT32_MAX >> 1)
typedef uint32_t HKHubModuleDebugControllerEventBufferIndex;
#elif HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_MAX <= (UINT64_MAX >> 1)
#define HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_SKIP_FLAG ~(UINT64_MAX >> 1)
typedef uint64_t HKHubModuleDebugControllerEventBufferIndex;
#else
#error Event buffer is too large
#endif
#endif

typedef enum {
    HKHubModuleDebugControllerDeviceEventTypeRun,
    HKHubModuleDebugControllerDeviceEventTypePause,
    HKHubModuleDebugControllerDeviceEventTypeChangeBreakpoint,
    HKHubModuleDebugControllerDeviceEventTypeChangePortConnection,
    HKHubModuleDebugControllerDeviceEventTypeExecutedOperation,
    HKHubModuleDebugControllerDeviceEventTypeModifyRegister,
    HKHubModuleDebugControllerDeviceEventTypeModifyMemory,
    HKHubModuleDebugControllerDeviceEventTypeChangedDataChunk,
    HKHubModuleDebugControllerDeviceEventTypeDeviceConnected,
    HKHubModuleDebugControllerDeviceEventTypeDeviceDisconnected
} HKHubModuleDebugControllerDeviceEventType;

typedef struct {
    CCBigIntFast id;
    HKHubModuleDebugControllerDeviceEventType type;
    uint16_t device;
    union {
        struct {
            uint8_t offset;
            HKHubArchProcessorDebugBreakpoint access;
        } breakpoint;
        struct {
            struct {
                uint16_t device;
                uint8_t port;
            } target;
            uint8_t port;
            _Bool connected;
        } connection;
        struct {
            uint8_t encoding[5];
            uint8_t size;
        } instruction;
        HKHubArchInstructionRegister reg;
        struct {
            uint8_t offset;
            uint8_t size;
        } memory;
        struct {
            union {
                CCData big;
                uint8_t small[7];
            };
            uint8_t size;
        } data;
    };
} HKHubModuleDebugControllerDeviceEvent;

CC_ARRAY_DECLARE(HKHubModuleDebugControllerDeviceEvent);

typedef struct {
    CCArray(HKHubModuleDebugControllerDeviceEvent) buffer;
    size_t count;
} HKHubModuleDebugControllerDeviceEventBuffer;

typedef enum {
    HKHubModuleDebugControllerDeviceTypeNone,
    HKHubModuleDebugControllerDeviceTypeProcessor,
    HKHubModuleDebugControllerDeviceTypeModule
} HKHubModuleDebugControllerDeviceType;

typedef struct {
    HKHubModuleDebugControllerDeviceType type;
    union {
        HKHubArchProcessor processor;
        HKHubModule module;
    };
    HKHubModuleDebugControllerDeviceEventBuffer events;
    size_t index;
    CCString name;
} HKHubModuleDebugControllerDevice;

CC_ARRAY_DECLARE(HKHubModuleDebugControllerDevice);

typedef struct {
    CCBigIntFast index;
    uint8_t *message;
    uint8_t chunks;
    uint8_t chunkBatchSize;
    struct {
        uint16_t commands;
        CCArray(uint16_t) devices;
    } filter;
} HKHubModuleDebugControllerEventState;

typedef struct {
    uint8_t *message;
    uint8_t size;
} HKHubModuleDebugControllerQueryState;

typedef struct {
    CCArray(HKHubModuleDebugControllerDevice) devices;
    CCBigIntFast sharedID;
    HKHubModuleDebugControllerEventState eventPortState[128];
    HKHubModuleDebugControllerQueryState queryPortState[127];
} HKHubModuleDebugControllerState;

static void HKHubModuleDebugControllerDeviceEventDestructor(HKHubModuleDebugControllerDeviceEvent *Event)
{
    if (Event->type == HKHubModuleDebugControllerDeviceEventTypeChangedDataChunk)
    {
        if ((!Event->data.size) && (Event->data.big)) CCDataDestroy(Event->data.big);
    }
    
    CCBigIntFastDestroy(Event->id);
}

static void HKHubModuleDebugControllerPushEvent(HKHubModuleDebugControllerState *State, HKHubModuleDebugControllerDeviceEventBuffer *Events, HKHubModuleDebugControllerDeviceEvent *Event)
{
    Event->id = CCBigIntFastCreate(CC_STD_ALLOCATOR);
    CCBigIntFastSet(&Event->id, State->sharedID);
    CCBigIntFastAdd(&State->sharedID, 1);
    
    if (CCArrayGetCount(Events->buffer) != HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_MAX)
    {
        CCArrayAppendElement(Events->buffer, Event);
    }
    
    else
    {
        HKHubModuleDebugControllerDeviceEventDestructor(CCArrayGetElementAtIndex(Events->buffer, Events->count % HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_MAX));
        
        CCArrayReplaceElementAtIndex(Events->buffer, Events->count % HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_MAX, Event);
    }
    
    Events->count++;
}

static inline size_t HKHubModuleDebugControllerGetBaseEventIndex(const HKHubModuleDebugControllerDeviceEventBuffer *Events)
{
    return CCArrayGetCount(Events->buffer) != HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_MAX ? 0 : (Events->count + 1) % HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_MAX;
}

static inline size_t HKHubModuleDebugControllerEventPortMessageSize(size_t MinSize, size_t DefaultChunkSize)
{
    const size_t DefaultLargestMessageSize = 2 + DefaultChunkSize;
    
    return MinSize > DefaultLargestMessageSize ? MinSize : DefaultLargestMessageSize;
}

static _Bool HKHubModuleDebugControllerFindDevice(CCArray(uint16_t) DeviceRanges, const uint16_t MatchDevice, size_t *RangeIndex, uint16_t *UpdatedRange, _Bool *Insert)
{
    //TODO: change to a binary search
    
    _Bool EarlyExit = FALSE;
    for (size_t Loop = 0, Count = CCArrayGetCount(DeviceRanges); Loop < Count; Loop++)
    {
        uint16_t *DeviceRange = CCArrayGetElementAtIndex(DeviceRanges, Loop);
        const uint16_t Start = *DeviceRange >> 12;
        const uint16_t Stop = (*DeviceRange & 0xf) + Start;
        const _Bool Unused = (*DeviceRange & 0xf) != 0xf;
        
        if (((Start - 1) == MatchDevice) && Unused)
        {
            if (RangeIndex) *RangeIndex = Loop;
            if (UpdatedRange) *UpdatedRange = ((Stop - Start) + 1) | ((Start - 1) << 12);
            if (Insert) *Insert = FALSE;
            
            return FALSE;
        }
        
        else if (((Stop + 1) == MatchDevice) && Unused)
        {
            if (RangeIndex) *RangeIndex = Loop;
            if (UpdatedRange) *UpdatedRange = ((Stop - Start) + 1) | (Start << 12);
            if (Insert) *Insert = FALSE;
            
            EarlyExit = TRUE;
        }
        
        else if ((Start <= MatchDevice) && (Stop >= MatchDevice))
        {
            if (RangeIndex) *RangeIndex = Loop;
            if (UpdatedRange) *UpdatedRange = *DeviceRange;
            if (Insert) *Insert = FALSE;
            
            return TRUE;
        }
        
        else if (MatchDevice < Start)
        {
            if (RangeIndex) *RangeIndex = Loop;
            if (UpdatedRange) *UpdatedRange = MatchDevice << 12;
            if (Insert) *Insert = TRUE;
            
            return FALSE;
        }
        
        else if (EarlyExit) return FALSE;
    }
    
    if (!EarlyExit)
    {
        if (RangeIndex) *RangeIndex = SIZE_MAX;
        if (UpdatedRange) *UpdatedRange = MatchDevice << 12;
        if (Insert) *Insert = TRUE;
    }
    
    return FALSE;
}

static void HKHubModuleDebugControllerAddDevice(CCArray(uint16_t) DeviceRanges, const uint16_t MatchDevice)
{
    size_t RangeIndex;
    uint16_t UpdatedRange;
    _Bool Insert;
    
    if (!HKHubModuleDebugControllerFindDevice(DeviceRanges, MatchDevice, &RangeIndex, &UpdatedRange, &Insert))
    {
        if (Insert)
        {
            if (RangeIndex == SIZE_MAX) CCArrayAppendElement(DeviceRanges, &UpdatedRange);
            else CCArrayInsertElementAtIndex(DeviceRanges, RangeIndex, &UpdatedRange);
        }
        
        else CCArrayReplaceElementAtIndex(DeviceRanges, RangeIndex, &UpdatedRange);
    }
}

static void HKHubModuleDebugControllerRemoveDevice(CCArray(uint16_t) DeviceRanges, const uint16_t MatchDevice)
{
    size_t RangeIndex;
    uint16_t UpdatedRange;
    
    if (HKHubModuleDebugControllerFindDevice(DeviceRanges, MatchDevice, &RangeIndex, &UpdatedRange, NULL))
    {
        const uint16_t Start = UpdatedRange >> 12;
        const uint16_t Stop = (UpdatedRange & 0xf) + Start;
        
        if (Start == Stop)
        {
            CCArrayRemoveElementAtIndex(DeviceRanges, RangeIndex);
        }
        
        else if ((Start - 1) == MatchDevice)
        {
            CCArrayReplaceElementAtIndex(DeviceRanges, RangeIndex, &(uint16_t){ ((Stop - Start) - 1) | ((Start + 1) << 12) });
        }
        
        else if ((Stop + 1) == MatchDevice)
        {
            CCArrayReplaceElementAtIndex(DeviceRanges, RangeIndex, &(uint16_t){ ((Stop - Start) - 1) | (Start << 12) });
        }
        
        else
        {
            CCArrayReplaceElementAtIndex(DeviceRanges, RangeIndex, &(uint16_t){ ((Stop - MatchDevice) - 1) | ((MatchDevice + 1) << 12) });
            CCArrayInsertElementAtIndex(DeviceRanges, RangeIndex, &(uint16_t){ ((MatchDevice - Start) - 1) | (Start << 12) });
        }
    }
}

static CC_FORCE_INLINE uint8_t HKHubModuleDebugControllerMessageGetU8(const HKHubArchPortMessage * const Message, const size_t Offset)
{
    uint8_t Value;
    CCMemoryReadBig(Message->memory, 256, Message->offset + Offset, sizeof(Value), &Value);
    
    return Value;
}

static CC_FORCE_INLINE uint16_t HKHubModuleDebugControllerMessageGetU16(const HKHubArchPortMessage * const Message, const size_t Offset)
{
    uint16_t Value;
    CCMemoryReadBig(Message->memory, 256, Message->offset + Offset, sizeof(Value), &Value);
    
    return Value;
}

static CC_FORCE_INLINE uint32_t HKHubModuleDebugControllerMessageGetU32(const HKHubArchPortMessage * const Message, const size_t Offset)
{
    uint32_t Value;
    CCMemoryReadBig(Message->memory, 256, Message->offset + Offset, sizeof(Value), &Value);
    
    return Value;
}

static CC_FORCE_INLINE uint16_t HKHubModuleDebugControllerMessageGetDeviceID(const HKHubArchPortMessage * const Message, const size_t Offset)
{
    return HKHubModuleDebugControllerMessageGetU16(Message, Offset) & 0xfff;
}

static HKHubArchPortResponse HKHubModuleDebugControllerReceive(HKHubArchPortConnection Connection, HKHubModule Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    const HKHubArchPort *OppositePort = HKHubArchPortConnectionGetOppositePort(Connection, Device, Port);
    
    if (HKHubArchPortIsReady(OppositePort))
    {
        if (Message->size >= 1)
        {
            HKHubModuleDebugControllerState *State = Device->internal;
            
            if (Port & HK_HUB_MODULE_DEBUG_CONTROLLER_QUERY_PORT_MASK)
            {
                Port ^= HK_HUB_MODULE_DEBUG_CONTROLLER_QUERY_PORT_MASK;
                
                // query api
                if (!State->queryPortState[Port].message)
                {
                    CC_SAFE_Malloc(State->queryPortState[Port].message, 256,
                                   CC_LOG_ERROR("Failed to create query port message buffer, due to allocation failure (256)");
                                   return HKHubArchPortResponseDefer;
                                   );
                }
                
                HKHubArchPortResponse Response = HKHubArchPortResponseTimeout;
                
                switch (Message->memory[Message->offset] >> 4)
                {
                    case 0:
                    {
                        //[0:4] device count (count:16)
                        const size_t Count = CCArrayGetCount(State->devices);
                        State->queryPortState[Port].message[0] = (Count >> 8) & 0xff;
                        State->queryPortState[Port].message[1] = Count & 0xff;
                        State->queryPortState[Port].size = 2;
                        break;
                    }
                        
                    case 1:
                        //[1:4] [device:12] memory size (size:16)
                        if (Message->size >= 2)
                        {
                            const uint16_t DeviceID = HKHubModuleDebugControllerMessageGetDeviceID(Message, 0);
                            
                            if (DeviceID < CCArrayGetCount(State->devices))
                            {
                                HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, DeviceID);
                                switch (Device->type)
                                {
                                    case HKHubModuleDebugControllerDeviceTypeNone:
                                        break;
                                        
                                    case HKHubModuleDebugControllerDeviceTypeProcessor:
                                        State->queryPortState[Port].message[0] = 1;
                                        State->queryPortState[Port].message[1] = 0;
                                        State->queryPortState[Port].size = 2;
                                        Response = HKHubArchPortResponseSuccess;
                                        break;
                                        
                                    case HKHubModuleDebugControllerDeviceTypeModule:
                                        if (Device->module->memory)
                                        {
                                            const size_t Count = CCDataGetSize(Device->module->memory);
                                            CCAssertLog(Count <= UINT16_MAX, "Memory size exceeds 16-bits");
                                            State->queryPortState[Port].message[0] = (Count >> 8) & 0xff;
                                            State->queryPortState[Port].message[1] = Count & 0xff;
                                        }
                                        
                                        else
                                        {
                                            State->queryPortState[Port].message[0] = 0;
                                            State->queryPortState[Port].message[1] = 0;
                                        }
                                        
                                        State->queryPortState[Port].size = 2;
                                        Response = HKHubArchPortResponseSuccess;
                                        break;
                                }
                            }
                        }
                        break;
                        
                    case 2:
                        //[2:4] [device:12] read memory [offset:8] [size:8] ... (bytes:sum sizes)
                        if ((Message->size >= 2) && ((Message->size % 2) == 0))
                        {
                            const uint16_t DeviceID = HKHubModuleDebugControllerMessageGetDeviceID(Message, 0);
                            
                            if (DeviceID < CCArrayGetCount(State->devices))
                            {
                                HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, DeviceID);
                                if (Device->type == HKHubModuleDebugControllerDeviceTypeProcessor)
                                {
                                    uint8_t Index = 0;
                                    for (size_t Loop = 2, Count = Message->size; Loop < Count; Loop += 2)
                                    {
                                        const size_t Offset = HKHubModuleDebugControllerMessageGetU8(Message, Loop), Size = HKHubModuleDebugControllerMessageGetU8(Message, Loop + 1);
                                        
                                        CCMemoryReadBig(Device->processor->memory, 256, Offset, Size, &State->queryPortState[Port].message[Index]);
                                        Index += Size;
                                    }
                                    
                                    State->queryPortState[Port].size = Index;
                                    
                                    Response = HKHubArchPortResponseSuccess;
                                }
                                
                                else if (Device->type == HKHubModuleDebugControllerDeviceTypeModule)
                                {
                                    const size_t MemorySize = CCDataGetSize(Device->module->memory);
                                    
                                    uint8_t Index = 0;
                                    for (size_t Loop = 2, Count = Message->size; Loop < Count; Loop += 2)
                                    {
                                        const size_t Offset = HKHubModuleDebugControllerMessageGetU8(Message, Loop), Size = HKHubModuleDebugControllerMessageGetU8(Message, Loop + 1);
                                        
                                        CCMemoryReadBig(Device->module->memory, MemorySize, Offset, Size, &State->queryPortState[Port].message[Index]);
                                        Index += Size;
                                    }
                                    
                                    State->queryPortState[Port].size = Index;
                                    
                                    Response = HKHubArchPortResponseSuccess;
                                }
                            }
                        }
                        break;
                        
                    case 3:
                        //[3:4] [device:12] read memory [offset:16] [size:8] ... (bytes:sum sizes)
                        if ((Message->size >= 2) && (((Message->size - 2) % 3) == 0))
                        {
                            const uint16_t DeviceID = HKHubModuleDebugControllerMessageGetDeviceID(Message, 0);
                            
                            if (DeviceID < CCArrayGetCount(State->devices))
                            {
                                HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, DeviceID);
                                if (Device->type == HKHubModuleDebugControllerDeviceTypeProcessor)
                                {
                                    uint8_t Index = 0;
                                    for (size_t Loop = 2, Count = Message->size; Loop < Count; Loop += 3)
                                    {
                                        const size_t Offset = HKHubModuleDebugControllerMessageGetU16(Message, Loop), Size = HKHubModuleDebugControllerMessageGetU8(Message, Loop + 2);
                                        
                                        CCMemoryReadBig(Device->processor->memory, 256, Offset, Size, &State->queryPortState[Port].message[Index]);
                                        Index += Size;
                                    }
                                    
                                    State->queryPortState[Port].size = Index;
                                    
                                    Response = HKHubArchPortResponseSuccess;
                                }
                                
                                else if (Device->type == HKHubModuleDebugControllerDeviceTypeModule)
                                {
                                    const size_t MemorySize = CCDataGetSize(Device->module->memory);
                                    
                                    uint8_t Index = 0;
                                    for (size_t Loop = 2, Count = Message->size; Loop < Count; Loop += 3)
                                    {
                                        const size_t Offset = HKHubModuleDebugControllerMessageGetU16(Message, Loop), Size = HKHubModuleDebugControllerMessageGetU8(Message, Loop + 2);
                                        
                                        CCMemoryReadBig(Device->module->memory, MemorySize, Offset, Size, &State->queryPortState[Port].message[Index]);
                                        Index += Size;
                                    }
                                    
                                    State->queryPortState[Port].size = Index;
                                    
                                    Response = HKHubArchPortResponseSuccess;
                                }
                            }
                        }
                        break;
                        
                    case 4:
                        //[4:4] [device:12] read registers [_:2, r0:1?, r1:1?, r2:1?, r3:1?, flags:1?, pc:1?, defaults to 0x3f] (r0:8?, r1:8?, r2:8?, r3:8?, flags:8?, pc:8?)
                        if (Message->size >= 2)
                        {
                            const uint16_t DeviceID = HKHubModuleDebugControllerMessageGetDeviceID(Message, 0);
                            
                            if (DeviceID < CCArrayGetCount(State->devices))
                            {
                                HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, DeviceID);
                                if (Device->type == HKHubModuleDebugControllerDeviceTypeProcessor)
                                {
                                    if (Message->size >= 3)
                                    {
                                        uint8_t Index = 0;
                                        const uint8_t Mask = HKHubModuleDebugControllerMessageGetU8(Message, 2);
                                        
                                        if (Mask & (1 << 5)) State->queryPortState[Port].message[Index++] = Device->processor->state.r[0];
                                        if (Mask & (1 << 4)) State->queryPortState[Port].message[Index++] = Device->processor->state.r[1];
                                        if (Mask & (1 << 3)) State->queryPortState[Port].message[Index++] = Device->processor->state.r[2];
                                        if (Mask & (1 << 2)) State->queryPortState[Port].message[Index++] = Device->processor->state.r[3];
                                        if (Mask & (1 << 1)) State->queryPortState[Port].message[Index++] = Device->processor->state.flags;
                                        if (Mask & (1 << 0)) State->queryPortState[Port].message[Index++] = Device->processor->state.pc;
                                        
                                        State->queryPortState[Port].size = Index;
                                    }
                                    
                                    else
                                    {
                                        State->queryPortState[Port].message[0] = Device->processor->state.r[0];
                                        State->queryPortState[Port].message[1] = Device->processor->state.r[1];
                                        State->queryPortState[Port].message[2] = Device->processor->state.r[2];
                                        State->queryPortState[Port].message[3] = Device->processor->state.r[3];
                                        State->queryPortState[Port].message[4] = Device->processor->state.flags;
                                        State->queryPortState[Port].message[5] = Device->processor->state.pc;
                                        State->queryPortState[Port].size = 6;
                                    }
                                    
                                    Response = HKHubArchPortResponseSuccess;
                                }
                            }
                        }
                        break;
                        
                    case 5:
                        //[5:4] [device:12] read breakpoints [offset:8? ... defaults to every offset] (w:1 r:1, ...)
                        if (Message->size >= 2)
                        {
                            const uint16_t DeviceID = HKHubModuleDebugControllerMessageGetDeviceID(Message, 0);
                            
                            if (DeviceID < CCArrayGetCount(State->devices))
                            {
                                HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, DeviceID);
                                if (Device->type == HKHubModuleDebugControllerDeviceTypeProcessor)
                                {
                                    size_t Index = 0;
                                    
                                    if (Message->size == 2)
                                    {
                                        if (Device->processor->state.debug.breakpoints)
                                        {
                                            for (size_t Loop = 0, Count = 256; Loop < Count; Loop++)
                                            {
                                                HKHubArchProcessorDebugBreakpoint CurrentBP = 0;
                                                HKHubArchProcessorDebugBreakpoint *Breakpoint = CCDictionaryGetValue(Device->processor->state.debug.breakpoints, &(uint8_t){ Loop });
                                                if (Breakpoint) CurrentBP = *Breakpoint;
                                                
                                                if (Index % 4 == 0) State->queryPortState[Port].message[Index / 4] = 0;
                                                
                                                State->queryPortState[Port].message[Index / 4] |= CurrentBP << (6 - ((Index % 4) * 2));
                                                Index++;
                                            }
                                        }
                                        
                                        else
                                        {
                                            Index = 64 * 4;
                                            memset(State->queryPortState[Port].message, 0, 64);
                                        }
                                    }
                                    
                                    else
                                    {
                                        if (Device->processor->state.debug.breakpoints)
                                        {
                                            for (size_t Loop = 2, Count = Message->size; Loop < Count; Loop++)
                                            {
                                                const uint8_t Offset = HKHubModuleDebugControllerMessageGetU8(Message, Loop);
                                                
                                                HKHubArchProcessorDebugBreakpoint CurrentBP = 0;
                                                HKHubArchProcessorDebugBreakpoint *Breakpoint = CCDictionaryGetValue(Device->processor->state.debug.breakpoints, &Offset);
                                                if (Breakpoint) CurrentBP = *Breakpoint;
                                                
                                                if (Index % 4 == 0) State->queryPortState[Port].message[Index] = 0;
                                                
                                                State->queryPortState[Port].message[Index / 4] |= CurrentBP << (6 - ((Index % 4) * 2));
                                                Index++;
                                            }
                                        }
                                        
                                        else
                                        {
                                            const size_t Count = ((((Message->size - 2) / 4) - 1) / 4) + 1;
                                            Index = Count * 4;
                                            memset(State->queryPortState[Port].message, 0, Count);
                                        }
                                    }
                                    
                                    State->queryPortState[Port].size = ((Index - 1) / 4) + 1;
                                    
                                    Response = HKHubArchPortResponseSuccess;
                                }
                            }
                        }
                        break;
                        
                    case 6:
                        //[6:4] [device:12] read ports (256 bits)
                        //[6:4] [device:12] read ports [port:8 ...] (receiving port:8, connected:1, _:3, device:12)
                        if (Message->size == 2)
                        {
                            const uint16_t DeviceID = HKHubModuleDebugControllerMessageGetDeviceID(Message, 0);
                            
                            if (DeviceID < CCArrayGetCount(State->devices))
                            {
                                HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, DeviceID);
                                if (Device->type == HKHubModuleDebugControllerDeviceTypeProcessor)
                                {
                                    memset(State->queryPortState[Port].message, 0, 32);
                                    State->queryPortState[Port].size = 32;
                                    
                                    CC_DICTIONARY_FOREACH_KEY(HKHubArchPortID, PortID, Device->processor->ports)
                                    {
                                        const size_t Index = PortID / 8;
                                        State->queryPortState[Port].message[Index] |= 1 << (7 - (PortID - (Index * 8)));
                                    }
                                    
                                    Response = HKHubArchPortResponseSuccess;
                                }
                            }
                        }
                        
                        else if (Message->size >= 3)
                        {
                            const uint16_t DeviceID = HKHubModuleDebugControllerMessageGetDeviceID(Message, 0);
                            
                            if (DeviceID < CCArrayGetCount(State->devices))
                            {
                                HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, DeviceID);
                                if (Device->type == HKHubModuleDebugControllerDeviceTypeProcessor)
                                {
                                    uint8_t Index = 0;
                                    for (size_t Loop = 2, Count = Message->size; Loop < Count; Loop++)
                                    {
                                        const HKHubArchPortID PortID = HKHubModuleDebugControllerMessageGetU8(Message, Loop);
                                        
                                        HKHubArchPortConnection Conn = HKHubArchProcessorGetPortConnection(Device->processor, PortID);
                                        if (Conn)
                                        {
                                            HKHubArchPort *OppositePort = HKHubArchPortConnectionGetOppositePort(Conn, Device->processor, PortID);
                                            
                                            State->queryPortState[Port].message[Index++] = OppositePort->id;
                                            // TODO: Add callback to HKHubArchPort to get debug context (only safe if don't allow other debug contexts)
                                            uint16_t ConnectedDeviceID = 0xfff;
                                            for (size_t Loop2 = 0, Count2 = CCArrayGetCount(State->devices); Loop2 < Count2; Loop2++)
                                            {
                                                HKHubModuleDebugControllerDevice *ConnectedDevice = CCArrayGetElementAtIndex(State->devices, Loop2);
                                                if (ConnectedDevice)
                                                {
                                                    if ((ConnectedDevice->processor == OppositePort->device) || (ConnectedDevice->module == OppositePort->device))
                                                    {
                                                        ConnectedDeviceID = Loop2;
                                                        break;
                                                    }
                                                }
                                            }
                                            
                                            State->queryPortState[Port].message[Index++] = (ConnectedDeviceID >> 8) | 0x80;
                                            State->queryPortState[Port].message[Index++] = ConnectedDeviceID & 0xff;
                                        }
                                        
                                        else
                                        {
                                            State->queryPortState[Port].message[Index++] = 0;
                                            State->queryPortState[Port].message[Index++] = 0xf;
                                            State->queryPortState[Port].message[Index++] = 0xff;
                                        }
                                    }
                                    
                                    State->queryPortState[Port].size = Index;
                                    
                                    Response = HKHubArchPortResponseSuccess;
                                }
                            }
                        }
                        break;
                        
                    case 7:
                        //[7:4] [device:12] toggle break [offset:8] [_:6] [wr:2] ... (xors wr)
                        if ((Message->size >= 2) && ((Message->size % 2) == 0))
                        {
                            const uint16_t DeviceID = HKHubModuleDebugControllerMessageGetDeviceID(Message, 0);
                            
                            if (DeviceID < CCArrayGetCount(State->devices))
                            {
                                HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, DeviceID);
                                if (Device->type == HKHubModuleDebugControllerDeviceTypeProcessor)
                                {
                                    for (size_t Loop = 2, Count = Message->size; Loop < Count; Loop += 2)
                                    {
                                        const uint8_t Offset = HKHubModuleDebugControllerMessageGetU8(Message, Loop);
                                        
                                        HKHubArchProcessorDebugBreakpoint CurrentBP = 0;
                                        if (Device->processor->state.debug.breakpoints)
                                        {
                                            HKHubArchProcessorDebugBreakpoint *Breakpoint = CCDictionaryGetValue(Device->processor->state.debug.breakpoints, &Offset);
                                            if (Breakpoint) CurrentBP = *Breakpoint;
                                        }
                                        
                                        HKHubArchProcessorSetBreakpoint(Device->processor, CurrentBP ^ HKHubModuleDebugControllerMessageGetU8(Message, Loop + 1), Offset);
                                    }
                                    
                                    Response = HKHubArchPortResponseSuccess;
                                }
                            }
                        }
                        break;
                        
                    case 8:
                        //[8:4] [device:12] continue
                        if (Message->size >= 2)
                        {
                            const uint16_t DeviceID = HKHubModuleDebugControllerMessageGetDeviceID(Message, 0);
                            
                            if (DeviceID < CCArrayGetCount(State->devices))
                            {
                                HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, DeviceID);
                                if (Device->type == HKHubModuleDebugControllerDeviceTypeProcessor)
                                {
                                    HKHubArchProcessorStep(Device->processor, 1);
                                    HKHubArchProcessorSetDebugMode(Device->processor, HKHubArchProcessorDebugModeContinue);
                                    Response = HKHubArchPortResponseSuccess;
                                }
                            }
                        }
                        break;
                        
                    case 9:
                        //[9:4] [device:12] pause
                        if (Message->size >= 2)
                        {
                            const uint16_t DeviceID = HKHubModuleDebugControllerMessageGetDeviceID(Message, 0);
                            
                            if (DeviceID < CCArrayGetCount(State->devices))
                            {
                                HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, DeviceID);
                                if (Device->type == HKHubModuleDebugControllerDeviceTypeProcessor)
                                {
                                    HKHubArchProcessorSetDebugMode(Device->processor, HKHubArchProcessorDebugModePause);
                                    Response = HKHubArchPortResponseSuccess;
                                }
                            }
                        }
                        break;
                        
                    case 10:
                        //[a:4] [device:12] step [count:8?]
                        //[a:4] [device:12] step [count:16?]
                        if (Message->size >= 2)
                        {
                            const uint16_t DeviceID = HKHubModuleDebugControllerMessageGetDeviceID(Message, 0);
                            
                            if (DeviceID < CCArrayGetCount(State->devices))
                            {
                                HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, DeviceID);
                                if (Device->type == HKHubModuleDebugControllerDeviceTypeProcessor)
                                {
                                    size_t Count = 1;
                                    if (Message->size == 3) Count = HKHubModuleDebugControllerMessageGetU8(Message, 2);
                                    else if (Message->size >= 4) Count = HKHubModuleDebugControllerMessageGetU16(Message, 2);
                                    
                                    HKHubArchProcessorStep(Device->processor, Count);
                                    Response = HKHubArchPortResponseSuccess;
                                }
                            }
                        }
                        break;
                        
                    case 11:
                        //[b:4] [device:12] mode (_:7, running/paused: 1 bit)
                        if (Message->size >= 2)
                        {
                            const uint16_t DeviceID = HKHubModuleDebugControllerMessageGetDeviceID(Message, 0);
                            
                            if (DeviceID < CCArrayGetCount(State->devices))
                            {
                                HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, DeviceID);
                                if (Device->type == HKHubModuleDebugControllerDeviceTypeProcessor)
                                {
                                    _Static_assert(HKHubArchProcessorDebugModeContinue == 0 &&
                                                   HKHubArchProcessorDebugModePause == 1, "Debug mode flags have changed");
                                    
                                    State->queryPortState[Port].message[0] = Device->processor->state.debug.mode;
                                    State->queryPortState[Port].size = 1;
                                    Response = HKHubArchPortResponseSuccess;
                                }
                            }
                        }
                        break;
                        
                    case 12:
                        //[c:4] [device:12] name [size:8? defaults to 256] (string:256?)
                        if (Message->size >= 2)
                        {
                            const uint16_t DeviceID = HKHubModuleDebugControllerMessageGetDeviceID(Message, 0);
                            
                            if (DeviceID < CCArrayGetCount(State->devices))
                            {
                                HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, DeviceID);
                                
                                size_t Length = 32;
                                if (Message->size == 3) Length = HKHubModuleDebugControllerMessageGetU8(Message, 2);
                                
                                memset(State->queryPortState[Port].message, 0, Length);
                                
                                if (Device->name)
                                {
                                    CC_STRING_TEMP_BUFFER(Buffer, Device->name)
                                    {
                                        memcpy(State->queryPortState[Port].message, Buffer, CCMin(CCStringGetSize(Device->name), Length));
                                    }
                                }
                                
                                State->queryPortState[Port].size = Length;
                                
                                Response = HKHubArchPortResponseSuccess;
                            }
                        }
                        break;
                        
                    case 13:
                        //[d:4] [device:12] read memory [offset:32] [size:8] ... (bytes:sum sizes)
                        if ((Message->size >= 2) && (((Message->size - 2) % 5) == 0))
                        {
                            const uint16_t DeviceID = HKHubModuleDebugControllerMessageGetDeviceID(Message, 0);
                            
                            if (DeviceID < CCArrayGetCount(State->devices))
                            {
                                HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, DeviceID);
                                if (Device->type == HKHubModuleDebugControllerDeviceTypeProcessor)
                                {
                                    uint8_t Index = 0;
                                    for (size_t Loop = 2, Count = Message->size; Loop < Count; Loop += 5)
                                    {
                                        const size_t Offset = HKHubModuleDebugControllerMessageGetU32(Message, Loop), Size = HKHubModuleDebugControllerMessageGetU8(Message, Loop + 4);
                                        
                                        CCMemoryReadBig(Device->processor->memory, 256, Offset, Size, &State->queryPortState[Port].message[Index]);
                                        Index += Size;
                                    }
                                    
                                    State->queryPortState[Port].size = Index;
                                    
                                    Response = HKHubArchPortResponseSuccess;
                                }
                                
                                else if (Device->type == HKHubModuleDebugControllerDeviceTypeModule)
                                {
                                    const size_t MemorySize = CCDataGetSize(Device->module->memory);
                                    
                                    uint8_t Index = 0;
                                    for (size_t Loop = 2, Count = Message->size; Loop < Count; Loop += 5)
                                    {
                                        const size_t Offset = HKHubModuleDebugControllerMessageGetU32(Message, Loop), Size = HKHubModuleDebugControllerMessageGetU8(Message, Loop + 4);
                                        
                                        CCMemoryReadBig(Device->module->memory, MemorySize, Offset, Size, &State->queryPortState[Port].message[Index]);
                                        Index += Size;
                                    }
                                    
                                    State->queryPortState[Port].size = Index;
                                    
                                    Response = HKHubArchPortResponseSuccess;
                                }
                            }
                        }
                        break;
                }
                
                return Response;
            }
            
            else
            {
                // event api
                HKHubArchPortResponse Response = HKHubArchPortResponseTimeout;
                
                switch (Message->memory[Message->offset] >> 4)
                {
                    case 0:
                        //[0:4] add filter [command:4]
                        State->eventPortState[Port].filter.commands |= 1 << (Message->memory[Message->offset] & 0xf);
                        Response = HKHubArchPortResponseSuccess;
                        break;
                        
                    case 1:
                        //[1:4] remove filter [command:4]
                        State->eventPortState[Port].filter.commands &= ~(1 << (Message->memory[Message->offset] & 0xf));
                        Response = HKHubArchPortResponseSuccess;
                        break;
                        
                    case 2:
                        //[2:4] add filter [device:12]
                        if (Message->size >= 2)
                        {
                            const uint16_t FilterDevice = HKHubModuleDebugControllerMessageGetDeviceID(Message, 0);
                            
                            if (!State->eventPortState[Port].filter.devices)
                            {
                                State->eventPortState[Port].filter.devices = CCArrayCreate(CC_STD_ALLOCATOR, sizeof(uint16_t), 4);
                            }
                            
                            HKHubModuleDebugControllerAddDevice(State->eventPortState[Port].filter.devices, FilterDevice);
                            Response = HKHubArchPortResponseSuccess;
                        }
                        break;
                        
                    case 3:
                        //[3:4] remove filter [device:12]
                        if (Message->size >= 2)
                        {
                            if (State->eventPortState[Port].filter.devices)
                            {
                                const uint16_t FilterDevice = HKHubModuleDebugControllerMessageGetDeviceID(Message, 0);
                                
                                HKHubModuleDebugControllerRemoveDevice(State->eventPortState[Port].filter.devices, FilterDevice);
                                
                                if (CCArrayGetCount(State->eventPortState[Port].filter.devices) == 0)
                                {
                                    CCArrayDestroy(State->eventPortState[Port].filter.devices);
                                    State->eventPortState[Port].filter.devices = NULL;
                                }
                            }
                            
                            Response = HKHubArchPortResponseSuccess;
                        }
                        break;
                        
                    case 4:
                        //[4:4] [_:4] set modified data chunk [size:8]
                        if (Message->size >= 2)
                        {
                            State->eventPortState[Port].chunkBatchSize = HKHubModuleDebugControllerMessageGetU8(Message, 1);
                            CC_SAFE_Realloc(State->eventPortState[Port].message, HKHubModuleDebugControllerEventPortMessageSize(16, State->eventPortState[Port].chunkBatchSize),
                                            CC_LOG_ERROR("Failed to resize event port message buffer, due to allocation failure (%zu)", HKHubModuleDebugControllerEventPortMessageSize(16, State->eventPortState[Port].chunkBatchSize));
                                            );
                            
                            Response = HKHubArchPortResponseSuccess;
                        }
                        
                        break;
                }
                
                return Response;
            }
        }
    }
    
    return HKHubArchPortResponseSuccess;
}

static HKHubArchPortResponse HKHubModuleDebugControllerSend(HKHubArchPortConnection Connection, HKHubModule Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchProcessor ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    HKHubModuleDebugControllerState *State = Device->internal;
    
    if (Port & HK_HUB_MODULE_DEBUG_CONTROLLER_QUERY_PORT_MASK)
    {
        Port ^= HK_HUB_MODULE_DEBUG_CONTROLLER_QUERY_PORT_MASK;
        
        // query api
        if ((State->queryPortState[Port].message) && (State->queryPortState[Port].size))
        {
            *Message = (HKHubArchPortMessage){
                .memory = State->queryPortState[Port].message,
                .offset = 0,
                .size = State->queryPortState[Port].size
            };
            
            State->queryPortState[Port].size = 0;
            
            if (!HKHubArchPortIsReady(HKHubArchPortConnectionGetOppositePort(Connection, Device, Port))) return HKHubArchPortResponseDefer;
            
            return HKHubArchPortResponseSuccess;
        }
    }
    
    else
    {
        // event api
        const size_t Count = CCArrayGetCount(State->devices);
        HKHubModuleDebugControllerEventBufferIndex *Skip;
        
        CC_TEMP_Malloc(Skip, sizeof(*Skip) * Count);
        memset(Skip, 0, sizeof(*Skip) * Count);
        
        _Static_assert(sizeof(HKHubModuleDebugControllerEventBufferIndex) <= sizeof(size_t), "Buffer index should not exceed size_t");
        
        for (size_t Loop = 0, Count = CCArrayGetCount(State->devices); Loop < Count; Loop++)
        {
            if (Skip[Loop] & HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_SKIP_FLAG) continue;
            
            const HKHubModuleDebugControllerDevice *DebuggedDevice = CCArrayGetElementAtIndex(State->devices, Loop);
            
            if (DebuggedDevice->events.buffer)
            {
                const HKHubModuleDebugControllerDeviceEvent *Event = NULL;
                CCComparisonResult Result = CCComparisonResultInvalid;
                
                for (size_t Loop2 = Skip[Loop], Base = HKHubModuleDebugControllerGetBaseEventIndex(&DebuggedDevice->events), Count2 = CCMin(CCArrayGetCount(DebuggedDevice->events.buffer), HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_MAX); (Loop2 < Count2) && (Result != CCComparisonResultEqual) && (Result != CCComparisonResultAscending); Loop2++)
                {
                    Event = CCArrayGetElementAtIndex(DebuggedDevice->events.buffer, (Base + Loop2) % HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_MAX);
                    Result = CCBigIntFastCompare(State->eventPortState[Port].index, Event->id);
                    
                    if (Result == CCComparisonResultEqual)
                    {
                        if ((State->eventPortState[Port].filter.commands != 0) && ((State->eventPortState[Port].filter.commands & (1 << Event->type)) == 0))
                        {
                            CCBigIntFastAdd(&State->eventPortState[Port].index, 1);
                            Result = CCComparisonResultInvalid;
                            Skip[Loop] = Loop2;
                            Loop = SIZE_MAX;
                        }
                        
                        else if ((State->eventPortState[Port].filter.devices) && (CCArrayGetCount(State->eventPortState[Port].filter.devices)) && (!HKHubModuleDebugControllerFindDevice(State->eventPortState[Port].filter.devices, (uint16_t)Event->device, NULL, NULL, NULL)))
                        {
                            CCBigIntFastAdd(&State->eventPortState[Port].index, 1);
                            Result = CCComparisonResultInvalid;
                            Skip[Loop] = Loop2;
                            Loop = SIZE_MAX;
                        }
                    }
                }
                
                if (Result == CCComparisonResultEqual)
                {
                    CC_TEMP_Free(Skip);
                    
                    size_t Size = 0;
                    State->eventPortState[Port].message[Size++] = (Event->type << 4) | ((Event->device & 0xf00) >> 8);
                    State->eventPortState[Port].message[Size++] = Event->device & 0xff;
                    
                    int NextIndex = 1;
                    
                    switch (Event->type)
                    {
                        case HKHubModuleDebugControllerDeviceEventTypeRun:
                            //[0:4] [device:12] running
                            break;
                            
                        case HKHubModuleDebugControllerDeviceEventTypePause:
                            //[1:4] [device:12] paused
                            break;
                            
                        case HKHubModuleDebugControllerDeviceEventTypeChangeBreakpoint:
                            //[2:4] [device:12] change breakpoint [offset:8] [_:6] [w:1] [r:1]
                            State->eventPortState[Port].message[Size++] = Event->breakpoint.offset;
                            State->eventPortState[Port].message[Size++] = Event->breakpoint.access & 3;
                            _Static_assert(HKHubArchProcessorDebugBreakpointRead == (1 << 0), "Read breakpoint flag changed");
                            _Static_assert(HKHubArchProcessorDebugBreakpointWrite == (1 << 1), "Write breakpoint flag changed");
                            break;
                            
                        case HKHubModuleDebugControllerDeviceEventTypeChangePortConnection:
                            //[3:4] [device:12] change [port:8] [receiving port: 8, connected:1, _:3, device:12]
                            State->eventPortState[Port].message[Size++] = Event->connection.port;
                            State->eventPortState[Port].message[Size++] = Event->connection.target.port;
                            State->eventPortState[Port].message[Size++] = ((Event->connection.target.device & 0xf00) >> 8) | (Event->connection.connected * 0x80);
                            State->eventPortState[Port].message[Size++] = Event->connection.target.device & 0xff;
                            break;
                            
                        case HKHubModuleDebugControllerDeviceEventTypeExecutedOperation:
                            //[4:4] [device:12] change op [encoded instruction:8 ...]
                            for (size_t Index = 0; Index < Event->instruction.size; Index++)
                            {
                                State->eventPortState[Port].message[Size++] = Event->instruction.encoding[Index];
                            }
                            break;
                            
                        case HKHubModuleDebugControllerDeviceEventTypeModifyRegister:
                            //[5:4] [device:12] modified [_:5] [reg:3]
                            State->eventPortState[Port].message[Size++] = Event->reg;
                            break;
                            
                        case HKHubModuleDebugControllerDeviceEventTypeModifyMemory:
                            //[6:4] [device:12] modified memory [offset:8] [size:8]
                            State->eventPortState[Port].message[Size++] = Event->memory.offset;
                            State->eventPortState[Port].message[Size++] = Event->memory.size;
                            break;
                            
                        case HKHubModuleDebugControllerDeviceEventTypeChangedDataChunk:
                            //[7:4] [device:12] modified [data:8 ...] (comes in as 8 byte sequences, this can be changed)
                            if (Event->data.size)
                            {
                                size_t ChunkSize = Event->data.size - State->eventPortState[Port].chunks;
                                
                                if (ChunkSize > State->eventPortState[Port].chunkBatchSize) ChunkSize = State->eventPortState[Port].chunkBatchSize;
                                
                                memcpy(&State->eventPortState[Port].message[Size], Event->data.small + State->eventPortState[Port].chunks, ChunkSize);
                                State->eventPortState[Port].chunks += ChunkSize;
                                Size += ChunkSize;
                            }
                            
                            else
                            {
                                size_t ChunkSize = CCDataGetSize(Event->data.big) - State->eventPortState[Port].chunks;
                                
                                if (ChunkSize > State->eventPortState[Port].chunkBatchSize) ChunkSize = State->eventPortState[Port].chunkBatchSize;
                                
                                CCDataReadBuffer(Event->data.big, State->eventPortState[Port].chunks, ChunkSize, &State->eventPortState[Port].message[Size]);
                                State->eventPortState[Port].chunks += ChunkSize;
                                Size += ChunkSize;
                            }
                            
                            if (State->eventPortState[Port].chunks == Event->data.size) State->eventPortState[Port].chunks = 0;
                            else NextIndex = 0;
                            break;
                            
                        case HKHubModuleDebugControllerDeviceEventTypeDeviceConnected:
                            //[8:4] [device:12] connected
                            break;
                            
                        case HKHubModuleDebugControllerDeviceEventTypeDeviceDisconnected:
                            //[9:4] [device:12] disconnected
                            break;
                            
                    }
                    
                    *Message = (HKHubArchPortMessage){
                        .memory = State->eventPortState[Port].message,
                        .offset = 0,
                        .size = Size
                    };
                    
                    if (!HKHubArchPortIsReady(HKHubArchPortConnectionGetOppositePort(Connection, Device, Port))) return HKHubArchPortResponseDefer;
                    
                    CCBigIntFastAdd(&State->eventPortState[Port].index, NextIndex);
                    
                    return HKHubArchPortResponseSuccess;
                }
                
                else if (Result == CCComparisonResultDescending)
                {
                    Skip[Loop] |= HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_BUFFER_SKIP_FLAG;
                }
            }
        }
        
        CC_TEMP_Free(Skip);
    }
    
    return HKHubArchPortResponseTimeout;
}

static void HKHubModuleDebugControllerStateDestructor(HKHubModuleDebugControllerState *State)
{
    for (size_t Loop = 0, Count = CCArrayGetCount(State->devices); Loop < Count; Loop++)
    {
        HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, Loop);
        
        if (Device->events.buffer)
        {
            for (size_t Loop2 = 0, Count2 = CCArrayGetCount(Device->events.buffer); Loop2 < Count2; Loop2++)
            {
                HKHubModuleDebugControllerDeviceEventDestructor(CCArrayGetElementAtIndex(Device->events.buffer, Loop2));
            }
        }
        
        switch (Device->type)
        {
            case HKHubModuleDebugControllerDeviceTypeProcessor:
                Device->processor->state.debug.operation = NULL;
                Device->processor->state.debug.portConnectionChange = NULL;
                Device->processor->state.debug.breakpointChange = NULL;
                Device->processor->state.debug.debugModeChange = NULL;
                
                Device->processor->state.debug.context = NULL;
                Device->processor->state.debug.extra = 0;
                
                HKHubArchProcessorSetDebugMode(Device->processor, HKHubArchProcessorDebugModeContinue);
                break;
                
            case HKHubModuleDebugControllerDeviceTypeModule:
                Device->module->debug.context = NULL;
                Device->module->debug.extra = 0;
                break;
                
            default:
                break;
        }
        
        CCArrayDestroy(Device->events.buffer);
        if (Device->name) CCStringDestroy(Device->name);
    }
    
    for (size_t Loop = 0; Loop < sizeof(State->eventPortState) / sizeof(typeof(*State->eventPortState)); Loop++)
    {
        CCBigIntFastDestroy(State->eventPortState[Loop].index);
        CC_SAFE_Free(State->eventPortState[Loop].message);
        if (State->eventPortState[Loop].filter.devices) CCArrayDestroy(State->eventPortState[Loop].filter.devices);
    }
    
    for (size_t Loop = 0; Loop < sizeof(State->queryPortState) / sizeof(typeof(*State->queryPortState)); Loop++)
    {
        if (State->queryPortState[Loop].message) CC_SAFE_Free(State->queryPortState[Loop].message);
    }
    
    CCArrayDestroy(State->devices);
    CCBigIntFastDestroy(State->sharedID);
    CCFree(State);
}

HKHubModule HKHubModuleDebugControllerCreate(CCAllocatorType Allocator)
{
    HKHubModuleDebugControllerState *State = CCMalloc(Allocator, sizeof(HKHubModuleDebugControllerState), NULL, CC_DEFAULT_ERROR_CALLBACK);
    if (State)
    {
        for (size_t Loop = 0; Loop < sizeof(State->eventPortState) / sizeof(typeof(*State->eventPortState)); Loop++)
        {
            State->eventPortState[Loop].index = CC_BIG_INT_FAST_0;
            State->eventPortState[Loop].chunks = 0;
            State->eventPortState[Loop].chunkBatchSize = HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_DATA_CHUNK_DEFAULT_SIZE;
            State->eventPortState[Loop].filter.commands = 0;
            State->eventPortState[Loop].filter.devices = NULL;
            
            CC_SAFE_Malloc(State->eventPortState[Loop].message, HKHubModuleDebugControllerEventPortMessageSize(16, HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_DATA_CHUNK_DEFAULT_SIZE),
                           CC_LOG_ERROR("Failed to create event port message buffer, due to allocation failure (%zu)", HKHubModuleDebugControllerEventPortMessageSize(16, HK_HUB_MODULE_DEBUG_CONTROLLER_EVENT_DATA_CHUNK_DEFAULT_SIZE));
                           );
        }
        
        for (size_t Loop = 0; Loop < sizeof(State->queryPortState) / sizeof(typeof(*State->queryPortState)); Loop++)
        {
            State->queryPortState[Loop].message = NULL;
            State->queryPortState[Loop].size = 0;
        }
        
        State->devices = CCArrayCreate(Allocator, sizeof(HKHubModuleDebugControllerDevice), 4);
        State->sharedID = CCBigIntFastCreate(CC_STD_ALLOCATOR);
        
        return HKHubModuleCreate(Allocator, (HKHubArchPortTransmit)HKHubModuleDebugControllerSend, (HKHubArchPortTransmit)HKHubModuleDebugControllerReceive, State, (HKHubModuleDataDestructor)HKHubModuleDebugControllerStateDestructor, NULL);
    }
    
    else CC_LOG_ERROR("Failed to create debug controller module due to allocation failure: allocation of size (%zu)", sizeof(HKHubModuleDebugControllerState));
    
    return NULL;
}

static void HKHubModuleDebugControllerInstructionHook(HKHubArchProcessor Processor, const HKHubArchInstructionState *Instruction, const uint8_t Encoding[5])
{
    HKHubModuleDebugControllerState *State = ((HKHubModule)Processor->state.debug.context)->internal;
    HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, Processor->state.debug.extra);
    
    HKHubModuleDebugControllerPushEvent(State, &Device->events, &(HKHubModuleDebugControllerDeviceEvent){
        .type = HKHubModuleDebugControllerDeviceEventTypeExecutedOperation,
        .device = (uint16_t)Device->index,
        .instruction = {
            .encoding = { Encoding[0], Encoding[1], Encoding[2], Encoding[3], Encoding[4] },
            .size = HKHubArchInstructionSizeOfEncoding(Instruction)
        }
    });
    
    if (Processor->state.debug.modified.reg & (HKHubArchInstructionRegisterGeneralPurpose | HKHubArchInstructionRegisterSpecialPurpose))
    {
        HKHubModuleDebugControllerPushEvent(State, &Device->events, &(HKHubModuleDebugControllerDeviceEvent){
            .type = HKHubModuleDebugControllerDeviceEventTypeModifyRegister,
            .device = (uint16_t)Device->index,
            .reg = Processor->state.debug.modified.reg
        });
        
        uint8_t Value;
        switch (Processor->state.debug.modified.reg)
        {
            case HKHubArchInstructionRegisterR0:
                Value = Processor->state.r[0];
                break;
                
            case HKHubArchInstructionRegisterR1:
                Value = Processor->state.r[1];
                break;
                
            case HKHubArchInstructionRegisterR2:
                Value = Processor->state.r[2];
                break;
                
            case HKHubArchInstructionRegisterR3:
                Value = Processor->state.r[3];
                break;
                
            case HKHubArchInstructionRegisterFlags:
                Value = Processor->state.flags;
                break;
                
            case HKHubArchInstructionRegisterPC:
                Value = Processor->state.pc;
                break;
                
            default:
                CCAssertLog(0, "Unsupported register type");
                break;
        }
        
        HKHubModuleDebugControllerPushEvent(State, &Device->events, &(HKHubModuleDebugControllerDeviceEvent){
            .type = HKHubModuleDebugControllerDeviceEventTypeChangedDataChunk,
            .device = (uint16_t)Device->index,
            .data = {
                .small[0] = Value,
                .size = 1
            }
        });
    }
    
    if (Processor->state.debug.modified.size)
    {
        HKHubModuleDebugControllerPushEvent(State, &Device->events, &(HKHubModuleDebugControllerDeviceEvent){
            .type = HKHubModuleDebugControllerDeviceEventTypeModifyMemory,
            .device = (uint16_t)Device->index,
            .memory = {
                .offset = Processor->state.debug.modified.offset,
                .size = Processor->state.debug.modified.size
            }
        });
        
        HKHubModuleDebugControllerDeviceEvent Event = {
            .type = HKHubModuleDebugControllerDeviceEventTypeChangedDataChunk,
            .device = (uint16_t)Device->index,
            .data = {
                .size = Processor->state.debug.modified.size
            }
        };
        
        if (Processor->state.debug.modified.size <= sizeof(Event.data.small))
        {
            CCMemoryRead(Processor->memory, sizeof(Processor->memory), Processor->state.debug.modified.offset, Processor->state.debug.modified.size, Event.data.small);
        }
        
        else
        {
            uint8_t *Bytes;
            CC_SAFE_Malloc(Bytes, Processor->state.debug.modified.size,
                           CC_LOG_ERROR("Failed to create event data chunk, due to allocation failure (%u)", Processor->state.debug.modified.size);
                           return;
                           );
            
            Event.data.big = CCDataBufferCreate(CC_STD_ALLOCATOR, CCDataBufferHintFree | CCDataHintRead, Processor->state.debug.modified.size, Bytes, NULL, NULL);
        }
        
        HKHubModuleDebugControllerPushEvent(State, &Device->events, &Event);
    }
    
    if ((Processor->state.debug.modified.reg != HKHubArchInstructionRegisterFlags) && (HKHubArchInstructionGetModifiedFlags(Instruction)))
    {
        HKHubModuleDebugControllerPushEvent(State, &Device->events, &(HKHubModuleDebugControllerDeviceEvent){
            .type = HKHubModuleDebugControllerDeviceEventTypeModifyRegister,
            .device = (uint16_t)Device->index,
            .reg = HKHubArchInstructionRegisterFlags
        });
        
        HKHubModuleDebugControllerPushEvent(State, &Device->events, &(HKHubModuleDebugControllerDeviceEvent){
            .type = HKHubModuleDebugControllerDeviceEventTypeChangedDataChunk,
            .device = (uint16_t)Device->index,
            .data = {
                .small[0] = Processor->state.flags,
                .size = 1
            }
        });
    }
    
    if ((Processor->state.debug.modified.reg != HKHubArchInstructionRegisterPC) && (!(HKHubArchInstructionGetControlFlow(Instruction) & HKHubArchInstructionControlFlowEffectPause)))
    {
        HKHubModuleDebugControllerPushEvent(State, &Device->events, &(HKHubModuleDebugControllerDeviceEvent){
            .type = HKHubModuleDebugControllerDeviceEventTypeModifyRegister,
            .device = (uint16_t)Device->index,
            .reg = HKHubArchInstructionRegisterPC
        });
        
        HKHubModuleDebugControllerPushEvent(State, &Device->events, &(HKHubModuleDebugControllerDeviceEvent){
            .type = HKHubModuleDebugControllerDeviceEventTypeChangedDataChunk,
            .device = (uint16_t)Device->index,
            .data = {
                .small[0] = Processor->state.pc,
                .size = 1
            }
        });
    }
}

static void HKHubModuleDebugControllerPortConnectionChangeHook(void *DebuggedDevice, HKHubArchPortID Port, HKHubModuleDebugControllerState *State, size_t Index, HKHubArchPortConnection Conn)
{
    HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, Index);
    
    HKHubModuleDebugControllerDeviceEvent Event = {
        .type = HKHubModuleDebugControllerDeviceEventTypeChangePortConnection,
        .device = (uint16_t)Device->index,
        .connection = {
            .port = Port,
            .target = {
                .device = 0xfff,
                .port = 0
            },
            .connected = FALSE
        }
    };
    
    if (Conn)
    {
        const HKHubArchPort *OppositePort = HKHubArchPortConnectionGetOppositePort(Conn, DebuggedDevice, Port);
        
        Event.connection.target.port = OppositePort->id;
        // TODO: Add callback to HKHubArchPort to get debug context (only safe if don't allow other debug contexts)
        uint16_t ConnectedDeviceID = 0xfff;
        for (size_t Loop2 = 0, Count2 = CCArrayGetCount(State->devices); Loop2 < Count2; Loop2++)
        {
            HKHubModuleDebugControllerDevice *ConnectedDevice = CCArrayGetElementAtIndex(State->devices, Loop2);
            if (ConnectedDevice)
            {
                if ((ConnectedDevice->processor == OppositePort->device) || (ConnectedDevice->module == OppositePort->device))
                {
                    ConnectedDeviceID = Loop2;
                    break;
                }
            }
        }
        
        Event.connection.target.device = ConnectedDeviceID;
        Event.connection.connected = TRUE;
    }
    
    HKHubModuleDebugControllerPushEvent(State, &Device->events, &Event);
}

static void HKHubModuleDebugControllerProcessorPortConnectionChangeHook(HKHubArchProcessor Processor, HKHubArchPortID Port)
{
    HKHubModuleDebugControllerPortConnectionChangeHook(Processor, Port, ((HKHubModule)Processor->state.debug.context)->internal, Processor->state.debug.extra, HKHubArchProcessorGetPortConnection(Processor, Port));
}

static void HKHubModuleDebugControllerModulePortConnectionChangeHook(HKHubModule Module, HKHubArchPortID Port)
{
    HKHubModuleDebugControllerPortConnectionChangeHook(Module, Port, ((HKHubModule)Module->debug.context)->internal, Module->debug.extra, HKHubModuleGetPortConnection(Module, Port));
}

static void HKHubModuleDebugControllerBreakpointChangeHook(HKHubArchProcessor Processor, HKHubArchProcessorDebugBreakpoint Breakpoint, uint8_t Offset)
{
    HKHubModuleDebugControllerState *State = ((HKHubModule)Processor->state.debug.context)->internal;
    HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, Processor->state.debug.extra);
    
    HKHubModuleDebugControllerPushEvent(State, &Device->events, &(HKHubModuleDebugControllerDeviceEvent){
        .type = HKHubModuleDebugControllerDeviceEventTypeChangeBreakpoint,
        .device = (uint16_t)Device->index,
        .breakpoint = {
            .offset = Offset,
            .access = Breakpoint
        }
    });
}

static void HKHubModuleDebugControllerDebugModeChangeHook(HKHubArchProcessor Processor)
{
    HKHubModuleDebugControllerState *State = ((HKHubModule)Processor->state.debug.context)->internal;
    HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, Processor->state.debug.extra);
    
    _Static_assert((HKHubArchProcessorDebugModePause == HKHubModuleDebugControllerDeviceEventTypePause) &&
                   (HKHubArchProcessorDebugModeContinue == HKHubModuleDebugControllerDeviceEventTypeRun), "Expects enums to match");
    
    HKHubModuleDebugControllerPushEvent(State, &Device->events, &(HKHubModuleDebugControllerDeviceEvent){
        .type = (HKHubModuleDebugControllerDeviceEventType)Processor->state.debug.mode,
        .device = (uint16_t)Device->index
    });
}

void HKHubModuleDebugControllerConnectProcessor(HKHubModule Controller, HKHubArchProcessor Processor, CCString Name)
{
    CCAssertLog(Controller, "Controller must not be null");
    CCAssertLog(Processor, "Processor must not be null");
    CCAssertLog(!Processor->state.debug.context, "Processor must not already be debugged");
    
    HKHubModuleDebugControllerState *State = Controller->internal;
    const size_t Index = CCArrayAppendElement(State->devices, &(HKHubModuleDebugControllerDevice){
        .type = HKHubModuleDebugControllerDeviceTypeProcessor,
        .processor = Processor,
        .events = {
            .buffer = CCArrayCreate(CC_STD_ALLOCATOR, sizeof(HKHubModuleDebugControllerDeviceEvent), 16),
            .count = 0
        },
        .name = (Name ? CCStringCopy(Name) : 0)
    });
    
    HKHubArchProcessorSetDebugMode(Processor, HKHubArchProcessorDebugModePause);
    
    HKHubModuleDebugControllerDevice * const Device = CCArrayGetElementAtIndex(State->devices, Index);
    
    Processor->state.debug.context = Controller;
    Processor->state.debug.extra = Index;
    
    Processor->state.debug.operation = HKHubModuleDebugControllerInstructionHook;
    Processor->state.debug.portConnectionChange = HKHubModuleDebugControllerProcessorPortConnectionChangeHook;
    Processor->state.debug.breakpointChange = HKHubModuleDebugControllerBreakpointChangeHook;
    Processor->state.debug.debugModeChange = HKHubModuleDebugControllerDebugModeChangeHook;
    
    CCAssertLog(Index == (uint16_t)Index, "Too many devices connected");
    
    HKHubModuleDebugControllerPushEvent(State, &Device->events, &(HKHubModuleDebugControllerDeviceEvent){
        .type = HKHubModuleDebugControllerDeviceEventTypeDeviceConnected,
        .device = (uint16_t)(Device->index = Index)
    });
}

void HKHubModuleDebugControllerDisconnectProcessor(HKHubModule Controller, HKHubArchProcessor Processor)
{
    CCAssertLog(Controller, "Controller must not be null");
    CCAssertLog(Processor, "Processor must not be null");
    CCAssertLog(Processor->state.debug.context == Controller, "Processor must be connected to the controller");
    
    HKHubModuleDebugControllerState *State = ((HKHubModule)Processor->state.debug.context)->internal;
    HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, Processor->state.debug.extra);
    Device->type = HKHubModuleDebugControllerDeviceTypeNone;
    Device->processor = NULL;
    
    HKHubModuleDebugControllerPushEvent(State, &Device->events, &(HKHubModuleDebugControllerDeviceEvent){
        .type = HKHubModuleDebugControllerDeviceEventTypeDeviceDisconnected,
        .device = (uint16_t)Device->index
    });
    
    Processor->state.debug.operation = NULL;
    Processor->state.debug.portConnectionChange = NULL;
    Processor->state.debug.breakpointChange = NULL;
    Processor->state.debug.debugModeChange = NULL;
    
    Processor->state.debug.context = NULL;
    Processor->state.debug.extra = 0;
    
    HKHubArchProcessorSetDebugMode(Processor, HKHubArchProcessorDebugModeContinue);
}

void HKHubModuleDebugControllerConnectModule(HKHubModule Controller, HKHubModule Module, CCString Name)
{
    CCAssertLog(Controller, "Controller must not be null");
    CCAssertLog(Module, "Module must not be null");
    CCAssertLog(!Module->debug.context, "Module must not already be debugged");
    
    HKHubModuleDebugControllerState *State = Controller->internal;
    const size_t Index = CCArrayAppendElement(State->devices, &(HKHubModuleDebugControllerDevice){
        .type = HKHubModuleDebugControllerDeviceTypeModule,
        .module = Module,
        .events = {
            .buffer = CCArrayCreate(CC_STD_ALLOCATOR, sizeof(HKHubModuleDebugControllerDeviceEvent), 4),
            .count = 0
        },
        .name = (Name ? CCStringCopy(Name) : 0)
    });
    
    HKHubModuleDebugControllerDevice * const Device = CCArrayGetElementAtIndex(State->devices, Index);
    
    Module->debug.context = Controller;
    Module->debug.extra = Index;
    
    Module->debug.portConnectionChange = HKHubModuleDebugControllerModulePortConnectionChangeHook;
    
    CCAssertLog(Index == (uint16_t)Index, "Too many devices connected");
    
    HKHubModuleDebugControllerPushEvent(State, &Device->events, &(HKHubModuleDebugControllerDeviceEvent){
        .type = HKHubModuleDebugControllerDeviceEventTypeDeviceConnected,
        .device = (uint16_t)(Device->index = Index)
    });
}

void HKHubModuleDebugControllerDisconnectModule(HKHubModule Controller, HKHubModule Module)
{
    CCAssertLog(Controller, "Controller must not be null");
    CCAssertLog(Module, "Module must not be null");
    CCAssertLog(Module->debug.context == Controller, "Module must be connected to the controller");
    
    HKHubModuleDebugControllerState *State = ((HKHubModule)Module->debug.context)->internal;
    HKHubModuleDebugControllerDevice *Device = CCArrayGetElementAtIndex(State->devices, Module->debug.extra);
    Device->type = HKHubModuleDebugControllerDeviceTypeNone;
    Device->module = NULL;
    
    HKHubModuleDebugControllerPushEvent(State, &Device->events, &(HKHubModuleDebugControllerDeviceEvent){
        .type = HKHubModuleDebugControllerDeviceEventTypeDeviceDisconnected,
        .device = (uint16_t)Device->index
    });
    
    Module->debug.portConnectionChange = NULL;
    
    Module->debug.context = NULL;
    Module->debug.extra = 0;
}
