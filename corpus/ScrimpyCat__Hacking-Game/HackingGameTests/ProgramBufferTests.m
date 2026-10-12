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

@interface ProgramBufferTests : ProgramTests

@end

@implementation ProgramBufferTests

-(const char*) program
{
    return "assets/logic/programs/buffer.chasm";
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

static CCQueue ReadData = NULL;
static _Bool (*OutPortBusy)(void) = NULL;
static _Bool CheckBusy = TRUE;
static HKHubArchPortResponse OutPort(HKHubArchPortConnection Connection, HKHubArchPortDevice Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    if ((CheckBusy) && (OutPortBusy) && (CheckBusy = OutPortBusy())) return HKHubArchPortResponseTimeout;
    
    const HKHubArchPort *OppositePort = HKHubArchPortConnectionGetOppositePort(Connection, Device, Port);
    
    if (HKHubArchPortIsReady(OppositePort))
    {
        CCQueuePush(ReadData, CCQueueCreateNode(CC_STD_ALLOCATOR, Message->size, Message->memory + Message->offset));
        
        CheckBusy = TRUE;
        
        return HKHubArchPortResponseSuccess;
    }
    
    return HKHubArchPortResponseDefer;
}

static _Bool (*ControlPortSend)(void) = NULL;
static _Bool CheckSend = TRUE;
static int BufferState = 0;
static HKHubArchPortResponse ControlPort(HKHubArchPortConnection Connection, HKHubArchPortDevice Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    if ((CheckSend) && (ControlPortSend) && (CheckSend = !ControlPortSend())) return HKHubArchPortResponseTimeout;
    
    const HKHubArchPort *OppositePort = HKHubArchPortConnectionGetOppositePort(Connection, Device, Port);
    
    if (HKHubArchPortIsReady(OppositePort))
    {
        BufferState++;
        
        CheckSend = TRUE;
        
        return HKHubArchPortResponseSuccess;
    }
    
    return HKHubArchPortResponseDefer;
}

-(void) setUp
{
    [super setUp];
    
    InData = NULL;
    DataCount = 0;
    DataIndex = 0;
    
    ReadData = CCQueueCreate(CC_STD_ALLOCATOR);
    OutPortBusy = NULL;
    CheckBusy = TRUE;
    
    ControlPortSend = NULL;
    CheckSend = TRUE;
    BufferState = 0;
    
    HKHubArchPortConnection Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(self.processor, 0), (HKHubArchPort){
        .sender = InPort,
        .receiver = NULL,
        .device = NULL,
        .destructor = NULL,
        .disconnect = NULL,
        .id = 0
    });
    
    HKHubArchProcessorConnect(self.processor, 0, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(self.processor, 1), (HKHubArchPort){
        .sender = NULL,
        .receiver = OutPort,
        .device = NULL,
        .destructor = NULL,
        .disconnect = NULL,
        .id = 0
    });
    
    HKHubArchProcessorConnect(self.processor, 1, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(self.processor, 2), (HKHubArchPort){
        .sender = NULL,
        .receiver = ControlPort,
        .device = NULL,
        .destructor = NULL,
        .disconnect = NULL,
        .id = 0
    });
    
    HKHubArchProcessorConnect(self.processor, 2, Conn);
    HKHubArchPortConnectionDestroy(Conn);
}

-(void)tearDown
{
    if (ReadData) CCQueueDestroy(ReadData);
    
    [super tearDown];
}

-(void) testNoData
{
    OutPortBusy = RetFalse;
    ControlPortSend = RetTrue;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 0, @"Should not consume any data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(BufferState, 0, @"Should not have change state");
}

-(void) testBufferingData
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    OutPortBusy = RetTrue;
    ControlPortSend = RetTrue;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, DataCount, @"Should consume all data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(BufferState, 0, @"Should not have change state");
}

-(void) testBufferingDataLimit
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
        23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
        43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62,
        63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82,
        83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101,
        102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117,
        118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133,
        134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149,
        150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
        166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181,
        182, 183
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    OutPortBusy = RetTrue;
    ControlPortSend = RetTrue;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, DataCount, @"Should consume all data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(BufferState, 1, @"Should be full");
}

-(void) testBufferingDataLimitWithBusyControlPort
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
        23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
        43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62,
        63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82,
        83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101,
        102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117,
        118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133,
        134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149,
        150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
        166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181,
        182, 183
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    OutPortBusy = RetTrue;
    ControlPortSend = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, DataCount, @"Should consume all data");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(BufferState, 0, @"Should not change state");
}

-(void) testBufferingDataLimitBlocked
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
        23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
        43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62,
        63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82,
        83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101,
        102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117,
        118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133,
        134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149,
        150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
        166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181,
        182, 183, 184
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    OutPortBusy = RetTrue;
    ControlPortSend = RetTrue;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, DataCount - 1, @"Should not consume data once blocked");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(BufferState, 1, @"Should be full");
}

-(void) testBufferingDataLimitBlockedWithBusyControlPort
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
        23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
        43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62,
        63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82,
        83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101,
        102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117,
        118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133,
        134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149,
        150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
        166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181,
        182, 183, 184
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    OutPortBusy = RetTrue;
    ControlPortSend = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, DataCount - 1, @"Should not consume data once blocked");
    
    CCQueueNode *Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive any data");
    
    XCTAssertEqual(BufferState, 0, @"Should not change state");
}

-(void) testReadingData
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
        23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
        43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62,
        63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82,
        83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101,
        102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117,
        118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133,
        134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149,
        150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
        166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181,
        182, 183, 184
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    OutPortBusy = RetFalse;
    ControlPortSend = RetTrue;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, DataCount, @"Should consume all data");
    
    CCQueueNode *Node;
    for (size_t Loop = 0; Loop < DataCount; Loop++)
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
    
    XCTAssertEqual(BufferState, 0, @"Should not change state");
}

-(void) testReadingDataWithBusyControlPort
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
        23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
        43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62,
        63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82,
        83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101,
        102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117,
        118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133,
        134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149,
        150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
        166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181,
        182, 183, 184
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    OutPortBusy = RetFalse;
    ControlPortSend = RetFalse;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, DataCount, @"Should consume all data");
    
    CCQueueNode *Node;
    for (size_t Loop = 0; Loop < DataCount; Loop++)
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
    
    XCTAssertEqual(BufferState, 0, @"Should not change state");
}

static _Bool StartRead = FALSE;
static _Bool HandleControl(void)
{
    StartRead = TRUE;
    return TRUE;
}

static _Bool Reader1(void)
{
    _Bool Read = StartRead;
    StartRead = FALSE;
    return !Read;
}

-(void) testReadingSomeDataAfterFull
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
        23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
        43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62,
        63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82,
        83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101,
        102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117,
        118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133,
        134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149,
        150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
        166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181,
        182, 183, 184
    };
    
    StartRead = FALSE;
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    OutPortBusy = Reader1;
    ControlPortSend = HandleControl;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, DataCount - 1, @"Should not consume data once blocked");
    
    CCQueueNode *Node;
    for (size_t Loop = 0; Loop < 1; Loop++)
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
    
    XCTAssertEqual(BufferState, 1, @"Should not change state");
}

static _Bool Reader(void)
{
    return !StartRead;
}

-(void) testReadingAllDataAfterFull
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
        23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
        43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62,
        63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82,
        83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101,
        102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117,
        118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133,
        134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149,
        150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
        166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181,
        182, 183, 184
    };
    
    StartRead = FALSE;
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    OutPortBusy = Reader;
    ControlPortSend = HandleControl;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, DataCount, @"Should consume all data");
    
    CCQueueNode *Node;
    for (size_t Loop = 0; Loop < DataCount; Loop++)
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
    
    XCTAssertEqual(BufferState, 2, @"Should not change state");
}

-(void) testReadingAllDataAfterFullx2
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
        23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
        43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62,
        63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82,
        83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101,
        102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117,
        118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133,
        134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149,
        150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
        166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181,
        182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197,
        198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213,
        214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229,
        230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245,
        246, 247, 248, 249, 250, 251, 252, 253, 254, 255,
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
        23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
        43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62,
        63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82,
        83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101,
        102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117,
        118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133,
        134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149,
        150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
        166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181,
        182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197,
        198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213,
        214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229,
        230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245,
        246, 247, 248, 249, 250, 251, 252, 253, 254, 255,
    };
    
    StartRead = FALSE;
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    OutPortBusy = Reader;
    ControlPortSend = HandleControl;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, DataCount, @"Should consume all data");
    
    CCQueueNode *Node;
    for (size_t Loop = 0; Loop < DataCount; Loop++)
    {
        Node = CCQueuePop(ReadData);
        XCTAssertNotEqual(Node, NULL, @"Should have received data");
        if (Node)
        {
            XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), Data[Loop], @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive anymore data");
    
    XCTAssertEqual(BufferState, 2, @"Should not change state");
}

static _Bool HandleControlSwitch(void)
{
    StartRead = !StartRead;
    return TRUE;
}

-(void) testReadingAllDataAfterFullStopOnNextControl
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
        23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
        43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62,
        63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82,
        83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101,
        102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117,
        118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133,
        134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149,
        150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
        166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181,
        182, 183,
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
        23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
        43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62,
        63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82,
        83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101,
        102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117,
        118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133,
        134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149,
        150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
        166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181,
        182, 183,
        1,
    };
    
    StartRead = FALSE;
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    OutPortBusy = Reader;
    ControlPortSend = HandleControlSwitch;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, DataCount, @"Should consume all data");
    
    CCQueueNode *Node;
    for (size_t Loop = 0; Loop < DataCount - 1; Loop++)
    {
        Node = CCQueuePop(ReadData);
        XCTAssertNotEqual(Node, NULL, @"Should have received data");
        if (Node)
        {
            XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), Data[Loop], @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    Node = CCQueuePop(ReadData);
    XCTAssertEqual(Node, NULL, @"Should not receive anymore data");
    
    XCTAssertEqual(BufferState, 4, @"Should not change state");
}

@end
