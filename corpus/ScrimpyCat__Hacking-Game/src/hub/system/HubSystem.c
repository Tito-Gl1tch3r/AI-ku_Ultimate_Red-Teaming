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

#include "HubSystem.h"
#include <threads.h>
#include "HubProcessorComponent.h"
#include "HubPortConnectionComponent.h"
#include "HubModuleComponent.h"
#include "HubDebuggerComponent.h"
#include "HubArchScheduler.h"
#include "HubArchInstruction.h"
#include "RapServer.h"
#include "HubModuleWirelessTransceiver.h"

static _Bool HKHubSystemTryLock(CCComponentSystemHandle *Handle);
static void HKHubSystemLock(CCComponentSystemHandle *Handle);
static void HKHubSystemUnlock(CCComponentSystemHandle *Handle);
static _Bool HKHubSystemHandlesComponent(CCComponentSystemHandle *Handle, CCComponentID id);
static void HKHubSystemUpdate(CCComponentSystemHandle *Handle, double DeltaTime, CCCollection(CCComponent) Components);

static HKHubArchScheduler HKHubSystemGetSchedulerForModule(HKHubModule Module)
{
    return HKHubSystemGetScheduler();
}

static CCCollection(CCComponent) Transceivers = NULL;
static void HKHubSystemPacketBroadcaster(HKHubModule Transmitter, HKHubModuleWirelessTransceiverPacket Packet)
{
    CC_COLLECTION_FOREACH(CCComponent, Transceiver, Transceivers)
    {
        HKHubModule Receiver = HKHubModuleComponentGetModule(Transceiver);
        if (Receiver != Transmitter)
        {
            HKHubModuleWirelessTransceiverReceivePacket(Receiver, Packet);
        }
    }
}

static HKHubArchScheduler Scheduler;
static mtx_t Lock;
static CCCollection(CCComponent) Schematics = NULL;
void HKHubSystemRegister(void)
{
    int err;
    if ((err = mtx_init(&Lock, mtx_plain | mtx_recursive)) != thrd_success)
    {
        CC_LOG_ERROR("Failed to create hub system lock (%d)", err);
        exit(EXIT_FAILURE); //TODO: How should we handle this?
    }
    
    Scheduler = HKHubArchSchedulerCreate(CC_STD_ALLOCATOR);
    
    CCComponentSystemRegister(HK_HUB_SYSTEM_ID, CCComponentSystemExecutionTypeUpdate, (CCComponentSystemUpdateCallback)HKHubSystemUpdate, NULL, HKHubSystemHandlesComponent, NULL, NULL, HKHubSystemTryLock, HKHubSystemLock, HKHubSystemUnlock);
    
    HKHubModuleWirelessTransceiverGetScheduler = HKHubSystemGetSchedulerForModule;
    HKHubModuleWirelessTransceiverBroadcast = HKHubSystemPacketBroadcaster;
    
    Transceivers = CCCollectionCreate(CC_STD_ALLOCATOR, CCCollectionHintSizeMedium, sizeof(CCComponent), NULL);
    Schematics = CCCollectionCreate(CC_STD_ALLOCATOR, CCCollectionHintSizeMedium, sizeof(CCComponent), NULL);
}

void HKHubSystemDeregister(void)
{
    mtx_destroy(&Lock);
    
    CCComponentSystemDeregister(HK_HUB_SYSTEM_ID, CCComponentSystemExecutionTypeUpdate);
}

static _Bool HKHubSystemTryLock(CCComponentSystemHandle *Handle)
{
    int err = mtx_trylock(&Lock);
    if ((err != thrd_success) && (err != thrd_busy))
    {
        CC_LOG_ERROR("Failed to lock hub system (%d)", err);
    }
    
    return err == thrd_success;
}

static void HKHubSystemLock(CCComponentSystemHandle *Handle)
{
    int err;
    if ((err = mtx_lock(&Lock)) != thrd_success)
    {
        CC_LOG_ERROR("Failed to lock hub system (%d)", err);
    }
}

static void HKHubSystemUnlock(CCComponentSystemHandle *Handle)
{
    int err;
    if ((err = mtx_unlock(&Lock)) != thrd_success)
    {
        CC_LOG_ERROR("Failed to unlock hub system (%d)", err);
    }
}

static _Bool HKHubSystemHandlesComponent(CCComponentSystemHandle *Handle, CCComponentID id)
{
    return (id & 0x7f000000) == HK_HUB_COMPONENT_FLAG;
}

static CCString BreakpointType[] = {
    0,
    CC_STRING(":read"),
    CC_STRING(":write"),
    CC_STRING(":read-write")
};

static void HKHubSystemInitDebugger(GUIObject Debugger, HKHubArchProcessor Processor)
{
    CCExpression State = GUIObjectGetExpressionState(Debugger);
    
    CCExpressionSetState(State, CC_STRING(".debug-mode"), CCExpressionCreateAtom(CC_STD_ALLOCATOR, (CCString[2]){
        CC_STRING(":continue"),
        CC_STRING(":pause")
    }[Processor->state.debug.mode], TRUE), FALSE);
    
    CCExpression Memory = CCExpressionCreateList(CC_STD_ALLOCATOR);
    for (size_t Loop = 0; Loop < sizeof(Processor->memory) / sizeof(typeof(*Processor->memory)); Loop++)
    {
        CCOrderedCollectionAppendElement(CCExpressionGetList(Memory), &(CCExpression){ CCExpressionCreateInteger(CC_STD_ALLOCATOR, Processor->memory[Loop]) });
    }
    
    CCExpressionSetState(State, CC_STRING(".memory"), Memory, FALSE);
    CCExpressionSetState(State, CC_STRING(".memory-changed"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
    CCExpressionSetState(State, CC_STRING(".memory-modified"), CCExpressionCreateFromSource("((0 256))"), FALSE);
    
    
    CCExpressionSetState(State, CC_STRING(".r0"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, Processor->state.r[0]), FALSE);
    CCExpressionSetState(State, CC_STRING(".r1"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, Processor->state.r[1]), FALSE);
    CCExpressionSetState(State, CC_STRING(".r2"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, Processor->state.r[2]), FALSE);
    CCExpressionSetState(State, CC_STRING(".r3"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, Processor->state.r[3]), FALSE);
    CCExpressionSetState(State, CC_STRING(".r0-changed"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
    CCExpressionSetState(State, CC_STRING(".r1-changed"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
    CCExpressionSetState(State, CC_STRING(".r2-changed"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
    CCExpressionSetState(State, CC_STRING(".r3-changed"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
    CCExpressionSetState(State, CC_STRING(".r0-modified"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, FALSE), FALSE);
    CCExpressionSetState(State, CC_STRING(".r1-modified"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, FALSE), FALSE);
    CCExpressionSetState(State, CC_STRING(".r2-modified"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, FALSE), FALSE);
    CCExpressionSetState(State, CC_STRING(".r3-modified"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, FALSE), FALSE);
    
    CCExpressionSetState(State, CC_STRING(".flags"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, Processor->state.flags), FALSE);
    CCExpressionSetState(State, CC_STRING(".flags-changed"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
    CCExpressionSetState(State, CC_STRING(".flags-modified"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, FALSE), FALSE);
    
    CCExpressionSetState(State, CC_STRING(".pc"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, Processor->state.pc), FALSE);
    CCExpressionSetState(State, CC_STRING(".pc-changed"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
    CCExpressionSetState(State, CC_STRING(".pc-modified"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, FALSE), FALSE);
    
    
    CCExpression Breakpoints = CCExpressionCreateList(CC_STD_ALLOCATOR);
    if (Processor->state.debug.breakpoints)
    {
        CC_DICTIONARY_FOREACH_KEY(uint8_t, Offset, Processor->state.debug.breakpoints)
        {
            HKHubArchProcessorDebugBreakpoint *Bp = CCDictionaryGetValue(Processor->state.debug.breakpoints, &Offset);
            
            if (BreakpointType[*Bp])
            {
                CCExpression Breakpoint = CCExpressionCreateList(CC_STD_ALLOCATOR);
                CCOrderedCollectionAppendElement(CCExpressionGetList(Breakpoint), &(CCExpression){ CCExpressionCreateInteger(CC_STD_ALLOCATOR, Offset) });
                CCOrderedCollectionAppendElement(CCExpressionGetList(Breakpoint), &(CCExpression){ CCExpressionCreateAtom(CC_STD_ALLOCATOR, BreakpointType[*Bp], TRUE) });
                
                CCOrderedCollectionAppendElement(CCExpressionGetList(Breakpoints), &Breakpoint);
            }
        }
    }
    
    CCExpressionSetState(State, CC_STRING(".breakpoints"), Breakpoints, FALSE);
    CCExpressionSetState(State, CC_STRING(".breakpoints-changed"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
    
    
    CCExpression Ports = CCExpressionCreateList(CC_STD_ALLOCATOR);
    
    CC_DICTIONARY_FOREACH_VALUE(HKHubArchPortConnection, Connection, Processor->ports)
    {
        HKHubArchPortID PortID = (Connection->port[0].device == Processor ? &Connection->port[0] : &Connection->port[1])->id;
        
        CCExpression Port = CCExpressionCreateList(CC_STD_ALLOCATOR);
        CCOrderedCollectionAppendElement(CCExpressionGetList(Port), &(CCExpression){ CCExpressionCreateInteger(CC_STD_ALLOCATOR, PortID) });
        CCOrderedCollectionAppendElement(CCExpressionGetList(Port), &(CCExpression){ CCExpressionCreateAtom(CC_STD_ALLOCATOR, CC_STRING(":connected"), TRUE) });
        
        CCOrderedCollectionAppendElement(CCExpressionGetList(Ports), &Port);
    }
    
    CCExpressionSetState(State, CC_STRING(".ports"), Ports, FALSE);
    CCExpressionSetState(State, CC_STRING(".ports-changed"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
    
    HKRapServerUpdate(Processor);
}

static void HKHubSystemDebuggerInstructionHook(HKHubArchProcessor Processor, const HKHubArchInstructionState *Instruction, const uint8_t Encoding[5])
{
    //TODO: Send update message (instead of update here/avoid locking UI)
    GUIManagerLock();
    
    GUIObjectInvalidateCache(Processor->state.debug.context);
    
    CCExpression State = GUIObjectGetExpressionState(Processor->state.debug.context);
    
    CCExpressionSetState(State, CC_STRING(".r0-modified"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, FALSE), FALSE);
    CCExpressionSetState(State, CC_STRING(".r1-modified"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, FALSE), FALSE);
    CCExpressionSetState(State, CC_STRING(".r2-modified"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, FALSE), FALSE);
    CCExpressionSetState(State, CC_STRING(".r3-modified"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, FALSE), FALSE);
    
    CCExpressionSetState(State, CC_STRING(".flags"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, Processor->state.flags), FALSE); //TODO: Workout how to convey changed flags
    CCExpressionSetState(State, CC_STRING(".flags-changed"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
    CCExpressionSetState(State, CC_STRING(".flags-modified"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
    
    CCExpressionSetState(State, CC_STRING(".pc"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, Processor->state.pc), FALSE);
    CCExpressionSetState(State, CC_STRING(".pc-changed"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
    CCExpressionSetState(State, CC_STRING(".pc-modified"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
    
    if (Processor->state.debug.modified.size)
    {
        CCExpression Memory = CCExpressionCreateList(CC_STD_ALLOCATOR);
        for (size_t Loop = 0; Loop < sizeof(Processor->memory) / sizeof(typeof(*Processor->memory)); Loop++)
        {
            CCOrderedCollectionAppendElement(CCExpressionGetList(Memory), &(CCExpression){ CCExpressionCreateInteger(CC_STD_ALLOCATOR, Processor->memory[Loop]) });
        }
        
        CCExpressionSetState(State, CC_STRING(".memory"), Memory, FALSE);
        CCExpressionSetState(State, CC_STRING(".memory-changed"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
        
        CCExpression ModifiedMemory = CCExpressionCreateList(CC_STD_ALLOCATOR);
        CCExpression ModifiedRange = CCExpressionCreateList(CC_STD_ALLOCATOR);
        CCOrderedCollectionAppendElement(CCExpressionGetList(ModifiedRange), &(CCExpression){ CCExpressionCreateInteger(CC_STD_ALLOCATOR, Processor->state.debug.modified.offset) });
        CCOrderedCollectionAppendElement(CCExpressionGetList(ModifiedRange), &(CCExpression){ CCExpressionCreateInteger(CC_STD_ALLOCATOR, Processor->state.debug.modified.size) });
        
        CCOrderedCollectionAppendElement(CCExpressionGetList(ModifiedMemory), &ModifiedRange);
        
        CCExpressionSetState(State, CC_STRING(".memory-modified"), ModifiedMemory, FALSE);
    }
    
    else
    {
        CCExpressionSetState(State, CC_STRING(".memory-modified"), CCExpressionCreateList(CC_STD_ALLOCATOR), FALSE);
    }
    
    CCString Reg[][3] = {
        { CC_STRING(".r0"), CC_STRING(".r0-changed"), CC_STRING(".r0-modified") },
        { CC_STRING(".r1"), CC_STRING(".r1-changed"), CC_STRING(".r1-modified") },
        { CC_STRING(".r2"), CC_STRING(".r2-changed"), CC_STRING(".r2-modified") },
        { CC_STRING(".r3"), CC_STRING(".r3-changed"), CC_STRING(".r3-modified") },
        { CC_STRING(".flags"), CC_STRING(".flags-changed"), CC_STRING(".flags-modified") },
        { CC_STRING(".pc"), CC_STRING(".pc-changed"), CC_STRING(".pc-modified") }
    };
    
    if (Processor->state.debug.modified.reg & HKHubArchInstructionRegisterGeneralPurpose)
    {
        const size_t Index = Processor->state.debug.modified.reg & HKHubArchInstructionRegisterGeneralPurposeIndexMask;
        
        CCExpressionSetState(State, Reg[Index][0], CCExpressionCreateInteger(CC_STD_ALLOCATOR, Processor->state.r[Index]), FALSE);
        CCExpressionSetState(State, Reg[Index][1], CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
        CCExpressionSetState(State, Reg[Index][2], CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
    }
    
    else if (Processor->state.debug.modified.reg & HKHubArchInstructionRegisterSpecialPurpose)
    {
        const size_t Index = (Processor->state.debug.modified.reg &  HKHubArchInstructionRegisterSpecialPurposeIndexMask) + 4;
        
        CCExpressionSetState(State, Reg[Index][0], CCExpressionCreateInteger(CC_STD_ALLOCATOR, Index == 4 ? Processor->state.flags : Processor->state.pc), FALSE);
        CCExpressionSetState(State, Reg[Index][1], CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
        CCExpressionSetState(State, Reg[Index][2], CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
    }
    
    GUIManagerUnlock();
    
    HKRapServerUpdate(Processor);
}

static void HKHubSystemDebuggerPortConnectionChangeHook(HKHubArchProcessor Processor, HKHubArchPortID Port)
{
    GUIManagerLock();
    
    GUIObjectInvalidateCache(Processor->state.debug.context);
    
    CCExpression State = GUIObjectGetExpressionState(Processor->state.debug.context);
    
    CCExpression Ports = CCExpressionCreateList(CC_STD_ALLOCATOR);
    
    CC_DICTIONARY_FOREACH_VALUE(HKHubArchPortConnection, Connection, Processor->ports)
    {
        HKHubArchPortID PortID = (Connection->port[0].device == Processor ? &Connection->port[0] : &Connection->port[1])->id;
        
        CCExpression Port = CCExpressionCreateList(CC_STD_ALLOCATOR);
        CCOrderedCollectionAppendElement(CCExpressionGetList(Port), &(CCExpression){ CCExpressionCreateInteger(CC_STD_ALLOCATOR, PortID) });
        CCOrderedCollectionAppendElement(CCExpressionGetList(Port), &(CCExpression){ CCExpressionCreateAtom(CC_STD_ALLOCATOR, CC_STRING(":connected"), TRUE) });
        
        CCOrderedCollectionAppendElement(CCExpressionGetList(Ports), &Port);
    }
    
    CCExpressionSetState(State, CC_STRING(".ports"), Ports, FALSE);
    CCExpressionSetState(State, CC_STRING(".ports-changed"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
    
    GUIManagerUnlock();
    
    HKRapServerUpdate(Processor);
}

static void HKHubSystemDebuggerBreakpointChangeHook(HKHubArchProcessor Processor, HKHubArchProcessorDebugBreakpoint Breakpoint, uint8_t Offset)
{
    //TODO: Send update message (instead of update here/avoid locking UI)
    GUIManagerLock();
    
    GUIObjectInvalidateCache(Processor->state.debug.context);
    
    CCExpression State = GUIObjectGetExpressionState(Processor->state.debug.context);
    
    CCExpression Breakpoints = CCExpressionCreateList(CC_STD_ALLOCATOR);
    if (Processor->state.debug.breakpoints)
    {
        CC_DICTIONARY_FOREACH_KEY(uint8_t, Offset, Processor->state.debug.breakpoints)
        {
            HKHubArchProcessorDebugBreakpoint *Bp = CCDictionaryGetValue(Processor->state.debug.breakpoints, &Offset);
            
            if (BreakpointType[*Bp])
            {
                CCExpression Breakpoint = CCExpressionCreateList(CC_STD_ALLOCATOR);
                CCOrderedCollectionAppendElement(CCExpressionGetList(Breakpoint), &(CCExpression){ CCExpressionCreateInteger(CC_STD_ALLOCATOR, Offset) });
                CCOrderedCollectionAppendElement(CCExpressionGetList(Breakpoint), &(CCExpression){ CCExpressionCreateAtom(CC_STD_ALLOCATOR, BreakpointType[*Bp], TRUE) });
                
                CCOrderedCollectionAppendElement(CCExpressionGetList(Breakpoints), &Breakpoint);
            }
        }
    }
    
    CCExpressionSetState(State, CC_STRING(".breakpoints"), Breakpoints, FALSE);
    CCExpressionSetState(State, CC_STRING(".breakpoints-changed"), CCExpressionCreateInteger(CC_STD_ALLOCATOR, TRUE), FALSE);
    
    GUIManagerUnlock();
    
    HKRapServerUpdate(Processor);
}

static void HKHubSystemDebuggerDebugModeChangeHook(HKHubArchProcessor Processor)
{
    //TODO: Send update message (instead of update here/avoid locking UI)
    GUIManagerLock();
    
    GUIObjectInvalidateCache(Processor->state.debug.context);
    
    CCExpression State = GUIObjectGetExpressionState(Processor->state.debug.context);
    
    CCExpressionSetState(State, CC_STRING(".debug-mode"), CCExpressionCreateAtom(CC_STD_ALLOCATOR, (CCString[2]){
        CC_STRING(":continue"),
        CC_STRING(":pause")
    }[Processor->state.debug.mode], TRUE), FALSE);
    
    GUIManagerUnlock();
}

static void HKHubSystemAttachDebugger(CCComponent Debugger)
{
    CCEntity Entity = CCComponentGetEntity(Debugger);
    CC_COLLECTION_FOREACH(CCComponent, Component, CCEntityGetComponents(Entity))
    {
        if ((CCComponentGetID(Component) & HKHubTypeMask) == HKHubTypeProcessor)
        {
            HKHubArchProcessor Target = HKHubProcessorComponentGetProcessor(Component);
            HKHubArchProcessorSetDebugMode(Target, HKHubArchProcessorDebugModePause);
            
            Target->state.debug.operation = HKHubSystemDebuggerInstructionHook;
            Target->state.debug.portConnectionChange = HKHubSystemDebuggerPortConnectionChangeHook;
            Target->state.debug.breakpointChange = HKHubSystemDebuggerBreakpointChangeHook;
            Target->state.debug.debugModeChange = HKHubSystemDebuggerDebugModeChangeHook;
            
            CCExpression Expr = CCExpressionCreateFromSource("(gui-debugger)");
            CCExpression Result = CCExpressionEvaluate(Expr);
            if (CCExpressionGetType(Result) == GUIExpressionValueTypeGUIObject)
            {
                CCExpressionChangeOwnership(Result, NULL, NULL);
                Target->state.debug.context = CCExpressionGetData(Result);
                HKHubSystemInitDebugger(Target->state.debug.context, Target);
                CCExpressionSetState(GUIObjectGetExpressionState(Target->state.debug.context), CC_STRING(".entity"), CCExpressionCreateCustomType(CC_STD_ALLOCATOR, CCEntityExpressionValueTypeEntity, CCRetain(Entity), CCExpressionRetainedValueCopy, (CCExpressionValueDestructor)CCEntityDestroy), FALSE);
                
                GUIObjectSetCacheStrategy(Target->state.debug.context, GUIObjectCacheStrategyInvalidateOnRequest | GUIObjectCacheStrategyInvalidateOnMove | GUIObjectCacheStrategyInvalidateOnResize);
                GUIObjectSetEnabled(Target->state.debug.context, TRUE);
                GUIManagerAddObject(Target->state.debug.context);
            }
            
            CCExpressionDestroy(Expr);
            
            break;
        }
        
        else if ((CCComponentGetID(Component) & HKHubTypeMask) == HKHubTypeSchematic)
        {
            CCCollection(CCEntity) Children = CCRelationSystemGetChildren(Entity);
            
            CC_COLLECTION_FOREACH(CCEntity, Child, Children)
            {
                CC_COLLECTION_FOREACH(CCComponent, ChildComponent, CCEntityGetComponents(Child))
                {
                    if ((CCComponentGetID(ChildComponent) & HKHubTypeMask) == HKHubTypeProcessor)
                    {
                        CCComponent DebuggerComponent = CCComponentCreate(HK_HUB_DEBUGGER_COMPONENT_ID);
                        CCEntityAttachComponent(Child, DebuggerComponent);
                        CCComponentSystemAddComponent(DebuggerComponent);
                    }
                }
            }
            
            CCCollectionDestroy(Children);
            
            break;
        }
    }
}

static void HKHubSystemDetachDebugger(CCComponent Debugger)
{
    CCEntity Entity = CCComponentGetEntity(Debugger);
    CC_COLLECTION_FOREACH(CCComponent, Component, CCEntityGetComponents(Entity))
    {
        if ((CCComponentGetID(Component) & HKHubTypeMask) == HKHubTypeProcessor)
        {
            HKHubArchProcessor Target = HKHubProcessorComponentGetProcessor(Component);
            HKHubArchProcessorSetDebugMode(Target, HKHubArchProcessorDebugModeContinue);
            
            GUIObjectSetEnabled(Target->state.debug.context, FALSE);
            GUIManagerRemoveObject(Target->state.debug.context);
            
            Target->state.debug.context = NULL;
            Target->state.debug.operation = NULL;
            
            break;
        }
        
        else if ((CCComponentGetID(Component) & HKHubTypeMask) == HKHubTypeSchematic)
        {
            CCCollection(CCEntity) Children = CCRelationSystemGetChildren(Entity);
            
            CC_COLLECTION_FOREACH(CCEntity, Child, Children)
            {
                CC_COLLECTION_FOREACH(CCComponent, ChildComponent, CCEntityGetComponents(Child))
                {
                    if ((CCComponentGetID(ChildComponent) & HKHubTypeMask) == HKHubTypeDebugger)
                    {
                        CCEntityDetachComponent(Child, ChildComponent);
                        CCComponentSystemRemoveComponent(ChildComponent);
                    }
                }
            }
            
            CCCollectionDestroy(Children);
            
            break;
        }
    }
    
    CCEntityDetachComponent(Entity, Debugger);
}

static void HKHubSystemConnectPorts(CCComponent Connection)
{
    const HKHubPortConnectionEntityMapping *Mapping = HKHubPortConnectionComponentGetEntityMapping(Connection);
    if ((Mapping[0].entity) && (Mapping[1].entity))
    {
        struct {
            void (*connect)(HKHubArchPortDevice, HKHubArchPortID, HKHubArchPortConnection);
            HKHubArchPort port;
        } Ports[2];
        
        for (size_t Loop = 0; Loop < 2; Loop++)
        {
            CC_COLLECTION_FOREACH(CCComponent, Component, CCEntityGetComponents(Mapping[Loop].entity))
            {
                if ((CCComponentGetID(Component) & HKHubTypeMask) == HKHubTypeProcessor)
                {
                    HKHubArchProcessor Processor = HKHubProcessorComponentGetProcessor(Component);
                    HKHubArchPortConnection PortConnection = HKHubArchProcessorGetPortConnection(Processor, Mapping[Loop].port);
                    
                    CCAssertLog(!PortConnection, "Cannot create a port connection where one already exists");
                    
                    Ports[Loop].connect = (typeof(Ports->connect))HKHubArchProcessorConnect;
                    Ports[Loop].port = HKHubArchProcessorGetPort(Processor, Mapping[Loop].port);
                    break;
                }
                
                else if ((CCComponentGetID(Component) & HKHubTypeMask) == HKHubTypeModule)
                {
                    HKHubModule Module = HKHubModuleComponentGetModule(Component);
                    HKHubArchPortConnection PortConnection = HKHubModuleGetPortConnection(Module, Mapping[Loop].port);
                    
                    CCAssertLog(!PortConnection, "Cannot create a port connection where one already exists");
                    
                    Ports[Loop].connect = (typeof(Ports->connect))HKHubModuleConnect;
                    Ports[Loop].port = HKHubModuleGetPort(Module, Mapping[Loop].port);
                    break;
                }
            }
        }
        
        HKHubArchPortConnection Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, Ports[0].port, Ports[1].port);
        Ports[0].connect(Ports[0].port.device, Ports[0].port.id, Conn);
        Ports[1].connect(Ports[1].port.device, Ports[1].port.id, Conn);
        HKHubPortConnectionComponentSetConnection(Connection, Conn); //TODO: Maybe store component in a dictionary so it can be looked up by using connection
        HKHubArchPortConnectionDestroy(Conn);
    }
}

static void HKHubSystemDisconnectPorts(CCComponent Connection)
{
}

static void HKHubSystemAddTransceiver(CCComponent Transceiver)
{
    CCCollectionInsertElement(Transceivers, &Transceiver);
}

static void HKHubSystemRemoveTransceiver(CCComponent Transceiver)
{
    CCCollectionRemoveElement(Transceivers, CCCollectionFindElement(Transceivers, &Transceiver, NULL));
}

static void HKHubSystemAddSchematic(CCComponent Schematic)
{
    CCCollectionInsertElement(Schematics, &Schematic);
}

static void HKHubSystemRemoveSchematic(CCComponent Schematic)
{
    CCCollectionRemoveElement(Schematics, CCCollectionFindElement(Schematics, &Schematic, NULL));
}

typedef struct {
    void (*processor)(HKHubArchScheduler, HKHubArchProcessor);
    void (*debugger)(CCComponent);
    void (*connection)(CCComponent);
    void (*transceiver)(CCComponent);
    void (*schematic)(CCComponent);
} HKHubSystemUpdater;

static void HKHubSystemUpdateScheduler(CCCollection(CCComponent) Components, HKHubSystemUpdater Update)
{
    CC_COLLECTION_FOREACH(CCComponent, Component, Components)
    {
        const CCComponentID ID = CCComponentGetID(Component);
        
        switch (ID & HKHubTypeMask)
        {
            case HKHubTypeProcessor:
                Update.processor(Scheduler, HKHubProcessorComponentGetProcessor(Component));
                break;
                
            case HKHubTypeDebugger:
                Update.debugger(Component);
                break;
                
            case HKHubTypePortConnection:
                Update.connection(Component);
                break;
                
            case HKHubTypeModule:
                if (ID & HKHubTypeModuleWirelessTransceiver)
                {
                    Update.transceiver(Component);
                }
                break;
                
            case HKHubTypeSchematic:
                Update.schematic(Component);
                break;
                
            default:
                CCAssertLog(0, "Unhandled HKHubType");
                break;
        }
    }
    
    CCCollectionDestroy(Components);
}

static void HKHubSystemUpdate(CCComponentSystemHandle *Handle, double DeltaTime, CCCollection(CCComponent) Components)
{
    HKHubSystemUpdateScheduler(CCComponentSystemGetAddedComponentsForSystem(HK_HUB_SYSTEM_ID), (HKHubSystemUpdater){
        .processor = HKHubArchSchedulerAddProcessor,
        .debugger = HKHubSystemAttachDebugger,
        .connection = HKHubSystemConnectPorts,
        .transceiver = HKHubSystemAddTransceiver,
        .schematic = HKHubSystemAddSchematic
    });
    HKHubSystemUpdateScheduler(CCComponentSystemGetRemovedComponentsForSystem(HK_HUB_SYSTEM_ID), (HKHubSystemUpdater){
        .processor = HKHubArchSchedulerRemoveProcessor,
        .debugger = HKHubSystemDetachDebugger,
        .connection = HKHubSystemDisconnectPorts,
        .transceiver = HKHubSystemRemoveTransceiver,
        .schematic = HKHubSystemRemoveSchematic
    });
    
    const size_t TimestampShift = DeltaTime * HKHubArchProcessorHertz;
    CC_COLLECTION_FOREACH(CCComponent, Transceiver, Transceivers)
    {
        HKHubModuleWirelessTransceiverShiftTimestamps(HKHubModuleComponentGetModule(Transceiver), TimestampShift);
    }
    
    HKHubArchSchedulerRun(Scheduler, DeltaTime);
    
    const size_t Timestamp = HKHubArchSchedulerGetTimestamp(Scheduler);
    CC_COLLECTION_FOREACH(CCComponent, Transceiver, Transceivers)
    {
        HKHubModuleWirelessTransceiverPacketPurge(HKHubModuleComponentGetModule(Transceiver), Timestamp);
    }
}

HKHubArchScheduler HKHubSystemGetScheduler(void)
{
    return Scheduler;
}
