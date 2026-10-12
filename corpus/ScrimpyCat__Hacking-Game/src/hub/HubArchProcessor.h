/*
 *  Copyright (c) 2016, Stefan Johnson
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

#ifndef HackingGame_HubArchProcessor_h
#define HackingGame_HubArchProcessor_h

#include "Base.h"
#include "HubArchBinary.h"
#include "HubArchPort.h"
#include "HubArchInstructionType.h"
#include "HubArchExecutionGraph.h"
#include "HubArchJIT.h"

typedef enum {
    HKHubArchProcessorStatusRunning = 0,
    HKHubArchProcessorStatusInsufficientCycles = (1 << 1),
    HKHubArchProcessorStatusResumable = (1 << 2),
    HKHubArchProcessorStatusIdle = (1 << 3),
    HKHubArchProcessorStatusTrap = (1 << 4)
} HKHubArchProcessorStatus;

typedef enum {
    HKHubArchProcessorDebugModeContinue,
    HKHubArchProcessorDebugModePause
} HKHubArchProcessorDebugMode;

typedef enum {
    HKHubArchProcessorDebugBreakpointNone,
    HKHubArchProcessorDebugBreakpointRead = (1 << 0),
    HKHubArchProcessorDebugBreakpointWrite = (1 << 1)
} HKHubArchProcessorDebugBreakpoint;

/*!
 * @brief The processor.
 * @description Allows @b CCRetain.
 */
typedef struct HKHubArchProcessorInfo *HKHubArchProcessor;

/*!
 * @brief Get the current state after each executed instruction.
 * @param Processor The processor that was executed.
 * @param Instruction The instruction state of the executed operation.
 * @param Encoding The encoded instruction.
 */
typedef void (*HKHubArchProcessorDebugOperationCallback)(HKHubArchProcessor Processor, const HKHubArchInstructionState *Instruction, const uint8_t Encoding[5]);

/*!
 * @brief Callback to hook any port connection changes.
 * @param Processor The processor that was executed.
 * @param Port The port of the processor that was changed.
 */
typedef void (*HKHubArchProcessorDebugPortConnectionChangeCallback)(HKHubArchProcessor Processor, HKHubArchPortID Port);

/*!
 * @brief Callback to hook any breakpoint changes.
 * @param Processor The processor that had a breakpoint changed.
 * @param Breakpoint The type of breakpoint change.
 * @param Offset The offset of the breapoint change.
 */
typedef void (*HKHubArchProcessorDebugBreakpointChangeCallback)(HKHubArchProcessor Processor, HKHubArchProcessorDebugBreakpoint Breakpoint, uint8_t Offset);

/*!
 * @brief Callback to hook any debug mode changes.
 * @param Processor The processor that had its debug mode changed.
 */
typedef void (*HKHubArchProcessorDebugModeChangeCallback)(HKHubArchProcessor Processor);

typedef struct HKHubArchProcessorInfo {
    CCDictionary(HKHubArchPortID, HKHubArchPortConnection) ports;
    struct {
        HKHubArchPortID port;
        HKHubArchPortMessage data;
        uint8_t offset;
        enum {
            HKHubArchProcessorMessageClear,
            HKHubArchProcessorMessageComplete,
            HKHubArchProcessorMessageSend,
            HKHubArchProcessorMessageReceive
        } type;
        size_t timestamp;
        size_t wait;
    } message;
    struct {
        uint8_t r[4];
        uint8_t pc;
        uint8_t flags;
        struct {
            HKHubArchProcessorDebugMode mode;
            size_t step;
            CCDictionary(uint8_t, HKHubArchProcessorDebugBreakpoint) breakpoints;
            struct {
                HKHubArchInstructionRegister reg;
                uint8_t offset;
                uint8_t size;
            } modified;
            struct {
                void *context;
                uintptr_t extra;
                HKHubArchProcessorDebugOperationCallback operation;
                HKHubArchProcessorDebugPortConnectionChangeCallback portConnectionChange;
                HKHubArchProcessorDebugBreakpointChangeCallback breakpointChange;
                HKHubArchProcessorDebugModeChangeCallback debugModeChange;
            };
        } debug;
    } state;
    struct {
        HKHubArchExecutionGraph graph;
        HKHubArchJIT jit;
    } cache;
    size_t cycles;
    double unusedTime;
    HKHubArchProcessorStatus status;
    uint8_t memory[256];
} HKHubArchProcessorInfo;

typedef enum {
    HKHubArchProcessorFlagsZero = (1 << 0),
    HKHubArchProcessorFlagsCarry = (1 << 1),
    HKHubArchProcessorFlagsSign = (1 << 2),
    HKHubArchProcessorFlagsOverflow = (1 << 3),
    
    HKHubArchProcessorFlagsMask = HKHubArchProcessorFlagsZero | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsOverflow
} HKHubArchProcessorFlags;

/*!
 * @brief The clock rate of the processor;
 */
extern const double HKHubArchProcessorHertz;

/*!
 * @brief The memory read speed of the processor;
 */
extern const size_t HKHubArchProcessorSpeedMemoryRead;

/*!
 * @brief The memory write speed of the processor;
 */
extern const size_t HKHubArchProcessorSpeedMemoryWrite;

/*!
 * @brief The port transmission speed of the processor;
 */
extern const size_t HKHubArchProcessorSpeedPortTransmission;


/*!
 * @brief Create a hub.
 * @param Allocator The allocator to be used.
 * @param Binary The binary to initialise the processor with.
 * @return The processor. Must be destroyed to free memory.
 */
CC_NEW HKHubArchProcessor HKHubArchProcessorCreate(CCAllocatorType Allocator, HKHubArchBinary Binary);

/*!
 * @brief Destroy a processor.
 * @param Processor The processor to be destroyed.
 */
void HKHubArchProcessorDestroy(HKHubArchProcessor CC_DESTROY(Processor));

/*!
 * @brief Reset the processor's state.
 * @param Processor The processor to reset.
 * @param Binary The binary to initialise the processor with.
 */
void HKHubArchProcessorReset(HKHubArchProcessor Processor, HKHubArchBinary Binary);

/*!
 * @brief Reset the processor's debug state.
 * @param Processor The processor to reset.
 */
void HKHubArchProcessorDebugReset(HKHubArchProcessor Processor);

/*!
 * @brief Reset the processor cache.
 * @param Processor The processor to reset.
 */
void HKHubArchProcessorCacheReset(HKHubArchProcessor Processor);

/*!
 * @brief Set the cycles the processor should run.
 * @param Processor The processor to allocate the time to.
 * @param Cycles The number of cycles to run.
 */
void HKHubArchProcessorSetCycles(HKHubArchProcessor Processor, size_t Cycles);

/*!
 * @brief Add the amount of time the processor should run for.
 * @param Processor The processor to allocate the time to.
 * @param Seconds The time in seconds the processor should run for.
 */
void HKHubArchProcessorAddProcessingTime(HKHubArchProcessor Processor, double Seconds);

/*!
 * @brief Add a connection to the processor.
 * @param Processor The processor to add the connection to.
 * @param Port The port of the processor the connection belongs to.
 * @param Connection The connection to add to the process. A reference to the connection is
 *        retained.
 */
void HKHubArchProcessorConnect(HKHubArchProcessor Processor, HKHubArchPortID Port, HKHubArchPortConnection CC_RETAIN(Connection));

/*!
 * @brief Disconnect a connection from the processor.
 * @description Causes the connection to be disconnected completely from either interface.
 * @param Processor The processor to remove the connection from.
 * @param Port The port of the processor the connection belongs to.
 */
void HKHubArchProcessorDisconnect(HKHubArchProcessor Processor, HKHubArchPortID Port);

/*!
 * @brief Get an interfaceable port reference from the processor.
 * @param Processor The processor to get the port of.
 * @param Port The port of the processor.
 * @return The port interface.
 */
HKHubArchPort HKHubArchProcessorGetPort(HKHubArchProcessor Processor, HKHubArchPortID Port);

/*!
 * @brief Get the current connection for the specified port of the processor.
 * @param Processor The processor to get the connection of.
 * @param Port The port of the processor.
 * @return The connection if one exists, otherwise NULL.
 */
HKHubArchPortConnection HKHubArchProcessorGetPortConnection(HKHubArchProcessor Processor, HKHubArchPortID Port);

/*!
 * @brief Run the processor.
 * @param Processor The processor to be run.
 */
void HKHubArchProcessorRun(HKHubArchProcessor Processor);

/*!
 * @brief Set the number of instructions the processor should step in debug mode.
 * @param Processor The processor to step.
 * @param Count The number of instructions to step over.
 */
void HKHubArchProcessorStep(HKHubArchProcessor Processor, size_t Count);

/*!
 * @brief Set the debug mode of the processor.
 * @param Processor The processor to have its debug mode set.
 * @param Mode The debug mode to be used.
 */
void HKHubArchProcessorSetDebugMode(HKHubArchProcessor Processor, HKHubArchProcessorDebugMode Mode);

/*!
 * @brief Set a breakpoint in the processor.
 * @description When hit will cause the debug mode to be switched to @b HKHubArchProcessorDebugModePause.
 * @param Processor The processor to have a breakpoint set.
 * @param Breakpoint The type of breakpoint to be set. Use @b HKHubArchProcessorDebugBreakpointNone to
 *        disable a breakpoint at a given offset.
 *
 * @param Offset The offset the breakpoint should be located at.
 */
void HKHubArchProcessorSetBreakpoint(HKHubArchProcessor Processor, HKHubArchProcessorDebugBreakpoint Breakpoint, uint8_t Offset);

/*!
 * @brief Remove all breakpoints in the processor.
 * @param Processor The processor to remove the breakpoints of.
 */
void HKHubArchProcessorClearBreakpoints(HKHubArchProcessor Processor);

/*!
 * @brief Generate the execution cache for the processor.
 * @param Processor The processor to create the execution cache of.
 * @param Options The options to control how the JIT should be generated.
 */
void HKHubArchProcessorCache(HKHubArchProcessor Processor, HKHubArchJITOptions Options);

/*!
 * @brief Whether the processor can continue to be executed or not.
 * @param Processor The processor to check has finished.
 */
static inline _Bool HKHubArchProcessorIsRunning(HKHubArchProcessor Processor);

#pragma mark -

static inline _Bool HKHubArchProcessorIsRunning(HKHubArchProcessor Processor)
{
    return (Processor->status == HKHubArchProcessorStatusRunning) && (Processor->cycles) && (((Processor->state.debug.mode != HKHubArchProcessorDebugModePause) || (Processor->state.debug.step)));
}

#endif
