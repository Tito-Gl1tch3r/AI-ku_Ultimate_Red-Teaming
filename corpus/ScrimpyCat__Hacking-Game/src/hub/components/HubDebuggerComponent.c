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

#include "HubDebuggerComponent.h"
#include "HubProcessorComponent.h"

const CCString HKHubDebuggerComponentName = CC_STRING("debugger");

static const CCComponentExpressionDescriptor HKHubDebuggerComponentDescriptor = {
    .id = HK_HUB_DEBUGGER_COMPONENT_ID,
    .initialize = NULL,
    .deserialize = NULL,
    .serialize = NULL
};

static void HKHubDebuggerComponentMessageHandler(CCComponent Debugger, CCMessage *Message)
{
    switch (Message->id)
    {
        case HK_HUB_DEBUGGER_COMPONENT_EXIT_MESSAGE_ID:
            CCComponentSystemRemoveComponent(Debugger);
            break;
            
        case HK_HUB_DEBUGGER_COMPONENT_PAUSE_MESSAGE_ID:
        {
            CC_COLLECTION_FOREACH(CCComponent, Component, CCEntityGetComponents(CCComponentGetEntity(Debugger)))
            {
                if ((CCComponentGetID(Component) & HKHubTypeMask) == HKHubTypeProcessor)
                {
                    HKHubArchProcessor Target = HKHubProcessorComponentGetProcessor(Component);
                    HKHubArchProcessorSetDebugMode(Target, HKHubArchProcessorDebugModePause);
                    break;
                }
            }
            break;
        }
            
        case HK_HUB_DEBUGGER_COMPONENT_CONTINUE_MESSAGE_ID:
        {
            CC_COLLECTION_FOREACH(CCComponent, Component, CCEntityGetComponents(CCComponentGetEntity(Debugger)))
            {
                if ((CCComponentGetID(Component) & HKHubTypeMask) == HKHubTypeProcessor)
                {
                    HKHubArchProcessor Target = HKHubProcessorComponentGetProcessor(Component);
                    HKHubArchProcessorStep(Target, 1);
                    HKHubArchProcessorSetDebugMode(Target, HKHubArchProcessorDebugModeContinue);
                    break;
                }
            }
            break;
        }
            
        case HK_HUB_DEBUGGER_COMPONENT_STEP_MESSAGE_ID:
        {
            CC_COLLECTION_FOREACH(CCComponent, Component, CCEntityGetComponents(CCComponentGetEntity(Debugger)))
            {
                if ((CCComponentGetID(Component) & HKHubTypeMask) == HKHubTypeProcessor)
                {
                    HKHubArchProcessor Target = HKHubProcessorComponentGetProcessor(Component);
                    HKHubArchProcessorStep(Target, 1);
                    break;
                }
            }
            break;
        }
            
        case HK_HUB_DEBUGGER_COMPONENT_TOGGLE_BREAKPOINT_MESSAGE_ID:
        {
            CC_COLLECTION_FOREACH(CCComponent, Component, CCEntityGetComponents(CCComponentGetEntity(Debugger)))
            {
                if ((CCComponentGetID(Component) & HKHubTypeMask) == HKHubTypeProcessor)
                {
                    HKHubArchProcessor Target = HKHubProcessorComponentGetProcessor(Component);
                    const HKHubDebuggerComponentMessageBreakpoint *Data = CCMessageGetData(Message);
                    
                    HKHubArchProcessorDebugBreakpoint CurrentBP = 0;
                    if (Target->state.debug.breakpoints)
                    {
                        HKHubArchProcessorDebugBreakpoint *Breakpoint = CCDictionaryGetValue(Target->state.debug.breakpoints, &Data->offset);
                        if (Breakpoint) CurrentBP = *Breakpoint;
                    }
                    
                    HKHubArchProcessorSetBreakpoint(Target, CurrentBP ^ Data->breakpoint, Data->offset);
                    break;
                }
            }
            break;
        }
            
        case HK_HUB_DEBUGGER_COMPONENT_BREAKPOINT_MESSAGE_ID:
        {
            CC_COLLECTION_FOREACH(CCComponent, Component, CCEntityGetComponents(CCComponentGetEntity(Debugger)))
            {
                if ((CCComponentGetID(Component) & HKHubTypeMask) == HKHubTypeProcessor)
                {
                    HKHubArchProcessor Target = HKHubProcessorComponentGetProcessor(Component);
                    const HKHubDebuggerComponentMessageBreakpoint *Data = CCMessageGetData(Message);
                    
                    HKHubArchProcessorSetBreakpoint(Target, Data->breakpoint, Data->offset);
                    break;
                }
            }
            break;
        }
            
        case HK_HUB_DEBUGGER_COMPONENT_CLEAR_BREAKPOINT_MESSAGE_ID:
        {
            CC_COLLECTION_FOREACH(CCComponent, Component, CCEntityGetComponents(CCComponentGetEntity(Debugger)))
            {
                if ((CCComponentGetID(Component) & HKHubTypeMask) == HKHubTypeProcessor)
                {
                    HKHubArchProcessor Target = HKHubProcessorComponentGetProcessor(Component);
                    HKHubArchProcessorClearBreakpoints(Target);
                    break;
                }
            }
            break;
        }
    }
}

static _Bool HKHubDebuggerComponentMessagePostBreakpoint(CCMessageRouter *Router, CCMessageID id, CCExpression Args);

static const struct {
    CCString name;
    CCMessageExpressionDescriptor descriptor;
} HKHubDebuggerComponentMessageDescriptors[] = {
    { .name = CC_STRING(":debug-exit"), .descriptor = { .id = HK_HUB_DEBUGGER_COMPONENT_EXIT_MESSAGE_ID, .post = CCMessageExpressionBasicPoster } },
    { .name = CC_STRING(":debug-pause"), .descriptor = { .id = HK_HUB_DEBUGGER_COMPONENT_PAUSE_MESSAGE_ID, .post = CCMessageExpressionBasicPoster } },
    { .name = CC_STRING(":debug-continue"), .descriptor = { .id = HK_HUB_DEBUGGER_COMPONENT_CONTINUE_MESSAGE_ID, .post = CCMessageExpressionBasicPoster } },
    { .name = CC_STRING(":debug-step"), .descriptor = { .id = HK_HUB_DEBUGGER_COMPONENT_STEP_MESSAGE_ID, .post = CCMessageExpressionBasicPoster } },
    { .name = CC_STRING(":debug-break"), .descriptor = { .id = HK_HUB_DEBUGGER_COMPONENT_BREAKPOINT_MESSAGE_ID, .post = HKHubDebuggerComponentMessagePostBreakpoint } },
    { .name = CC_STRING(":debug-toggle-break"), .descriptor = { .id = HK_HUB_DEBUGGER_COMPONENT_TOGGLE_BREAKPOINT_MESSAGE_ID, .post = HKHubDebuggerComponentMessagePostBreakpoint } },
    { .name = CC_STRING(":debug-clear-break"), .descriptor = { .id = HK_HUB_DEBUGGER_COMPONENT_TOGGLE_BREAKPOINT_MESSAGE_ID, .post = CCMessageExpressionBasicPoster } }
};

void HKHubDebuggerComponentRegister(void)
{
    CCComponentRegister(HK_HUB_DEBUGGER_COMPONENT_ID, HKHubDebuggerComponentName, CC_STD_ALLOCATOR, sizeof(HKHubDebuggerComponentClass), HKHubDebuggerComponentInitialize, HKHubDebuggerComponentMessageHandler, HKHubDebuggerComponentDeallocate);
    
    CCComponentExpressionRegister(CC_STRING("debugger"), &HKHubDebuggerComponentDescriptor, TRUE);
    
    for (size_t Loop = 0; Loop < sizeof(HKHubDebuggerComponentMessageDescriptors) / sizeof(typeof(*HKHubDebuggerComponentMessageDescriptors)); Loop++)
    {
        CCMessageExpressionRegister(HKHubDebuggerComponentMessageDescriptors[Loop].name, &HKHubDebuggerComponentMessageDescriptors[Loop].descriptor);
    }
}

void HKHubDebuggerComponentDeregister(void)
{
    CCComponentDeregister(HK_HUB_DEBUGGER_COMPONENT_ID);
}

static _Bool HKHubDebuggerComponentMessagePostBreakpoint(CCMessageRouter *Router, CCMessageID id, CCExpression Args)
{
    if ((Args) && (CCExpressionGetType(Args) == CCExpressionValueTypeList) && (CCCollectionGetCount(CCExpressionGetList(Args)) == 2))
    {
        CCExpression Offset = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(CCExpressionGetList(Args), 0);
        CCExpression Condition = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(CCExpressionGetList(Args), 1);
        
        if ((CCExpressionGetType(Offset) == CCExpressionValueTypeInteger) && (CCExpressionGetType(Condition) == CCExpressionValueTypeAtom))
        {
            HKHubDebuggerComponentMessageBreakpoint Breakpoint = {
                .breakpoint = HKHubArchProcessorDebugBreakpointNone,
                .offset = (uint8_t)CCExpressionGetInteger(Offset)
            };
            
            CCString Name = CCExpressionGetAtom(Condition);
            if (CCStringEqual(Name, CC_STRING(":none"))) Breakpoint.breakpoint = HKHubArchProcessorDebugBreakpointNone;
            else if (CCStringEqual(Name, CC_STRING(":read"))) Breakpoint.breakpoint = HKHubArchProcessorDebugBreakpointRead;
            else if (CCStringEqual(Name, CC_STRING(":write"))) Breakpoint.breakpoint = HKHubArchProcessorDebugBreakpointWrite;
            else if (CCStringEqual(Name, CC_STRING(":read-write"))) Breakpoint.breakpoint = HKHubArchProcessorDebugBreakpointRead | HKHubArchProcessorDebugBreakpointWrite;
            else CC_EXPRESSION_EVALUATOR_LOG_ERROR("message: :debug-%s expects condition type of (:none, :read, :write, :readwrite)", (id == HK_HUB_DEBUGGER_COMPONENT_BREAKPOINT_MESSAGE_ID ? "break" : "toggle-break"));
            
            CCMessagePost(CC_STD_ALLOCATOR, id, Router, sizeof(HKHubDebuggerComponentMessageBreakpoint), &Breakpoint, NULL);
            
            return TRUE;
        }
    }
    
    CC_EXPRESSION_EVALUATOR_LOG_ERROR("message: :debug-%s expects the arguments (offset:integer condition:atom)", (id == HK_HUB_DEBUGGER_COMPONENT_BREAKPOINT_MESSAGE_ID ? "break" : "toggle-break"));
    
    CCMessageRouterDestroy(Router);
    
    return FALSE;
}
