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

@interface ProgramPassthrough1Tests : ProgramTests

@end

@implementation ProgramPassthrough1Tests

-(const char*) program
{
    return "assets/logic/programs/passthrough_1.chasm";
}

-(const char*) defines
{
    return ".define count, 255\n";
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

static CCQueue Pool[255] = {NULL};
static size_t PoolIndex = 0;
static _Bool PoolAutoInc = FALSE;
static HKHubArchPortResponse OutPort(HKHubArchPortConnection Connection, HKHubArchPortDevice Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    const HKHubArchPort *OppositePort = HKHubArchPortConnectionGetOppositePort(Connection, Device, Port);
    
    if (OppositePort->id != PoolIndex) return HKHubArchPortResponseTimeout;
    
    if (HKHubArchPortIsReady(OppositePort))
    {
        CCQueuePush(Pool[PoolIndex], CCQueueCreateNode(CC_STD_ALLOCATOR, Message->size, Message->memory + Message->offset));
        
        if (PoolAutoInc) PoolIndex = (PoolIndex + 1) % (sizeof(Pool) / sizeof(typeof(*Pool)));
        
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
    
    PoolAutoInc = FALSE;
    PoolIndex = 0;
    for (size_t Loop = 0; Loop < sizeof(Pool) / sizeof(typeof(*Pool)); Loop++)
    {
        Pool[Loop] = CCQueueCreate(CC_STD_ALLOCATOR);
        
        HKHubArchPortConnection Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(self.processor, Loop), (HKHubArchPort){
            .sender = NULL,
            .receiver = OutPort,
            .device = NULL,
            .destructor = NULL,
            .disconnect = NULL,
            .id = 0
        });
        
        HKHubArchProcessorConnect(self.processor, Loop, Conn);
        HKHubArchPortConnectionDestroy(Conn);
    }
    
    HKHubArchPortConnection Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(self.processor, 255), (HKHubArchPort){
        .sender = InPort,
        .receiver = NULL,
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
    for (size_t Loop = 0; Loop < sizeof(Pool) / sizeof(typeof(*Pool)); Loop++)
    {
        if (Pool[Loop]) CCQueueDestroy(Pool[Loop]);
    }
    
    [super tearDown];
}

-(void) testPassingToBusyPool
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    PoolIndex = 256;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, 1, @"Should consume only the first chunk");
    
    for (size_t Loop = 0; Loop < sizeof(Pool) / sizeof(typeof(*Pool)); Loop++)
    {
        CCQueueNode *Node = CCQueuePop(Pool[Loop]);
        XCTAssertEqual(Node, NULL, @"Should not receive any data");
    }
}

-(void) testPassingToSinglePool
{
    uint8_t Data[] = {
        1, 2, 3, 4, 5
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    PoolIndex = 0;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, DataCount, @"Should consume all the input data");
    
    for (size_t Loop = 0; Loop < DataCount; Loop++)
    {
        CCQueueNode *Node = CCQueuePop(Pool[0]);
        XCTAssertNotEqual(Node, NULL, @"Should have data");
        if (Node)
        {
            XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), Loop + 1, @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    for (size_t Loop = 1; Loop < sizeof(Pool) / sizeof(typeof(*Pool)); Loop++)
    {
        CCQueueNode *Node = CCQueuePop(Pool[Loop]);
        XCTAssertEqual(Node, NULL, @"Should not receive any data");
    }
}

-(void) testPassingToManyPools
{
    uint8_t Data[] = {
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
        22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41,
        42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61,
        62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81,
        82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100,
        101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116,
        117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132,
        133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148,
        149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164,
        165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180,
        181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196,
        197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212,
        213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228,
        229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244,
        245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 0, 1, 2, 3, 4, 5, 6, 7
    };
    
    InData = Data;
    DataCount = sizeof(Data) / sizeof(typeof(*Data));
    DataIndex = 0;
    PoolIndex = 0;
    PoolAutoInc = TRUE;
    
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(DataIndex, DataCount, @"Should consume all the input data");
    
    for (size_t Loop = 0; Loop < sizeof(Pool) / sizeof(typeof(*Pool)); Loop++)
    {
        CCQueueNode *Node = CCQueuePop(Pool[Loop]);
        XCTAssertNotEqual(Node, NULL, @"Should have data");
        if (Node)
        {
            XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), Loop, @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
        
        if (Loop <= 8)
        {
            Node = CCQueuePop(Pool[Loop]);
            XCTAssertNotEqual(Node, NULL, @"Should have data");
            if (Node)
            {
                XCTAssertEqual(*(uint8_t*)CCQueueGetNodeData(Node), (uint8_t)(Loop - 1), @"Should have the correct data");
                CCQueueDestroyNode(Node);
            }
        }
        
        Node = CCQueuePop(Pool[Loop]);
        XCTAssertEqual(Node, NULL, @"Should not have any data left");
    }
}

@end
