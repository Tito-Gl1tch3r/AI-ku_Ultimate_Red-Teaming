/*
 *  Copyright (c) 2019, Stefan Johnson
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

#ifndef HackingGame_Base_h
#define HackingGame_Base_h

#define HK_TYPES(func, ...) \
B2_TYPES(func, __VA_ARGS__); \
func(__VA_ARGS__, HKHubDebuggerComponentMessageBreakpoint); \
func(__VA_ARGS__, HKHubPortConnectionEntityMapping); \
func(__VA_ARGS__, HKHubType); \
func(__VA_ARGS__, HKHubModule); \
func(__VA_ARGS__, HKHubModuleWirelessTransceiverPacketSignature); \
func(__VA_ARGS__, HKHubModuleWirelessTransceiverPacket); \
func(__VA_ARGS__, HKHubModuleDisplayBufferConverter); \
func(__VA_ARGS__, HKHubArchInstructionOperand); \
func(__VA_ARGS__, HKHubArchInstructionMemoryOperation); \
func(__VA_ARGS__, HKHubArchInstructionRegister); \
func(__VA_ARGS__, HKHubArchInstructionMemory); \
func(__VA_ARGS__, HKHubArchInstructionOperandValue); \
func(__VA_ARGS__, HKHubArchInstructionState); \
func(__VA_ARGS__, HKHubArchInstructionOperationResult); \
func(__VA_ARGS__, HKHubArchAssemblyASTType); \
func(__VA_ARGS__, HKHubArchAssemblyASTNode); \
func(__VA_ARGS__, HKHubArchAssemblyASTError); \
func(__VA_ARGS__, HKHubArchBinaryNamedPort); \
func(__VA_ARGS__, HKHubArchBinary); \
func(__VA_ARGS__, HKHubArchProcessorStatus); \
func(__VA_ARGS__, HKHubArchProcessorDebugMode); \
func(__VA_ARGS__, HKHubArchProcessorDebugBreakpoint); \
func(__VA_ARGS__, HKHubArchProcessor); \
func(__VA_ARGS__, HKHubArchProcessorFlags); \
func(__VA_ARGS__, HKHubArchPortConnection); \
func(__VA_ARGS__, HKHubArchPortID); \
func(__VA_ARGS__, HKHubArchPortDevice); \
func(__VA_ARGS__, HKHubArchPortMessage); \
func(__VA_ARGS__, HKHubArchPortResponse); \
func(__VA_ARGS__, HKHubArchPort); \
func(__VA_ARGS__, HKHubArchScheduler);

#define HK_TYPES_(func, ...) \
B2_TYPES_(func, __VA_ARGS__); \
func(__VA_ARGS__, HKHubDebuggerComponentMessageBreakpoint); \
func(__VA_ARGS__, HKHubPortConnectionEntityMapping); \
func(__VA_ARGS__, HKHubType); \
func(__VA_ARGS__, HKHubModule); \
func(__VA_ARGS__, HKHubModuleWirelessTransceiverPacketSignature); \
func(__VA_ARGS__, HKHubModuleWirelessTransceiverPacket); \
func(__VA_ARGS__, HKHubModuleDisplayBufferConverter); \
func(__VA_ARGS__, HKHubArchInstructionOperand); \
func(__VA_ARGS__, HKHubArchInstructionMemoryOperation); \
func(__VA_ARGS__, HKHubArchInstructionRegister); \
func(__VA_ARGS__, HKHubArchInstructionMemory); \
func(__VA_ARGS__, HKHubArchInstructionOperandValue); \
func(__VA_ARGS__, HKHubArchInstructionState); \
func(__VA_ARGS__, HKHubArchInstructionOperationResult); \
func(__VA_ARGS__, HKHubArchAssemblyASTType); \
func(__VA_ARGS__, HKHubArchAssemblyASTNode); \
func(__VA_ARGS__, HKHubArchAssemblyASTError); \
func(__VA_ARGS__, HKHubArchBinaryNamedPort); \
func(__VA_ARGS__, HKHubArchBinary); \
func(__VA_ARGS__, HKHubArchProcessorStatus); \
func(__VA_ARGS__, HKHubArchProcessorDebugMode); \
func(__VA_ARGS__, HKHubArchProcessorDebugBreakpoint); \
func(__VA_ARGS__, HKHubArchProcessor); \
func(__VA_ARGS__, HKHubArchProcessorFlags); \
func(__VA_ARGS__, HKHubArchPortConnection); \
func(__VA_ARGS__, HKHubArchPortID); \
func(__VA_ARGS__, HKHubArchPortDevice); \
func(__VA_ARGS__, HKHubArchPortMessage); \
func(__VA_ARGS__, HKHubArchPortResponse); \
func(__VA_ARGS__, HKHubArchPort); \
func(__VA_ARGS__, HKHubArchScheduler);

#ifndef CC_CUSTOM_TYPES
#define CC_CUSTOM_TYPES HK_TYPES
#endif

#ifndef CC_CUSTOM_TYPES_
#define CC_CUSTOM_TYPES_ HK_TYPES_
#endif

#ifndef CC_QUICK_COMPILE
#define CC_QUICK_COMPILE
#define CC_CONTAINER_ENABLE
#define CC_CONTAINER_DISABLE_PRESETS

#include "ContainerTypes.h"
#endif

#include <Blob2D/Blob2D.h>

/*!
 * @brief The game's asset path.
 * @note This should only be set if using a different project structure.
 */
extern FSPath HKAssetPath;

#endif
