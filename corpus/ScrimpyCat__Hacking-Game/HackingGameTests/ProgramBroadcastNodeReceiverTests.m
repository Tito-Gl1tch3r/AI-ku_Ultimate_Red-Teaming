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

#import <XCTest/XCTest.h>
#import "ProgramTests.h"

@interface ProgramBroadcastNodeReceiverTests : ProgramTests

@end

@implementation ProgramBroadcastNodeReceiverTests

-(const char*) program
{
    return "assets/logic/programs/broadcast_node_receiver.chasm";
}

-(const char*) defines
{
    return ".define buffer_count, 3\n";
}

static uint8_t *InData = NULL;
static size_t DataCount = 0, DataIndex = 0;

static HKHubArchPortResponse InPort(HKHubArchPortConnection Connection, HKHubArchPortDevice Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    if (DataIndex == DataCount) return HKHubArchPortResponseTimeout;
    
    *Message = (HKHubArchPortMessage){
        .memory = &InData[DataIndex],
        .offset = 0,
        .size = 1
    };
    
    if (!HKHubArchPortIsReady(HKHubArchPortConnectionGetOppositePort(Connection, Device, Port))) return HKHubArchPortResponseDefer;
    
    DataIndex++;
    
    return HKHubArchPortResponseSuccess;
}

static CCQueue ReadData[3] = {NULL};
static _Bool (*OutPortBusy[3])(void) = {NULL};
static _Bool CheckBusy[3] = {TRUE};
static HKHubArchPortResponse OutPort(HKHubArchPortConnection Connection, HKHubArchPortDevice Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    if ((CheckBusy[Port]) && (OutPortBusy[Port]) && (CheckBusy[Port] = OutPortBusy[Port]())) return HKHubArchPortResponseTimeout;
    
    if (HKHubArchPortIsReady(HKHubArchPortConnectionGetOppositePort(Connection, Device, Port)))
    {
        CCQueuePush(ReadData[Port], CCQueueCreateNode(CC_STD_ALLOCATOR, Message->size, Message->memory + Message->offset));
        
        CheckBusy[Port] = TRUE;
        
        return HKHubArchPortResponseSuccess;
    }
    
    return HKHubArchPortResponseDefer;
}

static _Bool (*ControlPortSend[3])(void) = {NULL};
static _Bool CheckSend[3] = {TRUE};
static HKHubArchPortResponse ControlPort(HKHubArchPortConnection Connection, HKHubArchPortDevice Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    if ((CheckSend[Port]) && (ControlPortSend[Port]) && (CheckSend[Port] = !ControlPortSend[Port]())) return HKHubArchPortResponseTimeout;
    
    *Message = (HKHubArchPortMessage){
        .memory = NULL,
        .offset = 0,
        .size = 0
    };
    
    if (!HKHubArchPortIsReady(HKHubArchPortConnectionGetOppositePort(Connection, Device, Port))) return HKHubArchPortResponseDefer;
    
    CheckSend[Port] = TRUE;
    
    return HKHubArchPortResponseSuccess;
}

static _Bool (*ProcessorPortSend)(void) = NULL;
static _Bool CheckProcessorSend = TRUE;
static int ProcessorState = 0;
static HKHubArchPortResponse ProcessorPort(HKHubArchPortConnection Connection, HKHubArchPortDevice Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    if ((CheckProcessorSend) && (ProcessorPortSend) && (CheckProcessorSend = !ProcessorPortSend())) return HKHubArchPortResponseTimeout;
    
    if (HKHubArchPortIsReady(HKHubArchPortConnectionGetOppositePort(Connection, Device, Port)))
    {
        ProcessorState++;
        
        CheckProcessorSend = TRUE;
        
        return HKHubArchPortResponseSuccess;
    }
    
    return HKHubArchPortResponseDefer;
}

#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wunused"
RET(1);
RET(2);
RET(3);
RET(4);
RET(5);
#pragma clang diagnostic pop

-(void) setUp
{
    [super setUp];
    
    RetOnceCalledDataIndex1 = FALSE;
    RetOnceCalledDataIndex2 = FALSE;
    RetOnceCalledDataIndex3 = FALSE;
    RetOnceCalledDataIndex4 = FALSE;
    RetOnceCalledDataIndex5 = FALSE;
    
    InData = NULL;
    DataCount = 0;
    DataIndex = 0;
    
    ProcessorPortSend = NULL;
    CheckProcessorSend = TRUE;
    ProcessorState = 0;
    
    HKHubArchPortConnection Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(self.processor, 1), (HKHubArchPort){
        .sender = InPort,
        .receiver = NULL,
        .device = NULL,
        .destructor = NULL,
        .disconnect = NULL,
        .id = 0
    });
    
    HKHubArchProcessorConnect(self.processor, 1, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(self.processor, 0), (HKHubArchPort){
        .sender = NULL,
        .receiver = ProcessorPort,
        .device = NULL,
        .destructor = NULL,
        .disconnect = NULL,
        .id = 0
    });
    
    HKHubArchProcessorConnect(self.processor, 0, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    for (size_t Loop = 0; Loop < 3; Loop++)
    {
        ReadData[Loop] = CCQueueCreate(CC_STD_ALLOCATOR);
        OutPortBusy[Loop] = NULL;
        ControlPortSend[Loop] = NULL;
        CheckBusy[Loop] = TRUE;
        CheckSend[Loop] = TRUE;
        
        Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(self.processor, Loop + 2), (HKHubArchPort){
            .sender = NULL,
            .receiver = OutPort,
            .device = NULL,
            .destructor = NULL,
            .disconnect = NULL,
            .id = Loop
        });
        
        HKHubArchProcessorConnect(self.processor, Loop + 2, Conn);
        HKHubArchPortConnectionDestroy(Conn);
        
        Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(self.processor, Loop + 129), (HKHubArchPort){
            .sender = ControlPort,
            .receiver = NULL,
            .device = NULL,
            .destructor = NULL,
            .disconnect = NULL,
            .id = Loop
        });
        
        HKHubArchProcessorConnect(self.processor, Loop + 129, Conn);
        HKHubArchPortConnectionDestroy(Conn);
    }
}

-(void)tearDown
{
    for (size_t Loop = 0; Loop < 3; Loop++)
    {
        if (ReadData[Loop]) CCQueueDestroy(ReadData[Loop]);
    }
    
    [super tearDown];
}

-(void) testNoData
{
    OutPortBusy[0] = RetFalse;
    OutPortBusy[1] = RetFalse;
    OutPortBusy[2] = RetFalse;
    ControlPortSend[0] = RetFalse;
    ControlPortSend[1] = RetFalse;
    ControlPortSend[2] = RetFalse;
    ProcessorPortSend = RetTrue;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 0, @"Should not consume any data");
    
    CCQueueNode *Node = CCQueuePop(ReadData[0]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    Node = CCQueuePop(ReadData[1]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    Node = CCQueuePop(ReadData[2]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(ProcessorState, 0, @"Should not have changed state");
}

-(void) testDataNonSwitching
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5
    };

    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;

    OutPortBusy[0] = RetFalse;
    OutPortBusy[1] = RetFalse;
    OutPortBusy[2] = RetFalse;
    ControlPortSend[0] = RetFalse;
    ControlPortSend[1] = RetFalse;
    ControlPortSend[2] = RetFalse;
    ProcessorPortSend = RetTrue;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, DataCount, @"Should consume all data");
    
    CCQueueNode *Node;
    for (size_t Loop = 0; Loop < DataCount; Loop++)
    {
        Node = CCQueuePop(ReadData[0]);
        XCTAssertNotEqual(Node, NULL, @"Should have received data");
        if (Node)
        {
            XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), Loop + 1, @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    Node = CCQueuePop(ReadData[0]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    Node = CCQueuePop(ReadData[1]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    Node = CCQueuePop(ReadData[2]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(ProcessorState, 0, @"Should not have changed state");
}

-(void) testDataSwitching
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy[0] = RetDataIndexNot1;
    OutPortBusy[1] = RetDataIndexNot2;
    OutPortBusy[2] = RetFalse;
    ControlPortSend[0] = RetOnceDataIndex2;
    ControlPortSend[1] = RetOnceDataIndex3;
    ControlPortSend[2] = RetFalse;
    ProcessorPortSend = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, DataCount, @"Should consume all data");
    
    CCQueueNode *Node = CCQueuePop(ReadData[0]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 1, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[0]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    Node = CCQueuePop(ReadData[1]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 2, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[1]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    for (size_t Loop = 0; Loop < 3; Loop++)
    {
        Node = CCQueuePop(ReadData[2]);
        XCTAssertNotEqual(Node, NULL, @"Should have received data");
        if (Node)
        {
            XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), Loop + 3, @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    Node = CCQueuePop(ReadData[2]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(ProcessorState, 0, @"Should not have changed state");
}

-(void) testDataSwitchingWithProcessor
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy[0] = RetDataIndexNot1;
    OutPortBusy[1] = RetDataIndexNot2;
    OutPortBusy[2] = RetFalse;
    ControlPortSend[0] = RetOnceDataIndex2;
    ControlPortSend[1] = RetOnceDataIndex3;
    ControlPortSend[2] = RetFalse;
    ProcessorPortSend = RetTrue;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, DataCount, @"Should consume all data");
    
    CCQueueNode *Node = CCQueuePop(ReadData[0]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 1, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[0]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    Node = CCQueuePop(ReadData[1]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 2, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[1]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    for (size_t Loop = 0; Loop < 3; Loop++)
    {
        Node = CCQueuePop(ReadData[2]);
        XCTAssertNotEqual(Node, NULL, @"Should have received data");
        if (Node)
        {
            XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), Loop + 3, @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    Node = CCQueuePop(ReadData[2]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(ProcessorState, 0, @"Should not have changed state");
}

-(void) testDataSwitchingAll
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy[0] = RetDataIndexNot1;
    OutPortBusy[1] = RetDataIndexNot2;
    OutPortBusy[2] = RetDataIndexNot3;
    ControlPortSend[0] = RetOnceDataIndex2;
    ControlPortSend[1] = RetOnceDataIndex3;
    ControlPortSend[2] = RetOnceDataIndex4;
    ProcessorPortSend = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 4, @"Should not consume all data");
    
    CCQueueNode *Node = CCQueuePop(ReadData[0]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 1, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[0]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    Node = CCQueuePop(ReadData[1]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 2, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[1]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    Node = CCQueuePop(ReadData[2]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 3, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[2]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(ProcessorState, 0, @"Should not have changed state");
}

-(void) testDataSwitchingAllWithProcessor
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy[0] = RetDataIndexNot1;
    OutPortBusy[1] = RetDataIndexNot2;
    OutPortBusy[2] = RetDataIndexNot3;
    ControlPortSend[0] = RetOnceDataIndex2;
    ControlPortSend[1] = RetOnceDataIndex3;
    ControlPortSend[2] = RetOnceDataIndex4;
    ProcessorPortSend = RetTrue;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 4, @"Should not consume all data");
    
    CCQueueNode *Node = CCQueuePop(ReadData[0]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 1, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[0]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    Node = CCQueuePop(ReadData[1]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 2, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[1]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    Node = CCQueuePop(ReadData[2]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 3, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[2]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(ProcessorState, 0, @"Should not have changed state");
}

static _Bool ClearedBuffer = TRUE;
static _Bool RetBusy(void)
{
    if (((DataIndex % 3) == 1) && (ClearedBuffer))
    {
        ClearedBuffer = FALSE;
        
        return FALSE;
    }
    
    return TRUE;
}

static _Bool SentBufferFree = FALSE;
static _Bool RetBufferStatus(void)
{
    if (!ClearedBuffer)
    {
        if (SentBufferFree)
        {
            ClearedBuffer = TRUE;
            return TRUE;
        }
        
        SentBufferFree = TRUE;
    }
    
    return FALSE;
}

-(void) testDataSwitchingAllClearingFirst
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    ClearedBuffer = TRUE;
    SentBufferFree = FALSE;
    
    OutPortBusy[0] = RetBusy;
    OutPortBusy[1] = RetDataIndexNot2;
    OutPortBusy[2] = RetDataIndexNot3;
    ControlPortSend[0] = RetBufferStatus;
    ControlPortSend[1] = RetOnceDataIndex3;
    ControlPortSend[2] = RetOnceDataIndex4;
    ProcessorPortSend = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 4, @"Should not consume all data");
    
    CCQueueNode *Node = CCQueuePop(ReadData[0]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 1, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[0]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 4, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[0]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    Node = CCQueuePop(ReadData[1]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 2, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[1]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    Node = CCQueuePop(ReadData[2]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 3, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[2]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(ProcessorState, 0, @"Should not have changed state");
}

-(void) testDataSwitchingAllClearingFirstProcessing
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    ClearedBuffer = TRUE;
    SentBufferFree = FALSE;
    
    OutPortBusy[0] = RetBusy;
    OutPortBusy[1] = RetDataIndexNot2;
    OutPortBusy[2] = RetDataIndexNot3;
    ControlPortSend[0] = RetBufferStatus;
    ControlPortSend[1] = RetOnceDataIndex3;
    ControlPortSend[2] = RetOnceDataIndex4;
    ProcessorPortSend = RetTrue;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 5, @"Should not consume all data");
    
    CCQueueNode *Node = CCQueuePop(ReadData[0]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 1, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[0]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 4, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[0]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    Node = CCQueuePop(ReadData[1]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 2, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[1]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    Node = CCQueuePop(ReadData[2]);
    XCTAssertNotEqual(Node, NULL, @"Should have received data");
    if (Node)
    {
        XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), 3, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(ReadData[2]);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(ProcessorState, 1, @"Should not have changed state");
}

@end
