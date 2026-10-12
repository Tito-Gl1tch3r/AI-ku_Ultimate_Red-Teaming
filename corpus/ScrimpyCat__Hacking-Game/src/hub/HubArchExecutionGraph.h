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

#ifndef HackingGame_HubArchInstructionGraph_h
#define HackingGame_HubArchInstructionGraph_h

#include "Base.h"
#include "HubArchInstructionType.h"

typedef struct {
    uint8_t offset;
    HKHubArchInstructionState state;
    CCLinkedList(HKHubArchExecutionGraphInstruction) jump;
} HKHubArchExecutionGraphInstruction;

typedef struct {
    uint8_t start;
    uint8_t count;
} HKHubArchExecutionGraphRange;

typedef struct {
    CCArray(CCLinkedList(HKHubArchExecutionGraphInstruction)) block;
    CCArray(HKHubArchExecutionGraphRange) range;
} HKHubArchExecutionGraphInfo;

/*!
 * @brief The execution graph.
 * @description Allows @b CCRetain.
 */
typedef HKHubArchExecutionGraphInfo *HKHubArchExecutionGraph;

CC_NEW HKHubArchExecutionGraph HKHubArchExecutionGraphCreate(CCAllocatorType Allocator, uint8_t Memory[256], uint8_t PC);

void HKHubArchExecutionGraphDestroy(HKHubArchExecutionGraph CC_DESTROY(Graph));

#endif
