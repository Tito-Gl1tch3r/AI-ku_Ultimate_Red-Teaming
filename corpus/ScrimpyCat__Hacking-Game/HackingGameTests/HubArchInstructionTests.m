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

#import <XCTest/XCTest.h>
#import "HubArchProcessor.h"
#import "HubArchAssembly.h"
#import "HubArchScheduler.h"

#define HKHubArchProcessorSetCycles(p, c) p->status = HKHubArchProcessorStatusRunning; p->message.type = HKHubArchProcessorMessageClear; HKHubArchProcessorSetCycles(p, c)
#define HKHubArchAssemblyPrintError(err) if (Errors) { HKHubArchAssemblyPrintError(err); CCCollectionDestroy(err); err = NULL; }

#define AssertMemoryOp(x, a, b, c) \
_Static_assert((((x) >> HKHubArchInstructionMemoryOperationOp1) & HKHubArchInstructionMemoryOperationMask) == (a), "op1"); \
_Static_assert((((x) >> HKHubArchInstructionMemoryOperationOp2) & HKHubArchInstructionMemoryOperationMask) == (b), "op2"); \
_Static_assert((((x) >> HKHubArchInstructionMemoryOperationOp3) & HKHubArchInstructionMemoryOperationMask) == (c), "op3");

AssertMemoryOp(HKHubArchInstructionMemoryOperationNone, 0, 0, 0);
AssertMemoryOp(HKHubArchInstructionMemoryOperationS, HKHubArchInstructionMemoryOperationSrc, 0, 0);
AssertMemoryOp(HKHubArchInstructionMemoryOperationD, HKHubArchInstructionMemoryOperationDst, 0, 0);
AssertMemoryOp(HKHubArchInstructionMemoryOperationB, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, 0, 0);
AssertMemoryOp(HKHubArchInstructionMemoryOperationSS, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationSrc, 0);
AssertMemoryOp(HKHubArchInstructionMemoryOperationSD, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationDst, 0);
AssertMemoryOp(HKHubArchInstructionMemoryOperationSB, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, 0);
AssertMemoryOp(HKHubArchInstructionMemoryOperationDS, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc, 0);
AssertMemoryOp(HKHubArchInstructionMemoryOperationDD, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationDst, 0);
AssertMemoryOp(HKHubArchInstructionMemoryOperationDB, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, 0);
AssertMemoryOp(HKHubArchInstructionMemoryOperationBS, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc, 0);
AssertMemoryOp(HKHubArchInstructionMemoryOperationBD, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationDst, 0);
AssertMemoryOp(HKHubArchInstructionMemoryOperationBB, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, 0);
AssertMemoryOp(HKHubArchInstructionMemoryOperationSSS, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationSrc);
AssertMemoryOp(HKHubArchInstructionMemoryOperationSSD, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationDst);
AssertMemoryOp(HKHubArchInstructionMemoryOperationSSB, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst);
AssertMemoryOp(HKHubArchInstructionMemoryOperationSDS, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc);
AssertMemoryOp(HKHubArchInstructionMemoryOperationSDD, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationDst);
AssertMemoryOp(HKHubArchInstructionMemoryOperationSDB, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst);
AssertMemoryOp(HKHubArchInstructionMemoryOperationSBS, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc);
AssertMemoryOp(HKHubArchInstructionMemoryOperationSBD, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationDst);
AssertMemoryOp(HKHubArchInstructionMemoryOperationSBB, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst);
AssertMemoryOp(HKHubArchInstructionMemoryOperationDSS, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationSrc);
AssertMemoryOp(HKHubArchInstructionMemoryOperationDSD, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationDst);
AssertMemoryOp(HKHubArchInstructionMemoryOperationDSB, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst);
AssertMemoryOp(HKHubArchInstructionMemoryOperationDDS, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc);
AssertMemoryOp(HKHubArchInstructionMemoryOperationDDD, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationDst);
AssertMemoryOp(HKHubArchInstructionMemoryOperationDDB, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst);
AssertMemoryOp(HKHubArchInstructionMemoryOperationDBS, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc);
AssertMemoryOp(HKHubArchInstructionMemoryOperationDBD, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationDst);
AssertMemoryOp(HKHubArchInstructionMemoryOperationDBB, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst);
AssertMemoryOp(HKHubArchInstructionMemoryOperationBSS, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationSrc);
AssertMemoryOp(HKHubArchInstructionMemoryOperationBSD, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationDst);
AssertMemoryOp(HKHubArchInstructionMemoryOperationBSB, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst);
AssertMemoryOp(HKHubArchInstructionMemoryOperationBDS, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc);
AssertMemoryOp(HKHubArchInstructionMemoryOperationBDD, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationDst);
AssertMemoryOp(HKHubArchInstructionMemoryOperationBDB, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst);
AssertMemoryOp(HKHubArchInstructionMemoryOperationBBS, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc);
AssertMemoryOp(HKHubArchInstructionMemoryOperationBBD, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationDst);
AssertMemoryOp(HKHubArchInstructionMemoryOperationBBB, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst, HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst);

@interface HubArchInstructionTests : XCTestCase

@end

@implementation HubArchInstructionTests

static int PortDeallocs = 0;
static void PortAllocEvent(CCCallbackAllocatorEvent Event, void *Ptr, size_t *Size)
{
    if (Event == CCCallbackAllocatorEventDeallocatePre) PortDeallocs++;
}

-(void) testPortDestruction
{
    const char *Source = "hlt\n";
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor P1 = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchProcessor P2 = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchPortConnection Conn = HKHubArchPortConnectionCreate(CC_CALLBACK_ALLOCATOR(PortAllocEvent), HKHubArchProcessorGetPort(P1, 0), HKHubArchProcessorGetPort(P2, 1));
    
    HKHubArchProcessorConnect(P1, 0, Conn);
    HKHubArchProcessorConnect(P2, 1, Conn);
    
    HKHubArchPortConnectionDestroy(Conn);
    
    HKHubArchProcessorDisconnect(P1, 0);
    HKHubArchProcessorDisconnect(P2, 1);
    
    XCTAssertEqual(PortDeallocs, 1);
    
    
    Conn = HKHubArchPortConnectionCreate(CC_CALLBACK_ALLOCATOR(PortAllocEvent), HKHubArchProcessorGetPort(P1, 0), HKHubArchProcessorGetPort(P2, 1));
    
    HKHubArchProcessorConnect(P1, 0, Conn);
    HKHubArchProcessorConnect(P2, 1, Conn);
    
    HKHubArchPortConnectionDisconnect(Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    XCTAssertEqual(PortDeallocs, 2);
    
    
    Conn = HKHubArchPortConnectionCreate(CC_CALLBACK_ALLOCATOR(PortAllocEvent), HKHubArchProcessorGetPort(P1, 0), HKHubArchProcessorGetPort(P2, 0));
    
    HKHubArchProcessorConnect(P1, 0, Conn);
    HKHubArchProcessorConnect(P2, 0, Conn);
    
    HKHubArchPortConnectionDestroy(Conn);
    
    XCTAssertEqual(PortDeallocs, 2);
    
    
    Conn = HKHubArchPortConnectionCreate(CC_CALLBACK_ALLOCATOR(PortAllocEvent), HKHubArchProcessorGetPort(P1, 0), HKHubArchProcessorGetPort(P2, 1));
    
    HKHubArchProcessorConnect(P1, 0, Conn);
    HKHubArchProcessorConnect(P2, 1, Conn);
    
    HKHubArchPortConnectionDestroy(Conn);
    
    XCTAssertEqual(PortDeallocs, 3);
    
    HKHubArchProcessorDestroy(P1);
    
    XCTAssertEqual(PortDeallocs, 4);
    
    HKHubArchProcessorDestroy(P2);
}

-(void) testPCRollover
{
    const char *Source =
        "add r0, 1\n"
        ".byte                0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8\n"
        ".byte 0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8\n"
        ".byte 0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8\n"
        ".byte 0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8\n"
        ".byte 0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8\n"
        ".byte 0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8\n"
        ".byte 0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8\n"
        ".byte 0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8\n"
        ".byte 0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8\n"
        ".byte 0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8\n"
        ".byte 0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8\n"
        ".byte 0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8\n"
        ".byte 0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8\n"
        ".byte 0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8\n"
        ".byte 0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8\n"
        ".byte 0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8,0xf8\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    XCTAssertEqual(Processor->status, HKHubArchProcessorStatusRunning, @"Should change the status to trap");
    XCTAssertFalse(HKHubArchProcessorIsRunning(Processor), @"Should not be running");
    
    HKHubArchProcessorSetCycles(Processor, (256 * HKHubArchProcessorSpeedMemoryRead) + 3);
    XCTAssertTrue(HKHubArchProcessorIsRunning(Processor), @"Should be running");
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 1, @"Should have one unused cycle");
    XCTAssertEqual(Processor->state.pc, 0, @"Should return to beginning");
    XCTAssertEqual(Processor->state.r[0], 1, @"Should have the correct value");
    
    
    Processor->state.r[0] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, (((256 * HKHubArchProcessorSpeedMemoryRead) + 2) * 3) + 1);
    XCTAssertTrue(HKHubArchProcessorIsRunning(Processor), @"Should be running");
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 1, @"Should have one unused cycle");
    XCTAssertEqual(Processor->state.pc, 0, @"Should return to beginning");
    XCTAssertEqual(Processor->state.r[0], 3, @"Should have the correct value");
    
    
    
    Processor->memory[255] = Processor->memory[0];
    Processor->memory[0] = Processor->memory[1];
    Processor->memory[1] = Processor->memory[2];
    Processor->memory[2] = 0xf8;
    
    Processor->state.r[0] = 0;
    Processor->state.pc = 2;
    HKHubArchProcessorSetCycles(Processor, (((256 * HKHubArchProcessorSpeedMemoryRead) + 2) * 3) + 1);
    XCTAssertTrue(HKHubArchProcessorIsRunning(Processor), @"Should be running");
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 1, @"Should have one unused cycle");
    XCTAssertEqual(Processor->state.pc, 2, @"Should return to beginning");
    XCTAssertEqual(Processor->state.r[0], 3, @"Should have the correct value");
}

static int TestAccumulationFailedSequences = 0;
static uint8_t TestAccumulationSequenceSum = 0;
static HKHubArchPortResponse TestAccumulationSequence(HKHubArchPortConnection Connection, HKHubArchPortDevice Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    const HKHubArchPort *OppositePort = HKHubArchPortConnectionGetOppositePort(Connection, Device, Port);
    
    if (HKHubArchPortIsReady(OppositePort))
    {
        if (TestAccumulationSequenceSum + 1 != Message->memory[Message->offset]) TestAccumulationFailedSequences++;
        
        TestAccumulationSequenceSum = Message->memory[Message->offset];
    }
    
    return HKHubArchPortResponseSuccess;
}

-(void) testMessaging
{
    const char *Source =
        "repeat: send 0\n" //read(2) + instruction(4) + no timeouts
        "jmp repeat\n" //read(2) + instruction(1)
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Sender = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Source =
        "repeat: recv r2,[r3]\n" //cycles(6) = read(2) + instruction(4) + no timeouts
        "jmp repeat\n" //cycles(3) = read(2) + instruction(1)
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Receiver = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchPortConnection Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(Sender, 0), HKHubArchProcessorGetPort(Receiver, 1));
    HKHubArchProcessorConnect(Sender, 0, Conn);
    HKHubArchProcessorConnect(Receiver, 1, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    HKHubArchScheduler Scheduler = HKHubArchSchedulerCreate(CC_STD_ALLOCATOR);
    HKHubArchSchedulerAddProcessor(Scheduler, Sender);
    HKHubArchSchedulerAddProcessor(Scheduler, Receiver);
    
    
    Receiver->state.r[2] = 1;
    
    HKHubArchProcessorSetCycles(Sender, 9);
    HKHubArchProcessorSetCycles(Receiver, 9);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertEqual(Receiver->cycles, 0, @"Should have the unused cycles");
    XCTAssertEqual(Receiver->state.pc, 0, @"Should have reached the end");
    XCTAssertEqual(Sender->cycles, 0, @"Should have the unused cycles");
    XCTAssertEqual(Sender->state.pc, 0, @"Should have reached the end");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    HKHubArchProcessorSetCycles(Sender, 18);
    HKHubArchProcessorSetCycles(Receiver, 18);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertEqual(Receiver->cycles, 0, @"Should have the unused cycles");
    XCTAssertEqual(Receiver->state.pc, 0, @"Should have reached the end");
    XCTAssertEqual(Sender->cycles, 0, @"Should have the unused cycles");
    XCTAssertEqual(Sender->state.pc, 0, @"Should have reached the end");
    
    
    Source =
        "repeat: send 1\n" //read(2) + instruction(4) + timeout(8)
        "jmp repeat\n" //read(2) + instruction(1)
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Receiver, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchProcessorSetCycles(Sender, 9);
    HKHubArchProcessorSetCycles(Receiver, 9);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertEqual(Receiver->cycles, 9, @"Should have the unused cycles");
    XCTAssertEqual(Receiver->state.pc, 0, @"Should have reached the end");
    XCTAssertEqual(Sender->cycles, 9, @"Should have the unused cycles");
    XCTAssertEqual(Sender->state.pc, 0, @"Should have reached the end");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    HKHubArchProcessorSetCycles(Sender, 17);
    HKHubArchProcessorSetCycles(Receiver, 17);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertEqual(Receiver->cycles, 0, @"Should have the unused cycles");
    XCTAssertEqual(Receiver->state.pc, 0, @"Should have reached the end");
    XCTAssertEqual(Sender->cycles, 0, @"Should have the unused cycles");
    XCTAssertEqual(Sender->state.pc, 0, @"Should have reached the end");
    
    
    
    Source =
        "send 0, 1, [a]\n" //read(5) + instruction(4) + timeout(8)
        "send 1, 1, [b]\n" //read(5) + instruction(4) + no timeouts
        "hlt\n"
        "a: .byte 5\n"
        "b: .byte 10\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Sender, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Source =
        "recv r1,[r0]\n" //cycles(6) = read(2) + instruction(4) + no timeouts
        "recv r2,[r3]\n" //cycles(6) = read(2) + instruction(4) + no timeouts
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Receiver, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(Sender, 1), HKHubArchProcessorGetPort(Receiver, 0));
    HKHubArchProcessorConnect(Sender, 1, Conn);
    HKHubArchProcessorConnect(Receiver, 0, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    Receiver->state.r[1] = 0;
    Receiver->state.r[2] = 1;
    Receiver->state.r[0] = 50;
    Receiver->state.r[3] = 51;

    for (size_t SenderCycles = 0; SenderCycles <= 34; SenderCycles++)
    {
        for (size_t ReceiverCycles = 0; ReceiverCycles <= 28; ReceiverCycles++)
        {
            Receiver->memory[50] = 0;
            Receiver->memory[51] = 0;
            Receiver->state.pc = 0;
            Sender->state.pc = 0;
            
            HKHubArchProcessorSetCycles(Sender, SenderCycles);
            HKHubArchProcessorSetCycles(Receiver, ReceiverCycles);
            HKHubArchSchedulerRun(Scheduler, 0.0);
            
            if (SenderCycles < 6)
            {
                XCTAssertEqual(Receiver->cycles, ReceiverCycles - ((ReceiverCycles / 14) * 14) - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                XCTAssertEqual(Receiver->state.pc, (ReceiverCycles / 14) * 2, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                XCTAssertEqual(Sender->cycles, SenderCycles - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                XCTAssertEqual(Sender->state.pc, 0, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
            }
            
            else if ((SenderCycles >= 6) && (SenderCycles < 9))
            {
                XCTAssertEqual(Receiver->cycles, ReceiverCycles - ((ReceiverCycles / (14 + SenderCycles - 5)) * 14) - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                XCTAssertEqual(Receiver->state.pc, (ReceiverCycles / (14 + SenderCycles - 5)) * 2, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                XCTAssertEqual(Sender->cycles, SenderCycles - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                XCTAssertEqual(Sender->state.pc, 0, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
            }
            
            else if ((SenderCycles >= 9) && (SenderCycles < 14))
            {
                XCTAssertEqual(Receiver->cycles, ReceiverCycles == 28 ? 14 : ReceiverCycles - ((ReceiverCycles / 14) * 14) - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                XCTAssertEqual(Receiver->state.pc, ReceiverCycles == 28 ? 2 : (ReceiverCycles / 14) * 2, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                XCTAssertEqual(Sender->cycles, SenderCycles - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                XCTAssertEqual(Sender->state.pc, 0, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
            }
            
            else if ((SenderCycles >= 14) && (SenderCycles < 17))
            {
                if (ReceiverCycles >= 25)
                {
                    const size_t Max = (SenderCycles - 9) - ((25 - 14) - 6);
                    const size_t Cycles = ReceiverCycles - 25;
                    XCTAssertEqual(Receiver->cycles, (Cycles > Max ? Max : Cycles) - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->state.pc, 4, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[51], 5, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->cycles, (Cycles > Max ? Max : Cycles) - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->state.pc, 5, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                }
                
                else
                {
                    XCTAssertEqual(Receiver->cycles, ReceiverCycles - ((ReceiverCycles / 14) * 14) - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->state.pc, (ReceiverCycles / 14) * 2, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->cycles, SenderCycles - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->state.pc, 0, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                }
            }
            
            else if ((SenderCycles >= 17) && (SenderCycles < 23))
            {
                if (ReceiverCycles >= 25)
                {
                    const size_t Max = (SenderCycles - 9) - ((25 - 14) - 6);
                    const size_t Cycles = ReceiverCycles - 25;
                    XCTAssertEqual(Receiver->cycles, (Cycles > Max ? Max : Cycles) - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->state.pc, 4, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[51], 5, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->cycles, (Cycles > Max ? Max : Cycles) - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->state.pc, 5, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                }
                
                else if (ReceiverCycles >= (20 + (SenderCycles - 17)))
                {
                    XCTAssertEqual(Receiver->cycles, ReceiverCycles - ((ReceiverCycles / 14) * 14) - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->state.pc, (ReceiverCycles / 14) * 2, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->cycles, SenderCycles - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->state.pc, 0, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                }
                
                else
                {
                    XCTAssertEqual(Receiver->cycles, ReceiverCycles - ((ReceiverCycles / 14) * 14) - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->state.pc, (ReceiverCycles / 14) * 2, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->cycles, SenderCycles - 17 - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->state.pc, 5, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                }
            }
            
            else if ((SenderCycles >= 23) && (SenderCycles < 31))
            {
                if (ReceiverCycles >= (26 + (SenderCycles - 23)))
                {
                    const size_t Max = (SenderCycles - 9) - ((25 - 14) - 6);
                    const size_t Cycles = ReceiverCycles - 25;
                    XCTAssertEqual(Receiver->cycles, (Cycles > Max ? Max : Cycles) - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->state.pc, 4, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[51], 5, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->cycles, (Cycles > Max ? Max : Cycles) - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->state.pc, 5, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                }
                
                else if (ReceiverCycles >= (20 + (SenderCycles - 17)))
                {
                    XCTAssertEqual(Receiver->cycles, ReceiverCycles - ((ReceiverCycles / 14) * 14) - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->state.pc, (ReceiverCycles / 14) * 2, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->cycles, SenderCycles - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->state.pc, 0, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                }
                
                else
                {
                    XCTAssertEqual(Receiver->cycles, ReceiverCycles <= (14 + (SenderCycles - 23)) ? ReceiverCycles : ReceiverCycles - ((ReceiverCycles / 14) * 14) - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->state.pc, ReceiverCycles > (14 + (SenderCycles - 23)) ? (ReceiverCycles / 14) * 2 : 0, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->cycles, SenderCycles - 17 - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->state.pc, 5, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                }
            }
            
            else if ((SenderCycles >= 31) && (SenderCycles < 34))
            {
                const size_t CycleDiff = SenderCycles - 31;
                
                if (ReceiverCycles >= 28)
                {
                    XCTAssertEqual(Receiver->cycles, 0 - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->state.pc, 4, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->cycles, 14 + CycleDiff - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->state.pc, 5, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                }
                
                else if (ReceiverCycles >= (23 + CycleDiff))
                {
                    XCTAssertEqual(Receiver->cycles, (ReceiverCycles - 14) - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->state.pc, 2, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->cycles, 14 + CycleDiff - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->state.pc, 5, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                }
                
                else if (ReceiverCycles >= 11)
                {
                    size_t Cycles = ReceiverCycles - 11;
                    if (Cycles > CycleDiff) Cycles = CycleDiff;
                    
                    XCTAssertEqual(Receiver->cycles, Cycles - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->state.pc, 2, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[50], 10, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->cycles, (ReceiverCycles >= (20 + CycleDiff) ? 14 : 0) + Cycles - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->state.pc, (ReceiverCycles >= (20 + CycleDiff) ? 5 : 10), @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                }
                
                else
                {
                    XCTAssertEqual(Receiver->cycles, ReceiverCycles <= (14 + (SenderCycles - 23)) ? ReceiverCycles : ReceiverCycles - ((ReceiverCycles / 14) * 14) - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->state.pc, ReceiverCycles > (14 + (SenderCycles - 23)) ? (ReceiverCycles / 14) * 2 : 0, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->cycles, SenderCycles - 17 - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->state.pc, 5, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                }
            }
            
            else
            {
                if (ReceiverCycles >= 28)
                {
                    XCTAssertEqual(Receiver->cycles, 0 - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->state.pc, 4, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->cycles, 0 - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->state.pc, 10, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                }
                
                else if (ReceiverCycles >= 23)
                {
                    XCTAssertEqual(Receiver->cycles, (ReceiverCycles - 14) - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->state.pc, 2, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->cycles, 0 - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->state.pc, 10, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                }
                
                else if (ReceiverCycles >= 12)
                {
                    size_t Cycles = ReceiverCycles - 11;
                    if (Cycles > 3) Cycles = 3;
                    
                    XCTAssertEqual(Receiver->cycles, Cycles - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->state.pc, 2, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[50], 10, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->cycles, Cycles - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->state.pc, 10, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                }
                
                else if (ReceiverCycles >= 11)
                {
                    XCTAssertEqual(Receiver->cycles, 0 - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->state.pc, 2, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[50], 10, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->cycles, (ReceiverCycles >= 20 ? 14 : 0) - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->state.pc, (ReceiverCycles >= 20 ? 5 : 10), @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                }
                
                else
                {
                    XCTAssertEqual(Receiver->cycles, ReceiverCycles <= (14 + (SenderCycles - 23)) ? ReceiverCycles : ReceiverCycles - ((ReceiverCycles / 14) * 14) - (_Bool)(Receiver->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->state.pc, ReceiverCycles > (14 + (SenderCycles - 23)) ? (ReceiverCycles / 14) * 2 : 0, @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->cycles, (ReceiverCycles >= 6 ? 17 : 0) - (_Bool)(Sender->status & HKHubArchProcessorStatusIdle), @"Should have the correct amount of cycles left (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                    XCTAssertEqual(Sender->state.pc, (ReceiverCycles >= 6 ? 5 : 10), @"Should have the correct address (iteration: %zu, %zu)", SenderCycles, ReceiverCycles);
                }
            }
        }
    }
    
    Receiver->state.pc = 0;
    Sender->state.pc = 0;
    Receiver->memory[50] = 0;
    Receiver->memory[51] = 0;
    HKHubArchProcessorSetCycles(Sender, 31);
    HKHubArchProcessorSetCycles(Receiver, 14);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertEqual(Receiver->cycles, 0, @"Should not have any unused cycles");
    XCTAssertEqual(Receiver->memory[50], 10, @"Should have received value from second send");
    XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send");
    XCTAssertEqual(Sender->cycles, 0, @"Should not have any unused cycles");
    
    
    Receiver->memory[50] = 0;
    Receiver->memory[51] = 0;
    Receiver->state.pc = 0;
    Sender->state.pc = 0;
    HKHubArchProcessorSetCycles(Sender, 34);
    HKHubArchProcessorSetCycles(Receiver, 28);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertEqual(Receiver->cycles, 0, @"Should not have any unused cycles");
    XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send");
    XCTAssertEqual(Receiver->memory[51], 0, @"Should not have received value from first send");
    XCTAssertEqual(Sender->cycles, 0, @"Should not have any unused cycles");
    
    
    Receiver->memory[50] = 0;
    Receiver->memory[51] = 0;
    Receiver->state.pc = 0;
    Sender->state.pc = 0;
    HKHubArchProcessorSetCycles(Sender, 14);
    HKHubArchProcessorSetCycles(Receiver, 31);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertEqual(Receiver->cycles, 0, @"Should not have any unused cycles");
    XCTAssertEqual(Receiver->memory[50], 0, @"Should not have received value from second send");
    XCTAssertEqual(Receiver->memory[51], 5, @"Should not have received value from first send");
    XCTAssertEqual(Sender->cycles, 0, @"Should not have any unused cycles");
    
    
    Source =
        "send 0, 1, [a]\n" //read(5) + instruction(4) + timeout(8)
        "send 1, 1, [b]\n" //read(5) + instruction(4) + timeout(8)
        "hlt\n"
        "a: .byte 5\n"
        "b: .byte 10\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Receiver, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Receiver->state.pc = 0;
    Sender->state.pc = 0;
    HKHubArchProcessorSetCycles(Sender, 34);
    HKHubArchProcessorSetCycles(Receiver, 34);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertEqual(Receiver->cycles, 0, @"Should not have any unused cycles");
    XCTAssertEqual(Receiver->state.pc, 10, @"Should have reached the end");
    XCTAssertEqual(Sender->state.pc, 10, @"Should have reached the end");
    XCTAssertEqual(Sender->cycles, 0, @"Should not have any unused cycles");
    
    
    Receiver->state.pc = 0;
    Sender->state.pc = 0;
    HKHubArchProcessorSetCycles(Sender, 33);
    HKHubArchProcessorSetCycles(Receiver, 34);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertEqual(Receiver->cycles, 0, @"Should not have any unused cycles");
    XCTAssertEqual(Receiver->state.pc, 10, @"Should have reached the end");
    XCTAssertEqual(Sender->state.pc, 5, @"Should have reached the end");
    XCTAssertEqual(Sender->cycles, 16, @"Should not have unused cycles");
    
    
    // Test messaging crashed and halted devices
    Source = "hlt\n";
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Receiver, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Receiver->state.pc = 0;
    Sender->state.pc = 0;
    HKHubArchProcessorSetCycles(Sender, 34);
    HKHubArchProcessorSetCycles(Receiver, 34);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertEqual(Receiver->cycles, 33, @"Should not have any unused cycles");
    XCTAssertEqual(Receiver->state.pc, 0, @"Should have reached the end");
    XCTAssertEqual(Sender->state.pc, 10, @"Should have reached the end");
    XCTAssertEqual(Sender->cycles, 0, @"Should not have any unused cycles");
    
    
    Source = ".byte 0xa8\n"; //invalid opcode
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Receiver, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Receiver->state.pc = 0;
    Sender->state.pc = 0;
    HKHubArchProcessorSetCycles(Sender, 34);
    HKHubArchProcessorSetCycles(Receiver, 34);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertEqual(Receiver->cycles, 34, @"Should not have any unused cycles");
    XCTAssertEqual(Receiver->state.pc, 0, @"Should have reached the end");
    XCTAssertEqual(Sender->state.pc, 10, @"Should have reached the end");
    XCTAssertEqual(Sender->cycles, 0, @"Should not have any unused cycles");
    
    
    Source =
        "recv r1,[r0]\n" //cycles(6) = read(2) + instruction(4) + timeout(8)
        "recv r2,[r3]\n" //cycles(6) = read(2) + instruction(4) + timeout(8)
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Receiver, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Source = "hlt\n";
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Sender, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Receiver->state.pc = 0;
    Sender->state.pc = 0;
    HKHubArchProcessorSetCycles(Sender, 28);
    HKHubArchProcessorSetCycles(Receiver, 28);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertEqual(Receiver->cycles, 0, @"Should not have any unused cycles");
    XCTAssertEqual(Receiver->state.pc, 4, @"Should have reached the end");
    XCTAssertEqual(Sender->state.pc, 0, @"Should have reached the end");
    XCTAssertEqual(Sender->cycles, 27, @"Should not have any unused cycles");
    
    
    Source = ".byte 0xa8\n"; //invalid opcode
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Sender, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Receiver->state.pc = 0;
    Sender->state.pc = 0;
    HKHubArchProcessorSetCycles(Sender, 28);
    HKHubArchProcessorSetCycles(Receiver, 28);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertEqual(Receiver->cycles, 0, @"Should not have any unused cycles");
    XCTAssertEqual(Receiver->state.pc, 4, @"Should have reached the end");
    XCTAssertEqual(Sender->state.pc, 0, @"Should have reached the end");
    XCTAssertEqual(Sender->cycles, 28, @"Should not have any unused cycles");
    
    HKHubArchSchedulerDestroy(Scheduler);
    HKHubArchProcessorDestroy(Sender);
    HKHubArchProcessorDestroy(Receiver);
    
    
    
    Source =
        "repeat: send 0\n" //cycles(6) = read(2) + instruction(4) + no timeouts
        "jz fail\n" //cycles(3) = read(2) + instruction(1)
        "add r0,1\n" //cycles(5) = read(3) + instruction(2)
        "jmp repeat\n" //cycles(3) = read(2) + instruction(1)
        "fail: add r1,1\n" //cycles(5) = read(3) + instruction(2)
        "jmp repeat\n" //cycles(3) = read(2) + instruction(1)
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Sender = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Source =
        "repeat: recv r2,[r3]\n" //cycles(6) = read(2) + instruction(4) + no timeouts
        "jz fail\n" //cycles(3) = read(2) + instruction(1)
        "add r0,1\n" //cycles(5) = read(3) + instruction(2)
        "jmp repeat\n" //cycles(3) = read(2) + instruction(1)
        "fail: add r1,1\n" //cycles(5) = read(3) + instruction(2)
        "jmp repeat\n" //cycles(3) = read(2) + instruction(1)
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Receiver = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(Sender, 0), HKHubArchProcessorGetPort(Receiver, 1));
    HKHubArchProcessorConnect(Sender, 0, Conn);
    HKHubArchProcessorConnect(Receiver, 1, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    Scheduler = HKHubArchSchedulerCreate(CC_STD_ALLOCATOR);
    HKHubArchSchedulerAddProcessor(Scheduler, Sender);
    HKHubArchSchedulerAddProcessor(Scheduler, Receiver);
    
    Receiver->state.r[2] = 1;
    
    HKHubArchProcessorSetCycles(Sender, 17 * 3);
    HKHubArchProcessorSetCycles(Receiver, 17 * 3);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertEqual(Receiver->cycles, 0, @"Should have the unused cycles");
    XCTAssertEqual(Receiver->state.r[0], 3, @"Should succeed this many times");
    XCTAssertEqual(Receiver->state.r[1], 0, @"Should fail this many times");
    XCTAssertEqual(Sender->cycles, 0, @"Should have the unused cycles");
    XCTAssertEqual(Sender->state.r[0], 3, @"Should succeed this many times");
    XCTAssertEqual(Sender->state.r[1], 0, @"Should fail this many times");
    
    
    Receiver->state.pc = 0;
    Sender->state.pc = 0;
    Receiver->state.r[0] = 0;
    Sender->state.r[0] = 0;
    HKHubArchProcessorSetCycles(Sender, 17);
    HKHubArchProcessorSetCycles(Receiver, (17 * 2) + 8); //first will timeout
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertEqual(Receiver->cycles, 0, @"Should have the unused cycles");
    XCTAssertEqual(Receiver->state.r[0], 1, @"Should succeed this many times");
    XCTAssertEqual(Receiver->state.r[1], 1, @"Should fail this many times");
    XCTAssertEqual(Sender->cycles, 0, @"Should have the unused cycles");
    XCTAssertEqual(Sender->state.r[0], 1, @"Should succeed this many times");
    XCTAssertEqual(Sender->state.r[1], 0, @"Should fail this many times");
    
    HKHubArchSchedulerDestroy(Scheduler);
    HKHubArchProcessorDestroy(Sender);
    HKHubArchProcessorDestroy(Receiver);
    
    
    
    Source =
        "send 0\n" //cycles(6 or 14 with timeout) = read(2) + instruction(4) + no timeouts
        "hlt\n" //cycles(1) = read(1)
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Sender = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Source =
        "recv r2,[r3]\n" //cycles(6 or 14 with timeout) = read(2) + instruction(4) + no timeouts
        "hlt\n" //cycles(1) = read(1)
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Receiver = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(Sender, 0), HKHubArchProcessorGetPort(Receiver, 1));
    HKHubArchProcessorConnect(Sender, 0, Conn);
    HKHubArchProcessorConnect(Receiver, 1, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    Scheduler = HKHubArchSchedulerCreate(CC_STD_ALLOCATOR);
    HKHubArchSchedulerAddProcessor(Scheduler, Sender);
    HKHubArchSchedulerAddProcessor(Scheduler, Receiver);
    
    Receiver->state.r[2] = 1;
    
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 14);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 13);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 12);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 11);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 10);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 9);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 8);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 7);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 6);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = 0;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 5);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertTrue(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should fail");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = 0;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 4);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertTrue(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should fail");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = 0;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 3);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertTrue(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should fail");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = 0;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 2);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertTrue(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should fail");
    
    
    
    Source =
        "recv 1,[0+r0]\n" //cycles(8 or 16 with timeout) = read(4) + instruction(4) + no timeouts
        "hlt\n" //cycles(1) = read(1)
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Receiver, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Sender->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 14);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 13);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 12);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 11);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 10);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 9);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 8);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 7);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertTrue(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should fail");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 6);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertTrue(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should fail");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = 0;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 5);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertTrue(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should fail");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = 0;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 4);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertTrue(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should fail");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = 0;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 3);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertTrue(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should fail");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = 0;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 2);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertTrue(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should fail");
    
    
    
    Source =
        "send 0,0,[r0]\n" //cycles(8 or 16 with timeout) = read(4) + instruction(4) + no timeouts
        "hlt\n" //cycles(1) = read(1)
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Sender, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 14);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 13);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 12);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 11);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 10);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 9);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 8);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 7);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 6);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = 0;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 5);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertTrue(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should fail");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = 0;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 4);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertTrue(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should fail");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = 0;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 3);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertTrue(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should fail");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = 0;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 2);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertTrue(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should fail");
    
    
    
    Source =
        "send 0,0,[0]\n" //cycles(9 or 17 with timeout) = read(5) + instruction(4) + no timeouts
        "hlt\n" //cycles(1) = read(1)
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Sender, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 14);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 13);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 12);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 11);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 10);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 9);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 8);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 7);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 6);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = 0;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 5);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = 0;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 4);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertTrue(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should fail");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = 0;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 3);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertTrue(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should fail");
    
    
    Sender->state.pc = 0;
    Receiver->state.pc = 0;
    Sender->state.flags = 0;
    HKHubArchProcessorSetCycles(Sender, 14 * 2);
    HKHubArchProcessorSetCycles(Receiver, 14 + 2);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertTrue(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should fail");
    
    
    
    Source =
        ".byte 0, 0, 0, 0\n"
        ".entrypoint\n"
        "recv 1,[0]\n" //cycles(29) = read(4) + instruction(4) + wait(1) + transfer<4>(16) + write(4)
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Receiver, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Source =
        ".byte 1, 2, 3, 4\n"
        ".entrypoint\n"
        "send 0,4,[0]\n" //cycles(29) = read(5) + instruction(4) + read(4) + transfer<4>(16)
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Sender, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Sender, 29);
    HKHubArchProcessorSetCycles(Receiver, 29);
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertEqual(Sender->cycles, 0, @"Should have unused cycles");
    XCTAssertEqual(Receiver->cycles, 0, @"Should have unused cycles");
    XCTAssertFalse(Sender->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    XCTAssertFalse(Receiver->state.flags & HKHubArchProcessorFlagsZero, @"Should succeed");
    XCTAssertEqual(Receiver->memory[0], 1, @"Should transfer data");
    XCTAssertEqual(Receiver->memory[1], 2, @"Should transfer data");
    XCTAssertEqual(Receiver->memory[2], 3, @"Should transfer data");
    XCTAssertEqual(Receiver->memory[3], 4, @"Should transfer data");
    
    HKHubArchSchedulerDestroy(Scheduler);
    HKHubArchProcessorDestroy(Sender);
    HKHubArchProcessorDestroy(Receiver);
    
    
    
    Source =
        "repeat: send 0\n" //cycles(6) = read(2) + instruction(4) + timeout(8)
        "jmp repeat\n" //cycles(3) = read(2) + instruction(1)
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor P[3] = {
        HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary),
        HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary),
        HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary)
    };
    HKHubArchBinaryDestroy(Binary);
    
    
    Scheduler = HKHubArchSchedulerCreate(CC_STD_ALLOCATOR);
    for (size_t Loop = 0; Loop < 3; Loop++)
    {
        size_t Next = (Loop + 1) % 3;
        Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(P[Loop], 0), HKHubArchProcessorGetPort(P[Next], 1));
        HKHubArchProcessorConnect(P[Loop], 0, Conn);
        HKHubArchProcessorConnect(P[Next], 1, Conn);
        HKHubArchPortConnectionDestroy(Conn);
        
        HKHubArchProcessorSetCycles(P[Loop], 17);
        
        HKHubArchSchedulerAddProcessor(Scheduler, P[Loop]);
    }
    
    HKHubArchSchedulerRun(Scheduler, 0.0);
    XCTAssertEqual(P[0]->cycles, 0, @"Should have the unused cycles");
    XCTAssertEqual(P[0]->state.pc, 0, @"Should have reached the end");
    XCTAssertEqual(P[1]->cycles, 0, @"Should have the unused cycles");
    XCTAssertEqual(P[1]->state.pc, 0, @"Should have reached the end");
    XCTAssertEqual(P[2]->cycles, 0, @"Should have the unused cycles");
    XCTAssertEqual(P[2]->state.pc, 0, @"Should have reached the end");
    
    HKHubArchSchedulerDestroy(Scheduler);
    HKHubArchProcessorDestroy(P[0]);
    HKHubArchProcessorDestroy(P[1]);
    HKHubArchProcessorDestroy(P[2]);
    
    
    
    Source =
        ".define counter, 1\n"
        ".define test, 0\n"
        "data: .byte 0\n"
        ".entrypoint\n"
        "repeat:\n"
        "send counter, 1, [data]\n"
        "jz repeat\n"
        "get:\n"
        "recv counter, [data]\n"
        "jz get\n"
        "send test, 1, [data]\n"
        "jmp repeat\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Checker = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(Checker, 0), (HKHubArchPort){
        .sender = NULL,
        .receiver = TestAccumulationSequence,
        .device = NULL,
        .destructor = NULL,
        .disconnect = NULL,
        .id = 0
    });
    
    HKHubArchProcessorConnect(Checker, 0, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    Source =
        ".define checker, 0\n"
        "data: .byte 9\n"
        ".entrypoint\n"
        "repeat:\n"
        "recv checker, [data]\n"
        "jz repeat\n"
        "add [data], 1\n"
        "try_again:\n"
        "send checker, 1, [data]\n"
        "jz try_again\n"
        "jmp repeat\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Counter = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(Checker, 1), HKHubArchProcessorGetPort(Counter, 0));
    
    HKHubArchProcessorConnect(Checker, 1, Conn);
    HKHubArchProcessorConnect(Counter, 0, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    
    Scheduler = HKHubArchSchedulerCreate(CC_STD_ALLOCATOR);
    HKHubArchSchedulerAddProcessor(Scheduler, Checker);
    HKHubArchSchedulerAddProcessor(Scheduler, Counter);
    
    
    for (int Loop = 0; Loop < 100; Loop++)
    {
        HKHubArchSchedulerRun(Scheduler, 0.03);
    }
    
    XCTAssertEqual(TestAccumulationFailedSequences, 0, @"Accumulation sequences should be synced");
    XCTAssertTrue(TestAccumulationSequenceSum > 0, @"Accumulation must occur");
    
    HKHubArchSchedulerDestroy(Scheduler);
    HKHubArchProcessorDestroy(Counter);
    HKHubArchProcessorDestroy(Checker);
}

-(void) testHalting
{
    const char *Source = ".byte 0xa8\n"; //invalid opcode
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    XCTAssertEqual(Processor->status, HKHubArchProcessorStatusRunning, @"Should change the status to trap");
    XCTAssertFalse(HKHubArchProcessorIsRunning(Processor), @"Should not be running");
    
    HKHubArchProcessorSetCycles(Processor, 100);
    XCTAssertTrue(HKHubArchProcessorIsRunning(Processor), @"Should be running");
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 100, @"Should not clear any cycles");
    XCTAssertEqual(Processor->state.pc, 0, @"Should not progress");
    XCTAssertEqual(Processor->status, HKHubArchProcessorStatusTrap, @"Should change the status to trap");
    XCTAssertFalse(HKHubArchProcessorIsRunning(Processor), @"Should no longer be running");
    
    
    Source = "hlt\n";
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 100);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 99, @"Should have the unused cycles");
    XCTAssertEqual(Processor->state.pc, 0, @"Should not progress");
    XCTAssertEqual(Processor->status, HKHubArchProcessorStatusIdle, @"Should change the status to idle");
    XCTAssertFalse(HKHubArchProcessorIsRunning(Processor), @"Should no longer be running");
    
    
    HKHubArchProcessorDestroy(Processor);
}

-(void) testAddition
{
    const char *Source =
        "add r0,r1\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process add");
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 6 - (_Bool)(Processor->status & HKHubArchProcessorStatusIdle), @"Should have the unused cycles");
    XCTAssertEqual(Processor->state.pc, 2, @"Should have reached the end");
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 128, @"Should have the correct value");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = -2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], (uint8_t)-3, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 130, @"Should have the correct value");
    
    Processor->state.r[0] = 255;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    
    
    Source =
        "add flags,r1\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Processor->state.flags = 255;
    Processor->state.r[1] = 1;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    
    
    
    Source =
        "add pc,Skip - .\n"
        "hlt\n"
        "Skip: mov r0,123\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[0], 123, @"Should have the correct value");
    
    
    HKHubArchProcessorDestroy(Processor);
}

-(void) testSubtraction
{
    const char *Source =
        "sub r0,r1\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process add");
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 6 - (_Bool)(Processor->status & HKHubArchProcessorStatusIdle), @"Should have the unused cycles");
    XCTAssertEqual(Processor->state.pc, 2, @"Should have reached the end");
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 127, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 129, @"Should have the correct value");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 255, @"Should have the correct value");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 255;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 2, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 126, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 128, @"Should have the correct value");
    
    
    
    Source =
        "sub flags,r1\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Processor->state.flags = 1;
    Processor->state.r[1] = 1;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    
    
    
    Source =
        "sub pc,. - Skip\n"
        "hlt\n"
        "Skip: mov r0,123\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[0], 123, @"Should have the correct value");
    
    
    HKHubArchProcessorDestroy(Processor);
}

-(void) testMultiplication
{
    const char *Source =
        "mul r0,r1\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process add");
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 6 - (_Bool)(Processor->status & HKHubArchProcessorStatusIdle), @"Should have the unused cycles");
    XCTAssertEqual(Processor->state.pc, 2, @"Should have reached the end");
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 128, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 128, @"Should have the correct value");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 2;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], (uint8_t)-2, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 254, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 128, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 1, @"Should have the correct value");
    
    Processor->state.r[0] = 255;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 254, @"Should have the correct value");
    
    Processor->state.r[0] = 2;
    Processor->state.r[1] = 255;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 254, @"Should have the correct value");
    
    Processor->state.r[0] = -2;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsZero | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    
    
    Source =
        "mul flags,r1\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Processor->state.flags = 255;
    Processor->state.r[1] = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    
    
    
    Source =
        "nop\n"
        "mul pc,Skip\n"
        "hlt\n"
        "Skip: mov r0,123\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[0], 123, @"Should have the correct value");
    
    
    HKHubArchProcessorDestroy(Processor);
}

-(void) testDivision
{
    const char *Source =
        "sdiv r0,r1\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process add");
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 5 - (_Bool)(Processor->status & HKHubArchProcessorStatusIdle), @"Should have the unused cycles");
    XCTAssertEqual(Processor->state.pc, 2, @"Should have reached the end");
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 128, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 128, @"Should have the correct value");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 2;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], (uint8_t)-2, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 63, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 1, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 1, @"Should have the correct value");
    
    Processor->state.r[0] = 255;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 2;
    Processor->state.r[1] = 255;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], (uint8_t)-2, @"Should have the correct value");
    
    Processor->state.r[0] = 246;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], (uint8_t)-5, @"Should have the correct value");
    
    Processor->state.r[0] = 246;
    Processor->state.r[1] = -2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 5, @"Should have the correct value");
    
    Processor->state.r[0] = -56;
    Processor->state.r[1] = -127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = -127;
    Processor->state.r[1] = -56;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 2, @"Should have the correct value");
    
    
    
    Source =
        "sdiv flags,r1\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Processor->state.flags = 1;
    Processor->state.r[1] = 1;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    
    
    
    Source =
        "udiv r0,r1\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process add");
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 5 - (_Bool)(Processor->status & HKHubArchProcessorStatusIdle), @"Should have the unused cycles");
    XCTAssertEqual(Processor->state.pc, 2, @"Should have reached the end");
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 128, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 2;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 63, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 1, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 1, @"Should have the correct value");
    
    Processor->state.r[0] = 255;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 127, @"Should have the correct value");
    
    Processor->state.r[0] = 2;
    Processor->state.r[1] = 255;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 246;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 123, @"Should have the correct value");
    
    Processor->state.r[0] = 246;
    Processor->state.r[1] = -2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    
    
    Source =
        "udiv flags,r1\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Processor->state.flags = 1;
    Processor->state.r[1] = 1;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    
    
    HKHubArchProcessorDestroy(Processor);
}

-(void) testModulo
{
    const char *Source =
        "smod r0,r1\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process add");
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 5 - (_Bool)(Processor->status & HKHubArchProcessorStatusIdle), @"Should have the unused cycles");
    XCTAssertEqual(Processor->state.pc, 2, @"Should have reached the end");
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 2;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 1, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 127, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = -56;
    Processor->state.r[1] = -127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], (uint8_t)-56, @"Should have the correct value");
    
    Processor->state.r[0] = -127;
    Processor->state.r[1] = -56;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], (uint8_t)-15, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 255;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], (uint8_t)-1, @"Should have the correct value");
    
    Processor->state.r[0] = 2;
    Processor->state.r[1] = 255;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 246;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 246;
    Processor->state.r[1] = -2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    
    
    Source =
        "smod flags,r1\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Processor->state.flags = 1;
    Processor->state.r[1] = 1;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    
    
    
    Source =
        "umod r0,r1\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process add");
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 5 - (_Bool)(Processor->status & HKHubArchProcessorStatusIdle), @"Should have the unused cycles");
    XCTAssertEqual(Processor->state.pc, 2, @"Should have reached the end");
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 128, @"Should have the correct value");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 2;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 2, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 1, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 127, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 255;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 1, @"Should have the correct value");
    
    Processor->state.r[0] = 2;
    Processor->state.r[1] = 255;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 2, @"Should have the correct value");
    
    Processor->state.r[0] = 246;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 246;
    Processor->state.r[1] = -2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 246, @"Should have the correct value");
    
    
    
    Source =
        "umod flags,r1\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Processor->state.flags = 1;
    Processor->state.r[1] = 1;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    
    
    HKHubArchProcessorDestroy(Processor);
}

-(void) testLeftShift
{
    const char *Source =
        "shl r0,r1\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process add");
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 7 - (_Bool)(Processor->status & HKHubArchProcessorStatusIdle), @"Should have the unused cycles");
    XCTAssertEqual(Processor->state.pc, 2, @"Should have reached the end");
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 254, @"Should have the correct value");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 252, @"Should have the correct value");
    
    Processor->state.r[0] = 129;
    Processor->state.r[1] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 129, @"Should have the correct value");
    
    Processor->state.r[0] = 129;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 2, @"Should have the correct value");
    
    Processor->state.r[0] = 129;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 4, @"Should have the correct value");
    
    Processor->state.r[0] = 129;
    Processor->state.r[1] = 8;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsZero | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 129;
    Processor->state.r[1] = 9;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    
    
    Source =
        "shl flags,r1\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Processor->state.flags = 0x80;
    Processor->state.r[1] = 1;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsZero | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    
    
    HKHubArchProcessorDestroy(Processor);
}

-(void) testRightShift
{
    const char *Source =
        "shr r0,r1\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process add");
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 7 - (_Bool)(Processor->status & HKHubArchProcessorStatusIdle), @"Should have the unused cycles");
    XCTAssertEqual(Processor->state.pc, 2, @"Should have reached the end");
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 254;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 127, @"Should have the correct value");
    
    Processor->state.r[0] = 254;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 63, @"Should have the correct value");
    
    Processor->state.r[0] = 129;
    Processor->state.r[1] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 129, @"Should have the correct value");
    
    Processor->state.r[0] = 129;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 64, @"Should have the correct value");
    
    Processor->state.r[0] = 129;
    Processor->state.r[1] = 2;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 32, @"Should have the correct value");
    
    Processor->state.r[0] = 129;
    Processor->state.r[1] = 8;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsZero | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 129;
    Processor->state.r[1] = 9;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    
    
    Source =
        "shr flags,r1\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Processor->state.flags = 1;
    Processor->state.r[1] = 1;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsZero | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    
    
    HKHubArchProcessorDestroy(Processor);
}

-(void) testXor
{
    const char *Source =
        "xor r0,r1\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process add");
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 7 - (_Bool)(Processor->status & HKHubArchProcessorStatusIdle), @"Should have the unused cycles");
    XCTAssertEqual(Processor->state.pc, 2, @"Should have reached the end");
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 7;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 6, @"Should have the correct value");
    
    Processor->state.r[0] = 7;
    Processor->state.r[1] = 7;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 7;
    Processor->state.r[1] = 0x80;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0x87, @"Should have the correct value");
    
    
    
    Source =
        "xor flags,r1\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Processor->state.flags = 1;
    Processor->state.r[1] = 1;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    
    
    HKHubArchProcessorDestroy(Processor);
}

-(void) testOr
{
    const char *Source =
        "or r0,r1\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process add");
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 7 - (_Bool)(Processor->status & HKHubArchProcessorStatusIdle), @"Should have the unused cycles");
    XCTAssertEqual(Processor->state.pc, 2, @"Should have reached the end");
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 7;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 7, @"Should have the correct value");
    
    Processor->state.r[0] = 7;
    Processor->state.r[1] = 7;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 7, @"Should have the correct value");
    
    Processor->state.r[0] = 7;
    Processor->state.r[1] = 0x80;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0x87, @"Should have the correct value");
    
    
    
    Source =
        "or flags,r1\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Processor->state.flags = 0;
    Processor->state.r[1] = 1;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    
    
    HKHubArchProcessorDestroy(Processor);
}

-(void) testAnd
{
    const char *Source =
        "and r0,r1\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process add");
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 7 - (_Bool)(Processor->status & HKHubArchProcessorStatusIdle), @"Should have the unused cycles");
    XCTAssertEqual(Processor->state.pc, 2, @"Should have reached the end");
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 7;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 1, @"Should have the correct value");
    
    Processor->state.r[0] = 7;
    Processor->state.r[1] = 7;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 7, @"Should have the correct value");
    
    Processor->state.r[0] = 7;
    Processor->state.r[1] = 0x80;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 0x87;
    Processor->state.r[1] = 0x80;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0x80, @"Should have the correct value");
    
    
    
    Source =
        "and flags,r1\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Processor->state.flags = 1;
    Processor->state.r[1] = 1;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    
    
    HKHubArchProcessorDestroy(Processor);
}

-(void) testNot
{
    const char *Source =
        "not r0\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process add");
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 7 - (_Bool)(Processor->status & HKHubArchProcessorStatusIdle), @"Should have the unused cycles");
    XCTAssertEqual(Processor->state.pc, 2, @"Should have reached the end");
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 255, @"Should have the correct value");
    
    Processor->state.r[0] = 7;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0xf8, @"Should have the correct value");
    
    Processor->state.r[0] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0xfe, @"Should have the correct value");
    
    Processor->state.r[0] = 0x88;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0x77, @"Should have the correct value");
    
    Processor->state.r[0] = 255;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    
    
    Source =
        "not flags\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Processor->state.flags = 255;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    
    
    HKHubArchProcessorDestroy(Processor);
}

-(void) testNeg
{
    const char *Source =
        "neg r0\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process add");
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 7 - (_Bool)(Processor->status & HKHubArchProcessorStatusIdle), @"Should have the unused cycles");
    XCTAssertEqual(Processor->state.pc, 2, @"Should have reached the end");
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 7;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], (uint8_t)-7, @"Should have the correct value");
    
    Processor->state.r[0] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], (uint8_t)-1, @"Should have the correct value");
    
    Processor->state.r[0] = 255;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 1, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 128, @"Should have the correct value");
    
    
    
    Source =
        "neg flags\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Processor->state.flags = 255;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    
    
    HKHubArchProcessorDestroy(Processor);
}

-(void) testComparison
{
    const char *Source =
        "cmp r0,r1\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process add");
    
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 6 - (_Bool)(Processor->status & HKHubArchProcessorStatusIdle), @"Should have the unused cycles");
    XCTAssertEqual(Processor->state.pc, 2, @"Should have reached the end");
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 128, @"Should be unchanged");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 128, @"Should be unchanged");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should be unchanged");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 255;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 1, @"Should be unchanged");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 127, @"Should be unchanged");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsCarry, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 127, @"Should be unchanged");
    
    
    
    Source =
        "mov r2,1\n"
        "cmp r0,r1\n"
        "jz skip\n"
        "mov r2,0\n"
        "skip: hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 5;
    Processor->state.r[1] = 20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 20;
    Processor->state.r[1] = 5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -5;
    Processor->state.r[1] = -20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -20;
    Processor->state.r[1] = -5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    
    
    Source =
        "mov r2,1\n"
        "cmp r0,r1\n"
        "jnz skip\n"
        "mov r2,0\n"
        "skip: hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 5;
    Processor->state.r[1] = 20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 20;
    Processor->state.r[1] = 5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -5;
    Processor->state.r[1] = -20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -20;
    Processor->state.r[1] = -5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    
    
    Source =
        "mov r2,1\n"
        "cmp r0,r1\n"
        "js skip\n"
        "mov r2,0\n"
        "skip: hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 5;
    Processor->state.r[1] = 20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 20;
    Processor->state.r[1] = 5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -5;
    Processor->state.r[1] = -20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -20;
    Processor->state.r[1] = -5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    
    
    Source =
        "mov r2,1\n"
        "cmp r0,r1\n"
        "jns skip\n"
        "mov r2,0\n"
        "skip: hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 5;
    Processor->state.r[1] = 20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 20;
    Processor->state.r[1] = 5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -5;
    Processor->state.r[1] = -20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -20;
    Processor->state.r[1] = -5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    
    
    Source =
        "mov r2,1\n"
        "cmp r0,r1\n"
        "jo skip\n"
        "mov r2,0\n"
        "skip: hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 5;
    Processor->state.r[1] = 20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 20;
    Processor->state.r[1] = 5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -5;
    Processor->state.r[1] = -20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -20;
    Processor->state.r[1] = -5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    
    
    Source =
        "mov r2,1\n"
        "cmp r0,r1\n"
        "jno skip\n"
        "mov r2,0\n"
        "skip: hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 5;
    Processor->state.r[1] = 20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 20;
    Processor->state.r[1] = 5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -5;
    Processor->state.r[1] = -20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -20;
    Processor->state.r[1] = -5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    
    
    Source =
        "mov r2,1\n"
        "cmp r0,r1\n"
        "jsl skip\n"
        "mov r2,0\n"
        "skip: hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 5;
    Processor->state.r[1] = 20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 20;
    Processor->state.r[1] = 5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -5;
    Processor->state.r[1] = -20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -20;
    Processor->state.r[1] = -5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    
    
    Source =
        "mov r2,1\n"
        "cmp r0,r1\n"
        "jsge skip\n"
        "mov r2,0\n"
        "skip: hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 5;
    Processor->state.r[1] = 20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 20;
    Processor->state.r[1] = 5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -5;
    Processor->state.r[1] = -20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -20;
    Processor->state.r[1] = -5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    
    
    Source =
        "mov r2,1\n"
        "cmp r0,r1\n"
        "jsle skip\n"
        "mov r2,0\n"
        "skip: hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 5;
    Processor->state.r[1] = 20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 20;
    Processor->state.r[1] = 5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -5;
    Processor->state.r[1] = -20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -20;
    Processor->state.r[1] = -5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    
    
    Source =
        "mov r2,1\n"
        "cmp r0,r1\n"
        "jsg skip\n"
        "mov r2,0\n"
        "skip: hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 5;
    Processor->state.r[1] = 20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 20;
    Processor->state.r[1] = 5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -5;
    Processor->state.r[1] = -20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -20;
    Processor->state.r[1] = -5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    
    
    Source =
        "mov r2,1\n"
        "cmp r0,r1\n"
        "jul skip\n"
        "mov r2,0\n"
        "skip: hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 5;
    Processor->state.r[1] = 20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 20;
    Processor->state.r[1] = 5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -5;
    Processor->state.r[1] = -20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -20;
    Processor->state.r[1] = -5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    
    
    Source =
        "mov r2,1\n"
        "cmp r0,r1\n"
        "juge skip\n"
        "mov r2,0\n"
        "skip: hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 5;
    Processor->state.r[1] = 20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 20;
    Processor->state.r[1] = 5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -5;
    Processor->state.r[1] = -20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -20;
    Processor->state.r[1] = -5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    
    
    Source =
        "mov r2,1\n"
        "cmp r0,r1\n"
        "jule skip\n"
        "mov r2,0\n"
        "skip: hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 5;
    Processor->state.r[1] = 20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 20;
    Processor->state.r[1] = 5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -5;
    Processor->state.r[1] = -20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -20;
    Processor->state.r[1] = -5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    
    
    Source =
        "mov r2,1\n"
        "cmp r0,r1\n"
        "jug skip\n"
        "mov r2,0\n"
        "skip: hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = -1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 0;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 1;
    Processor->state.r[1] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -1;
    Processor->state.r[1] = 1;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 128;
    Processor->state.r[1] = 127;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = 127;
    Processor->state.r[1] = 128;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 5;
    Processor->state.r[1] = 20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    Processor->state.r[0] = 20;
    Processor->state.r[1] = 5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -5;
    Processor->state.r[1] = -20;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 1, @"Jump should be taken");
    
    Processor->state.r[0] = -20;
    Processor->state.r[1] = -5;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 20);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.r[2], 0, @"Jump should not be taken");
    
    
    
    Source =
        "cmp flags,r1\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    Processor->state.flags = HKHubArchProcessorFlagsZero;
    Processor->state.r[1] = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Processor, 10);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.flags, HKHubArchProcessorFlagsZero, @"Should have the correct value");
    
    
    HKHubArchProcessorDestroy(Processor);
}

-(void) testMoving
{
    const char *Source =
        "mov r0,value\n"
        "mov r1,[value]\n"
        "mov r2,[value+1]\n"
        "mov r3,[value+r1]\n"
        "mov [r0+r1],r2\n"
        "mov [r0+r2],r1\n"
        "mov r0,[r0+r2]\n"
        "mov flags,5\n"
        "mov pc,value+4\n"
        "value: .byte 3, 2, 1, 0\n"
        "mov r0,0\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process first move");
    
    HKHubArchProcessorSetCycles(Processor, 100);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->cycles, 54 - (_Bool)(Processor->status & HKHubArchProcessorStatusIdle), @"Should have the unused cycles");
    XCTAssertEqual(Processor->state.pc, 34, @"Should have reached the end");
    XCTAssertEqual(Processor->state.flags, 5, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[1], 3, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[2], 2, @"Should have the correct value");
    XCTAssertEqual(Processor->state.r[3], 0, @"Should have the correct value");
    
    HKHubArchProcessorDestroy(Processor);
}

-(void) testBranching
{
    const char *Source =
        "A: jmp C\n"
        "B: jmp D\n"
        "C: jmp B\n"
        "D: jmp F\n"
        "E: jmp A\n"
        "F: jmp E\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process first jump");
    
    HKHubArchProcessorSetCycles(Processor, 2);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process first jump");
    
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 4, @"Processes first jump");
    
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 4);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 4, @"Processes first jump but not enough for second jump");
    
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 5);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 4, @"Processes first jump but not enough for second jump");
    
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 6);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes first jump and second jump");
    
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 18);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Processes all jumps once");
    
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 21);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 4, @"Processes all jumps once and first jump");
    
    HKHubArchProcessorDestroy(Processor);
    
    
    
    Source = "jz A\nnop\nA: nop\n";
    
    AST = HKHubArchAssemblyParse(Source);
    
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Processor->state.flags = HKHubArchProcessorFlagsZero;
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 2);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    //ZF = 1
    _Bool ResultsJZ[16] = {
        //0000  000z  00c0  00cz
        FALSE, TRUE, FALSE, TRUE,
        //0s00  0s0z  0sc0  0scz
        FALSE, TRUE, FALSE, TRUE,
        //o000  o00z  o0c0  o0cz
        FALSE, TRUE, FALSE, TRUE,
        //os00  os0z  osc0  oscz
        FALSE, TRUE, FALSE, TRUE
    };
    
    for (int Loop = 0; Loop < 16; Loop++)
    {
        Processor->state.flags = Loop;
        Processor->state.pc = 0;
        HKHubArchProcessorSetCycles(Processor, 3);
        HKHubArchProcessorRun(Processor);
        if (ResultsJZ[Loop]) XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
        else XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    }
    
    HKHubArchProcessorDestroy(Processor);
    
    
    
    Source = "jnz A\nnop\nA: nop\n";
    
    AST = HKHubArchAssemblyParse(Source);
    
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Processor->state.flags = 0;
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 2);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags = HKHubArchProcessorFlagsZero;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    //ZF = 0
    _Bool ResultsJNZ[16] = {
        //0000  000z  00c0  00cz
        TRUE, FALSE, TRUE, FALSE,
        //0s00  0s0z  0sc0  0scz
        TRUE, FALSE, TRUE, FALSE,
        //o000  o00z  o0c0  o0cz
        TRUE, FALSE, TRUE, FALSE,
        //os00  os0z  osc0  oscz
        TRUE, FALSE, TRUE, FALSE
    };
    
    for (int Loop = 0; Loop < 16; Loop++)
    {
        Processor->state.flags = Loop;
        Processor->state.pc = 0;
        HKHubArchProcessorSetCycles(Processor, 3);
        HKHubArchProcessorRun(Processor);
        if (ResultsJNZ[Loop]) XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
        else XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    }
    
    HKHubArchProcessorDestroy(Processor);
    
    
    
    Source = "js A\nnop\nA: nop\n";
    
    AST = HKHubArchAssemblyParse(Source);
    
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Processor->state.flags = HKHubArchProcessorFlagsSign;
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 2);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    //SF = 1
    _Bool ResultsJS[16] = {
        //0000  000z  00c0  00cz
        FALSE, FALSE, FALSE, FALSE,
        //0s00  0s0z  0sc0  0scz
        TRUE, TRUE, TRUE, TRUE,
        //o000  o00z  o0c0  o0cz
        FALSE, FALSE, FALSE, FALSE,
        //os00  os0z  osc0  oscz
        TRUE, TRUE, TRUE, TRUE
    };
    
    for (int Loop = 0; Loop < 16; Loop++)
    {
        Processor->state.flags = Loop;
        Processor->state.pc = 0;
        HKHubArchProcessorSetCycles(Processor, 3);
        HKHubArchProcessorRun(Processor);
        if (ResultsJS[Loop]) XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
        else XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    }
    
    HKHubArchProcessorDestroy(Processor);
    
    
    
    Source = "jns A\nnop\nA: nop\n";
    
    AST = HKHubArchAssemblyParse(Source);
    
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Processor->state.flags = 0;
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 2);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags = HKHubArchProcessorFlagsSign;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    //SF = 1
    _Bool ResultsJNS[16] = {
        //0000  000z  00c0  00cz
        TRUE, TRUE, TRUE, TRUE,
        //0s00  0s0z  0sc0  0scz
        FALSE, FALSE, FALSE, FALSE,
        //o000  o00z  o0c0  o0cz
        TRUE, TRUE, TRUE, TRUE,
        //os00  os0z  osc0  oscz
        FALSE, FALSE, FALSE, FALSE
    };
    
    for (int Loop = 0; Loop < 16; Loop++)
    {
        Processor->state.flags = Loop;
        Processor->state.pc = 0;
        HKHubArchProcessorSetCycles(Processor, 3);
        HKHubArchProcessorRun(Processor);
        if (ResultsJNS[Loop]) XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
        else XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    }
    
    HKHubArchProcessorDestroy(Processor);
    
    
    
    Source = "jo A\nnop\nA: nop\n";
    
    AST = HKHubArchAssemblyParse(Source);
    
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Processor->state.flags = HKHubArchProcessorFlagsOverflow;
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 2);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    //OF = 1
    _Bool ResultsJO[16] = {
        //0000  000z  00c0  00cz
        FALSE, FALSE, FALSE, FALSE,
        //0s00  0s0z  0sc0  0scz
        FALSE, FALSE, FALSE, FALSE,
        //o000  o00z  o0c0  o0cz
        TRUE, TRUE, TRUE, TRUE,
        //os00  os0z  osc0  oscz
        TRUE, TRUE, TRUE, TRUE
    };
    
    for (int Loop = 0; Loop < 16; Loop++)
    {
        Processor->state.flags = Loop;
        Processor->state.pc = 0;
        HKHubArchProcessorSetCycles(Processor, 3);
        HKHubArchProcessorRun(Processor);
        if (ResultsJO[Loop]) XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
        else XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    }
    
    HKHubArchProcessorDestroy(Processor);
    
    
    
    Source = "jno A\nnop\nA: nop\n";
    
    AST = HKHubArchAssemblyParse(Source);
    
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Processor->state.flags = 0;
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 2);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags = HKHubArchProcessorFlagsOverflow;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    //OF = 0
    _Bool ResultsJNO[16] = {
        //0000  000z  00c0  00cz
        TRUE, TRUE, TRUE, TRUE,
        //0s00  0s0z  0sc0  0scz
        TRUE, TRUE, TRUE, TRUE,
        //o000  o00z  o0c0  o0cz
        FALSE, FALSE, FALSE, FALSE,
        //os00  os0z  osc0  oscz
        FALSE, FALSE, FALSE, FALSE
    };
    
    for (int Loop = 0; Loop < 16; Loop++)
    {
        Processor->state.flags = Loop;
        Processor->state.pc = 0;
        HKHubArchProcessorSetCycles(Processor, 3);
        HKHubArchProcessorRun(Processor);
        if (ResultsJNO[Loop]) XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
        else XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    }
    
    HKHubArchProcessorDestroy(Processor);
    
    
    
    Source = "jsl A\nnop\nA: nop\n";
    
    AST = HKHubArchAssemblyParse(Source);
    
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Processor->state.flags = HKHubArchProcessorFlagsOverflow;
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 2);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags |= HKHubArchProcessorFlagsSign;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    Processor->state.flags = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    Processor->state.flags = HKHubArchProcessorFlagsSign;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    //SF <> OF
    _Bool ResultsJSL[16] = {
        //0000  000z  00c0  00cz
        FALSE, FALSE, FALSE, FALSE,
        //0s00  0s0z  0sc0  0scz
        TRUE, TRUE, TRUE, TRUE,
        //o000  o00z  o0c0  o0cz
        TRUE, TRUE, TRUE, TRUE,
        //os00  os0z  osc0  oscz
        FALSE, FALSE, FALSE, FALSE
    };
    
    for (int Loop = 0; Loop < 16; Loop++)
    {
        Processor->state.flags = Loop;
        Processor->state.pc = 0;
        HKHubArchProcessorSetCycles(Processor, 3);
        HKHubArchProcessorRun(Processor);
        if (ResultsJSL[Loop]) XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
        else XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    }
    
    HKHubArchProcessorDestroy(Processor);
    
    
    
    Source = "jsge A\nnop\nA: nop\n";
    
    AST = HKHubArchAssemblyParse(Source);
    
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Processor->state.flags = HKHubArchProcessorFlagsOverflow;
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 2);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    Processor->state.flags |= HKHubArchProcessorFlagsSign;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags = HKHubArchProcessorFlagsSign;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    //SF = OF
    _Bool ResultsJSGE[16] = {
        //0000  000z  00c0  00cz
        TRUE, TRUE, TRUE, TRUE,
        //0s00  0s0z  0sc0  0scz
        FALSE, FALSE, FALSE, FALSE,
        //o000  o00z  o0c0  o0cz
        FALSE, FALSE, FALSE, FALSE,
        //os00  os0z  osc0  oscz
        TRUE, TRUE, TRUE, TRUE
    };
    
    for (int Loop = 0; Loop < 16; Loop++)
    {
        Processor->state.flags = Loop;
        Processor->state.pc = 0;
        HKHubArchProcessorSetCycles(Processor, 3);
        HKHubArchProcessorRun(Processor);
        if (ResultsJSGE[Loop]) XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
        else XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    }
    
    HKHubArchProcessorDestroy(Processor);
    
    
    
    Source = "jsle A\nnop\nA: nop\n";
    
    AST = HKHubArchAssemblyParse(Source);
    
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Processor->state.flags = HKHubArchProcessorFlagsOverflow;
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 2);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags |= HKHubArchProcessorFlagsSign;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    Processor->state.flags = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    Processor->state.flags = HKHubArchProcessorFlagsSign;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags = HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsZero;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags |= HKHubArchProcessorFlagsSign;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags = HKHubArchProcessorFlagsZero;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags |= HKHubArchProcessorFlagsSign;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    //ZF = 1 or SF <> OF
    _Bool ResultsJSLE[16] = {
        //0000  000z  00c0  00cz
        FALSE, TRUE, FALSE, TRUE,
        //0s00  0s0z  0sc0  0scz
        TRUE, TRUE, TRUE, TRUE,
        //o000  o00z  o0c0  o0cz
        TRUE, TRUE, TRUE, TRUE,
        //os00  os0z  osc0  oscz
        FALSE, TRUE, FALSE, TRUE
    };
    
    for (int Loop = 0; Loop < 16; Loop++)
    {
        Processor->state.flags = Loop;
        Processor->state.pc = 0;
        HKHubArchProcessorSetCycles(Processor, 3);
        HKHubArchProcessorRun(Processor);
        if (ResultsJSLE[Loop]) XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
        else XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    }
    
    HKHubArchProcessorDestroy(Processor);
    
    
    
    Source = "jsg A\nnop\nA: nop\n";
    
    AST = HKHubArchAssemblyParse(Source);
    
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Processor->state.flags = HKHubArchProcessorFlagsOverflow;
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 2);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    Processor->state.flags |= HKHubArchProcessorFlagsSign;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags = HKHubArchProcessorFlagsSign;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    Processor->state.flags = HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsZero;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    Processor->state.flags |= HKHubArchProcessorFlagsSign;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    Processor->state.flags = HKHubArchProcessorFlagsZero;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    Processor->state.flags |= HKHubArchProcessorFlagsSign;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    //ZF = 0 and SF = OF
    _Bool ResultsJSG[16] = {
        //0000  000z  00c0  00cz
        TRUE, FALSE, TRUE, FALSE,
        //0s00  0s0z  0sc0  0scz
        FALSE, FALSE, FALSE, FALSE,
        //o000  o00z  o0c0  o0cz
        FALSE, FALSE, FALSE, FALSE,
        //os00  os0z  osc0  oscz
        TRUE, FALSE, TRUE, FALSE
    };
    
    for (int Loop = 0; Loop < 16; Loop++)
    {
        Processor->state.flags = Loop;
        Processor->state.pc = 0;
        HKHubArchProcessorSetCycles(Processor, 3);
        HKHubArchProcessorRun(Processor);
        if (ResultsJSG[Loop]) XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
        else XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    }
    
    HKHubArchProcessorDestroy(Processor);
    
    
    
    Source = "jul A\nnop\nA: nop\n";
    
    AST = HKHubArchAssemblyParse(Source);
    
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Processor->state.flags = HKHubArchProcessorFlagsCarry;
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 2);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    //CF = 1
    _Bool ResultsJUL[16] = {
        //0000  000z  00c0  00cz
        FALSE, FALSE, TRUE, TRUE,
        //0s00  0s0z  0sc0  0scz
        FALSE, FALSE, TRUE, TRUE,
        //o000  o00z  o0c0  o0cz
        FALSE, FALSE, TRUE, TRUE,
        //os00  os0z  osc0  oscz
        FALSE, FALSE, TRUE, TRUE
    };
    
    for (int Loop = 0; Loop < 16; Loop++)
    {
        Processor->state.flags = Loop;
        Processor->state.pc = 0;
        HKHubArchProcessorSetCycles(Processor, 3);
        HKHubArchProcessorRun(Processor);
        if (ResultsJUL[Loop]) XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
        else XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    }
    
    HKHubArchProcessorDestroy(Processor);
    
    
    
    Source = "juge A\nnop\nA: nop\n";
    
    AST = HKHubArchAssemblyParse(Source);
    
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Processor->state.flags = 0;
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 2);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags = HKHubArchProcessorFlagsCarry;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    //CF = 0
    _Bool ResultsJUGE[16] = {
        //0000  000z  00c0  00cz
        TRUE, TRUE, FALSE, FALSE,
        //0s00  0s0z  0sc0  0scz
        TRUE, TRUE, FALSE, FALSE,
        //o000  o00z  o0c0  o0cz
        TRUE, TRUE, FALSE, FALSE,
        //os00  os0z  osc0  oscz
        TRUE, TRUE, FALSE, FALSE
    };
    
    for (int Loop = 0; Loop < 16; Loop++)
    {
        Processor->state.flags = Loop;
        Processor->state.pc = 0;
        HKHubArchProcessorSetCycles(Processor, 3);
        HKHubArchProcessorRun(Processor);
        if (ResultsJUGE[Loop]) XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
        else XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    }
    
    HKHubArchProcessorDestroy(Processor);
    
    
    
    Source = "jule A\nnop\nA: nop\n";
    
    AST = HKHubArchAssemblyParse(Source);
    
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Processor->state.flags = HKHubArchProcessorFlagsCarry;
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 2);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags |= HKHubArchProcessorFlagsZero;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags = HKHubArchProcessorFlagsZero;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    Processor->state.flags = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    //CF = 1 or ZF = 1
    _Bool ResultsJULE[16] = {
        //0000  000z  00c0  00cz
        FALSE, TRUE, TRUE, TRUE,
        //0s00  0s0z  0sc0  0scz
        FALSE, TRUE, TRUE, TRUE,
        //o000  o00z  o0c0  o0cz
        FALSE, TRUE, TRUE, TRUE,
        //os00  os0z  osc0  oscz
        FALSE, TRUE, TRUE, TRUE
    };
    
    for (int Loop = 0; Loop < 16; Loop++)
    {
        Processor->state.flags = Loop;
        Processor->state.pc = 0;
        HKHubArchProcessorSetCycles(Processor, 3);
        HKHubArchProcessorRun(Processor);
        if (ResultsJULE[Loop]) XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
        else XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    }
    
    HKHubArchProcessorDestroy(Processor);
    
    
    
    Source = "jug A\nnop\nA: nop\n";
    
    AST = HKHubArchAssemblyParse(Source);
    
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    Processor->state.flags = HKHubArchProcessorFlagsCarry;
    HKHubArchProcessorSetCycles(Processor, 1);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 2);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 0, @"Not enough cycles to process jump");
    
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    Processor->state.flags |= HKHubArchProcessorFlagsZero;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    Processor->state.flags = HKHubArchProcessorFlagsZero;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    
    Processor->state.flags = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 3);
    HKHubArchProcessorRun(Processor);
    XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
    
    //CF = 0 and ZF = 0
    _Bool ResultsJUG[16] = {
        //0000  000z  00c0  00cz
        TRUE, FALSE, FALSE, FALSE,
        //0s00  0s0z  0sc0  0scz
        TRUE, FALSE, FALSE, FALSE,
        //o000  o00z  o0c0  o0cz
        TRUE, FALSE, FALSE, FALSE,
        //os00  os0z  osc0  oscz
        TRUE, FALSE, FALSE, FALSE
    };
    
    for (int Loop = 0; Loop < 16; Loop++)
    {
        Processor->state.flags = Loop;
        Processor->state.pc = 0;
        HKHubArchProcessorSetCycles(Processor, 3);
        HKHubArchProcessorRun(Processor);
        if (ResultsJUG[Loop]) XCTAssertEqual(Processor->state.pc, 3, @"Processes jump");
        else XCTAssertEqual(Processor->state.pc, 2, @"Processes jump but doesn't take it");
    }
    
    HKHubArchProcessorDestroy(Processor);
}

@end
