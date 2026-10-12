/*
 *  Copyright (c) 2017, Stefan Johnson
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

#ifndef HackingGame_HubDebuggerComponent_h
#define HackingGame_HubDebuggerComponent_h

#include "Base.h"
#include "HubSystem.h"

#define HK_HUB_DEBUGGER_COMPONENT_ID (HKHubTypeDebugger | HK_HUB_COMPONENT_FLAG)

typedef struct {
    CC_COMPONENT_INHERIT(CCComponentClass);
} HKHubDebuggerComponentClass, *HKHubDebuggerComponentPrivate;

typedef struct {
    HKHubArchProcessorDebugBreakpoint breakpoint;
    uint8_t offset;
} HKHubDebuggerComponentMessageBreakpoint;

#define HK_HUB_DEBUGGER_COMPONENT_EXIT_MESSAGE_ID 'exit'
#define HK_HUB_DEBUGGER_COMPONENT_PAUSE_MESSAGE_ID 'paus'
#define HK_HUB_DEBUGGER_COMPONENT_CONTINUE_MESSAGE_ID 'cont'
#define HK_HUB_DEBUGGER_COMPONENT_STEP_MESSAGE_ID 'step'
#define HK_HUB_DEBUGGER_COMPONENT_BREAKPOINT_MESSAGE_ID 'brk\0'
#define HK_HUB_DEBUGGER_COMPONENT_TOGGLE_BREAKPOINT_MESSAGE_ID 'tbrk'
#define HK_HUB_DEBUGGER_COMPONENT_CLEAR_BREAKPOINT_MESSAGE_ID 'cbrk'

void HKHubDebuggerComponentRegister(void);
void HKHubDebuggerComponentDeregister(void);

/*!
 * @brief Initialize the debugger component.
 * @param Component The component to be initialized.
 * @param id The component ID.
 */
static inline void HKHubDebuggerComponentInitialize(CCComponent Component, CCComponentID id);

/*!
 * @brief Deallocate the debugger component.
 * @param Component The component to be deallocated.
 */
static inline void HKHubDebuggerComponentDeallocate(CCComponent Component);


#pragma mark -

static inline void HKHubDebuggerComponentInitialize(CCComponent Component, CCComponentID id)
{
    CCComponentInitialize(Component, id);
}

static inline void HKHubDebuggerComponentDeallocate(CCComponent Component)
{
    CCComponentDeallocate(Component);
}

#endif
