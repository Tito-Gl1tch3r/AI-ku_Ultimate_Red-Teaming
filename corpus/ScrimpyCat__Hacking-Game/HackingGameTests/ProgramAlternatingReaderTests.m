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

@interface ProgramAlternatingReaderTests : ProgramTests

@end

@implementation ProgramAlternatingReaderTests

-(const char*) program
{
    return "assets/logic/programs/alternating_reader.chasm";
}

-(const char*) defines
{
    return ".define active, 0\n.define read_attempts, 4\n";
}

static uint8_t *InData = NULL;
static size_t DataCount = 0, DataIndex = 0, ReadAttempts = 0;

static HKHubArchPortResponse InPort(HKHubArchPortConnection Connection, HKHubArchPortDevice Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    ReadAttempts++;
    
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

static CCQueue ReadData = NULL;
static _Bool (*OutPortBusy)(void) = NULL;
static _Bool CheckOutBusy = TRUE;
static HKHubArchPortResponse OutPort(HKHubArchPortConnection Connection, HKHubArchPortDevice Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    if ((CheckOutBusy) && (OutPortBusy) && (CheckOutBusy = OutPortBusy())) return HKHubArchPortResponseTimeout;
    
    const HKHubArchPort *OppositePort = HKHubArchPortConnectionGetOppositePort(Connection, Device, Port);
    
    if (HKHubArchPortIsReady(OppositePort))
    {
        CCQueuePush(ReadData, CCQueueCreateNode(CC_STD_ALLOCATOR, Message->size, Message->memory + Message->offset));
        
        CheckOutBusy = TRUE;
        
        return HKHubArchPortResponseSuccess;
    }
    
    return HKHubArchPortResponseDefer;
}

static _Bool (*SwitchPortBusy)(void) = NULL;
static _Bool CheckSwitchBusy = TRUE;
static int SwitchState = 0;
static HKHubArchPortResponse SwitchPort(HKHubArchPortConnection Connection, HKHubArchPortDevice Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    if ((CheckSwitchBusy) && (SwitchPortBusy) && (CheckSwitchBusy = SwitchPortBusy())) return HKHubArchPortResponseTimeout;
    
    const HKHubArchPort *OppositePort = HKHubArchPortConnectionGetOppositePort(Connection, Device, Port);
    
    if (HKHubArchPortIsReady(OppositePort))
    {
        SwitchState++;
        
        CheckSwitchBusy = TRUE;
        
        return HKHubArchPortResponseSuccess;
    }
    
    return HKHubArchPortResponseDefer;
}

static _Bool (*ReadNotifierPortSend)(void) = NULL;
static _Bool ReadNotifierSend = TRUE;
static HKHubArchPortResponse ReadNotifierPortSender(HKHubArchPortConnection Connection, HKHubArchPortDevice Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    if ((ReadNotifierSend) && (ReadNotifierPortSend) && (ReadNotifierSend = !ReadNotifierPortSend())) return HKHubArchPortResponseTimeout;
    
    *Message = (HKHubArchPortMessage){
        .memory = NULL,
        .offset = 0,
        .size = 0
    };
    
    if (!HKHubArchPortIsReady(HKHubArchPortConnectionGetOppositePort(Connection, Device, Port))) return HKHubArchPortResponseDefer;
    
    ReadNotifierSend = TRUE;
    
    return HKHubArchPortResponseSuccess;
}

static _Bool (*ReadNotifierPortBusy)(void) = NULL;
static _Bool CheckReadNotifierBusy = TRUE;
static int ReadNotifierState = 0;
static HKHubArchPortResponse ReadNotifierPortReceiver(HKHubArchPortConnection Connection, HKHubArchPortDevice Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    if ((CheckReadNotifierBusy) && (ReadNotifierPortBusy) && (CheckReadNotifierBusy = ReadNotifierPortBusy())) return HKHubArchPortResponseTimeout;
    
    const HKHubArchPort *OppositePort = HKHubArchPortConnectionGetOppositePort(Connection, Device, Port);
    
    if (HKHubArchPortIsReady(OppositePort))
    {
        ReadNotifierState++;
        
        CheckReadNotifierBusy = TRUE;
        
        return HKHubArchPortResponseSuccess;
    }
    
    return HKHubArchPortResponseDefer;
}

static _Bool (*WriteNotifierPortSend)(void) = NULL;
static _Bool WriteNotifierSend = TRUE;
static HKHubArchPortResponse WriteNotifierPortSender(HKHubArchPortConnection Connection, HKHubArchPortDevice Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    if ((WriteNotifierSend) && (WriteNotifierPortSend) && (WriteNotifierSend = !WriteNotifierPortSend())) return HKHubArchPortResponseTimeout;
    
    *Message = (HKHubArchPortMessage){
        .memory = NULL,
        .offset = 0,
        .size = 0
    };
    
    if (!HKHubArchPortIsReady(HKHubArchPortConnectionGetOppositePort(Connection, Device, Port))) return HKHubArchPortResponseDefer;
    
    WriteNotifierSend = TRUE;
    
    return HKHubArchPortResponseSuccess;
}

static _Bool (*WriteNotifierPortBusy)(void) = NULL;
static _Bool CheckWriteNotifierBusy = TRUE;
static int WriteNotifierState = 0;
static HKHubArchPortResponse WriteNotifierPortReceiver(HKHubArchPortConnection Connection, HKHubArchPortDevice Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    if ((CheckWriteNotifierBusy) && (WriteNotifierPortBusy) && (CheckWriteNotifierBusy = WriteNotifierPortBusy())) return HKHubArchPortResponseTimeout;
    
    const HKHubArchPort *OppositePort = HKHubArchPortConnectionGetOppositePort(Connection, Device, Port);
    
    if (HKHubArchPortIsReady(OppositePort))
    {
        WriteNotifierState++;
        
        CheckWriteNotifierBusy = TRUE;
        
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
    
    RetCallCount = 0;
    RetOnceCalledDataIndex1 = FALSE;
    RetOnceCalledDataIndex2 = FALSE;
    RetOnceCalledDataIndex3 = FALSE;
    RetOnceCalledDataIndex4 = FALSE;
    RetOnceCalledDataIndex5 = FALSE;
    
    InData = NULL;
    DataCount = 0;
    DataIndex = 0;
    ReadAttempts = 0;
    
    ReadData = CCQueueCreate(CC_STD_ALLOCATOR);
    OutPortBusy = NULL;
    CheckOutBusy = TRUE;
    
    SwitchPortBusy = NULL;
    CheckSwitchBusy = TRUE;
    SwitchState = 0;
    
    ReadNotifierPortSend = NULL;
    ReadNotifierSend = TRUE;
    
    ReadNotifierPortBusy = NULL;
    CheckReadNotifierBusy = TRUE;
    ReadNotifierState = 0;
    
    WriteNotifierPortSend = NULL;
    WriteNotifierSend = TRUE;
    
    WriteNotifierPortBusy = NULL;
    CheckWriteNotifierBusy = TRUE;
    WriteNotifierState = 0;
    
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
    
    Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(self.processor, 2), (HKHubArchPort){
        .sender = NULL,
        .receiver = OutPort,
        .device = NULL,
        .destructor = NULL,
        .disconnect = NULL,
        .id = 0
    });
    
    HKHubArchProcessorConnect(self.processor, 2, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(self.processor, 3), (HKHubArchPort){
        .sender = NULL,
        .receiver = SwitchPort,
        .device = NULL,
        .destructor = NULL,
        .disconnect = NULL,
        .id = 0
    });
    
    HKHubArchProcessorConnect(self.processor, 3, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(self.processor, 0), (HKHubArchPort){
        .sender = ReadNotifierPortSender,
        .receiver = ReadNotifierPortReceiver,
        .device = NULL,
        .destructor = NULL,
        .disconnect = NULL,
        .id = 0
    });
    
    HKHubArchProcessorConnect(self.processor, 0, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(self.processor, 255), (HKHubArchPort){
        .sender = WriteNotifierPortSender,
        .receiver = WriteNotifierPortReceiver,
        .device = NULL,
        .destructor = NULL,
        .disconnect = NULL,
        .id = 0
    });
    
    HKHubArchProcessorConnect(self.processor, 255, Conn);
    HKHubArchPortConnectionDestroy(Conn);
}

-(void)tearDown
{
    if (ReadData) CCQueueDestroy(ReadData);
    
    [super tearDown];
}

-(void) testNoDataWaitingToRead
{
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetFalse;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetFalse;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 0, @"Should not consume any data");
    XCTAssertEqual(ReadAttempts, 0, @"Should not make any attempts to consume data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(SwitchState, 0, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 0, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 0, @"Should not have change state");
}

-(void) testNoDataReadyToRead
{
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetTrue;
    ReadNotifierPortBusy = RetTrue;
    WriteNotifierPortSend = RetFalse;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 0, @"Should not consume any data");
    XCTAssertEqual(ReadAttempts, 4, @"Should attempt to consume data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(SwitchState, 0, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 0, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 0, @"Should not have change state");
}

-(void) testNoDataReadyToReadAlertAfterRead
{
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetTrue;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetFalse;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 0, @"Should not consume any data");
    XCTAssertEqual(ReadAttempts, 4, @"Should attempt to consume data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(SwitchState, 0, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 1, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 0, @"Should not have change state");
}

-(void) testNoDataReadyToReadAlertAfterReadReadyToWrite
{
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetTrue;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetTrue;
    WriteNotifierPortBusy = RetTrue;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 0, @"Should not consume any data");
    XCTAssertEqual(ReadAttempts, 4, @"Should attempt to consume data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(SwitchState, 1, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 1, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 0, @"Should not have change state");
}

-(void) testNoDataReadyToReadAlertAfterReadReadyToWriteAlertAfterWrite
{
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetCallCountLessThan3;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetTrue;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 0, @"Should not consume any data");
    XCTAssertEqual(ReadAttempts, 12, @"Should attempt to consume data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(SwitchState, 3, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 3, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 3, @"Should not have change state");
}

-(void) testDataWaitingToRead
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetFalse;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetFalse;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 0, @"Should not consume any data");
    XCTAssertEqual(ReadAttempts, 0, @"Should not make any attempts to consume data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(SwitchState, 0, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 0, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 0, @"Should not have change state");
}

-(void) testDataReadyToRead
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetTrue;
    ReadNotifierPortBusy = RetTrue;
    WriteNotifierPortSend = RetFalse;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 4, @"Should consume some data");
    XCTAssertEqual(ReadAttempts, 4, @"Should attempt to consume data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(SwitchState, 0, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 0, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 0, @"Should not have change state");
}

-(void) testDataReadyToReadAlertAfterRead
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetTrue;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetFalse;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 4, @"Should consume some data");
    XCTAssertEqual(ReadAttempts, 4, @"Should attempt to consume data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive anymore data");
    
    XCTAssertEqual(SwitchState, 0, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 1, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 0, @"Should not have change state");
}

-(void) testDataReadyToReadAlertAfterReadReadyToWrite
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetTrue;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetTrue;
    WriteNotifierPortBusy = RetTrue;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 4, @"Should consume some data");
    XCTAssertEqual(ReadAttempts, 4, @"Should attempt to consume data");
    
    CCQueueNode *Node;
    for (size_t Loop = 0; Loop < 4; Loop++)
    {
        Node = CCQueuePop(ReadData);
        XCTAssertNotEqual(Node, NULL, @"Should have received data");
        if (Node)
        {
            XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), Loop + 1, @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive anymore data");
    
    XCTAssertEqual(SwitchState, 1, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 1, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 0, @"Should not have change state");
}

-(void) testDataReadyToReadAlertAfterReadReadyToWriteAlertAfterWrite
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetCallCountLessThan3;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetTrue;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 5, @"Should consume some data");
    XCTAssertEqual(ReadAttempts, 12, @"Should attempt to consume data");
    
    CCQueueNode *Node;
    for (size_t Loop = 0; Loop < 5; Loop++)
    {
        Node = CCQueuePop(ReadData);
        XCTAssertNotEqual(Node, NULL, @"Should have received data");
        if (Node)
        {
            XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), Loop + 1, @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive anymore data");
    
    XCTAssertEqual(SwitchState, 3, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 3, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 3, @"Should not have change state");
}

-(void) testExcessDataWaitingToRead
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetFalse;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetFalse;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 0, @"Should not consume any data");
    XCTAssertEqual(ReadAttempts, 0, @"Should not make any attempts to consume data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(SwitchState, 0, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 0, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 0, @"Should not have change state");
}

-(void) testExcessDataReadyToRead
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetTrue;
    ReadNotifierPortBusy = RetTrue;
    WriteNotifierPortSend = RetFalse;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 4, @"Should consume some data");
    XCTAssertEqual(ReadAttempts, 4, @"Should attempt to consume data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(SwitchState, 0, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 0, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 0, @"Should not have change state");
}

-(void) testExcessDataReadyToReadAlertAfterRead
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetTrue;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetFalse;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 4, @"Should consume some data");
    XCTAssertEqual(ReadAttempts, 4, @"Should attempt to consume data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive anymore data");
    
    XCTAssertEqual(SwitchState, 0, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 1, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 0, @"Should not have change state");
}

-(void) testExcessDataReadyToReadAlertAfterReadReadyToWrite
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetTrue;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetTrue;
    WriteNotifierPortBusy = RetTrue;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 4, @"Should consume some data");
    XCTAssertEqual(ReadAttempts, 4, @"Should attempt to consume data");
    
    CCQueueNode *Node;
    for (size_t Loop = 0; Loop < 4; Loop++)
    {
        Node = CCQueuePop(ReadData);
        XCTAssertNotEqual(Node, NULL, @"Should have received data");
        if (Node)
        {
            XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), Loop + 1, @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive anymore data");
    
    XCTAssertEqual(SwitchState, 1, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 1, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 0, @"Should not have change state");
}

-(void) testExcessDataReadyToReadAlertAfterReadReadyToWriteAlertAfterWrite
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetCallCountLessThan3;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetTrue;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 12, @"Should consume some data");
    XCTAssertEqual(ReadAttempts, 12, @"Should attempt to consume data");
    
    CCQueueNode *Node;
    for (size_t Loop = 0; Loop < 12; Loop++)
    {
        Node = CCQueuePop(ReadData);
        XCTAssertNotEqual(Node, NULL, @"Should have received data");
        if (Node)
        {
            XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), Loop + 1, @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive anymore data");
    
    XCTAssertEqual(SwitchState, 3, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 3, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 3, @"Should not have change state");
}

@end


@interface ProgramAlternatingReaderActiveTests : ProgramAlternatingReaderTests

@end

@implementation ProgramAlternatingReaderActiveTests

-(const char*) defines
{
    return ".define active, 1\n.define read_attempts, 4\n";
}

-(void) testNoDataWaitingToRead
{
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetFalse;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetFalse;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 0, @"Should not consume any data");
    XCTAssertEqual(ReadAttempts, 4, @"Should not make any attempts to consume data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(SwitchState, 0, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 1, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 0, @"Should not have change state");
}

-(void) testNoDataReadyToReadAlertAfterReadReadyToWriteAlertAfterWrite
{
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetCallCountLessThan3;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetTrue;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 0, @"Should not consume any data");
    XCTAssertEqual(ReadAttempts, 16, @"Should attempt to consume data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(SwitchState, 4, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 4, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 4, @"Should not have change state");
}

-(void) testDataWaitingToRead
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetFalse;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetFalse;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 4, @"Should not consume any data");
    XCTAssertEqual(ReadAttempts, 4, @"Should not make any attempts to consume data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(SwitchState, 0, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 1, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 0, @"Should not have change state");
}

-(void) testDataReadyToReadAlertAfterReadReadyToWriteAlertAfterWrite
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetCallCountLessThan3;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetTrue;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 5, @"Should consume some data");
    XCTAssertEqual(ReadAttempts, 16, @"Should attempt to consume data");
    
    CCQueueNode *Node;
    for (size_t Loop = 0; Loop < 5; Loop++)
    {
        Node = CCQueuePop(ReadData);
        XCTAssertNotEqual(Node, NULL, @"Should have received data");
        if (Node)
        {
            XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), Loop + 1, @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive anymore data");
    
    XCTAssertEqual(SwitchState, 4, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 4, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 4, @"Should not have change state");
}

-(void) testExcessDataWaitingToRead
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetFalse;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetFalse;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 4, @"Should not consume any data");
    XCTAssertEqual(ReadAttempts, 4, @"Should not make any attempts to consume data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(SwitchState, 0, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 1, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 0, @"Should not have change state");
}

-(void) testExcessDataReadyToReadAlertAfterReadReadyToWriteAlertAfterWrite
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    
    OutPortBusy = RetFalse;
    SwitchPortBusy = RetFalse;
    ReadNotifierPortSend = RetCallCountLessThan3;
    ReadNotifierPortBusy = RetFalse;
    WriteNotifierPortSend = RetTrue;
    WriteNotifierPortBusy = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 16, @"Should consume some data");
    XCTAssertEqual(ReadAttempts, 16, @"Should attempt to consume data");
    
    CCQueueNode *Node;
    for (size_t Loop = 0; Loop < 16; Loop++)
    {
        Node = CCQueuePop(ReadData);
        XCTAssertNotEqual(Node, NULL, @"Should have received data");
        if (Node)
        {
            XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), Loop + 1, @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive anymore data");
    
    XCTAssertEqual(SwitchState, 4, @"Should not have change state");
    XCTAssertEqual(ReadNotifierState, 4, @"Should not have change state");
    XCTAssertEqual(WriteNotifierState, 4, @"Should not have change state");
}

@end
