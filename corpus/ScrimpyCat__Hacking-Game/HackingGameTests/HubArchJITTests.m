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
#import "HubArchProcessor.h"
#import "HubArchAssembly.h"
#import "HubArchInstruction.h"
#import "HubArchJIT.h"

#define HKHubArchAssemblyPrintError(err) if (Errors) { HKHubArchAssemblyPrintError(err); CCCollectionDestroy(err); err = NULL; }

void HKHubArchJITCall(HKHubArchJIT JIT, HKHubArchProcessor Processor);

@interface HubArchJITTests : XCTestCase

@end

@implementation HubArchJITTests

-(void) run: (const char*)source Halts: (_Bool)halts
{
    CCOrderedCollection AST = HKHubArchAssemblyParse(source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchExecutionGraph Graph = HKHubArchExecutionGraphCreate(CC_STD_ALLOCATOR, Binary->data, Binary->entrypoint);
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary), ProcessorNormal = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchJIT JIT = HKHubArchJITCreate(CC_STD_ALLOCATOR, Graph, 0);
    HKHubArchExecutionGraphDestroy(Graph);
    
    HKHubArchProcessorSetCycles(Processor, 1000);
    for (size_t PrevCycles = 0; PrevCycles != Processor->cycles; )
    {
        PrevCycles = Processor->cycles;
        HKHubArchJITCall(JIT, Processor);
    }
    
    HKHubArchJITDestroy(JIT);
    
    HKHubArchProcessorSetCycles(ProcessorNormal, 1000);
    HKHubArchProcessorRun(ProcessorNormal);
    
    XCTAssertEqual(Processor->state.r[0], ProcessorNormal->state.r[0], "Should have the correct value");
    XCTAssertEqual(Processor->state.r[1], ProcessorNormal->state.r[1], "Should have the correct value");
    XCTAssertEqual(Processor->state.r[2], ProcessorNormal->state.r[2], "Should have the correct value");
    XCTAssertEqual(Processor->state.r[3], ProcessorNormal->state.r[3], "Should have the correct value");
    XCTAssertEqual(Processor->state.pc, ProcessorNormal->state.pc, "Should have the correct value");
    XCTAssertEqual(Processor->state.flags, ProcessorNormal->state.flags, "Should have the correct value");
    XCTAssertEqual(Processor->cycles ? (Processor->cycles - halts) : 0, ProcessorNormal->cycles, "Should have the correct value");
    
    for (size_t Loop = 0; Loop < 256; Loop++) XCTAssertEqual(Processor->memory[Loop], ProcessorNormal->memory[Loop], "Should have the correct value");
    
    HKHubArchProcessorDestroy(Processor);
    HKHubArchProcessorDestroy(ProcessorNormal);
}

-(void) run: (const char*)source
{
    [self run: source Halts: TRUE];
}

-(void) testMove
{
    const char *Sources[] = {
        ".byte 4\n"
        ".entrypoint\n"
        "mov [0], 4\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 1\n"
        "mov [128+r0], 2\n"
        "mov [255+r0], 3\n"
        "hlt\n",
        
        "mov r1, 127\n"
        "mov [r1], 1\n"
        "mov r1, 128\n"
        "mov [r1], 2\n"
        "mov r1, 255\n"
        "mov [r1], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov r1, 127\n"
        "mov [r1+r0], 1\n"
        "mov r1, 128\n"
        "mov [r1+r0], 2\n"
        "mov r1, 255\n"
        "mov [r1+r0], 3\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r0, [127]\n"
        "mov r1, [128]\n"
        "mov r2, [255]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov [0], [127]\n"
        "mov [127], [128]\n"
        "mov [128], [255]\n"
        "mov [255], [0]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "mov [127+r3], 1\n"
        "mov [128+r3], 2\n"
        "mov [255+r3], 3\n"
        "mov r0, [127+r3]\n"
        "mov r1, [128+r3]\n"
        "mov r2, [255+r3]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "mov [127+r3], 1\n"
        "mov [128+r3], 2\n"
        "mov [255+r3], 3\n"
        "mov [0+r3], [127+r3]\n"
        "mov [127+r3], [128+r3]\n"
        "mov [128+r3], [255+r3]\n"
        "mov [255+r3], [0+r3]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "mov r0, [r3]\n"
        "mov r3, 128\n"
        "mov r1, [r3]\n"
        "mov r3, 255\n"
        "mov r2, [r3]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "mov [0], [r3]\n"
        "mov r3, 128\n"
        "mov [127], [r3]\n"
        "mov r3, 255\n"
        "mov [128], [r3]\n"
        "mov [r3], [0]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r0, 1\n"
        "mov r3, 127\n"
        "mov r0, [r3+r0]\n"
        "mov r3, 128\n"
        "mov r1, [r3+r0]\n"
        "mov r3, 255\n"
        "mov r2, [r3+r0]\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 1\n"
        "mov [128+r0], 2\n"
        "mov [255+r0], 3\n"
        "mov r3, 127\n"
        "mov [0+r0], [r3+r0]\n"
        "mov r3, 128\n"
        "mov [127+r0], [r3+r0]\n"
        "mov r3, 255\n"
        "mov [128+r0], [r3+r0]\n"
        "mov [r3+r0], [0+r0]\n"
        "hlt\n",
        
        "mov r0, 4\n"
        "mov r0, 5\n"
        "hlt\n",
        
        "mov r0, 0\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r2, 3\n"
        "mov r3, 4\n"
        "mov r0, r1\n"
        "mov r2, r3\n"
        "mov r0, r2\n"
        "hlt\n",
        
        ".byte 1,2,3,4\n"
        ".entrypoint\n"
        "mov r1, 1\n"
        "mov r0, [r1]\n"
        "mov r0, [r1+r0]\n"
        "mov r0, [r1+1]\n"
        "mov r0, [1]\n"
        "mov [r1], [r1]\n"
        "mov [r1], [r1-1]\n"
        "mov [r1], [r1+r1]\n"
        "mov [r1], [1]\n"
        "mov [r1], r1\n"
        "mov [r1], 1\n"
        "mov [r1+r1], [r1]\n"
        "mov [r1+r1], [r1-1]\n"
        "mov [r1+r1], [r1+r1]\n"
        "mov [r1+r1], [1]\n"
        "mov [r1+r1], r1\n"
        "mov [r1+r1], 1\n"
        "mov [r1-1], [r1]\n"
        "mov [r1-1], [r1-1]\n"
        "mov [r1-1], [r1+r1]\n"
        "mov [r1-1], [1]\n"
        "mov [r1-1], r1\n"
        "mov [r1-1], 1\n"
        "mov [1], [r1]\n"
        "mov [1], [r1-1]\n"
        "mov [1], [r1+r1]\n"
        "mov [1], [1]\n"
        "mov [1], r1\n"
        "mov [1], 1\n"
        "hlt\n",
        
        "mov r0, 127\n"
        "mov r0, 1\n"
        "hlt\n",
        
        "mov r0, -1\n"
        "mov r0, -2\n"
        "hlt\n",
        
        "mov r0, 128\n"
        "mov r0, 2\n"
        "hlt\n",
        
        "mov r0, 255\n"
        "mov r0, 1\n"
        "hlt\n",
        
        "mov flags, 255\n"
        "hlt\n",
        
        "mov pc, skip\n"
        "mov r0, 1\n"
        "skip: hlt\n"
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop]];
}

-(void) testAddition
{
    const char *Sources[] = {
        ".byte 4\n"
        ".entrypoint\n"
        "add [0], 4\n"
        "hlt\n",
        
        "add [127], 1\n"
        "add [128], 2\n"
        "add [255], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "add [127+r0], 1\n"
        "add [128+r0], 2\n"
        "add [255+r0], 3\n"
        "hlt\n",
        
        "mov r1, 127\n"
        "add [r1], 1\n"
        "mov r1, 128\n"
        "add [r1], 2\n"
        "mov r1, 255\n"
        "add [r1], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov r1, 127\n"
        "add [r1+r0], 1\n"
        "mov r1, 128\n"
        "add [r1+r0], 2\n"
        "mov r1, 255\n"
        "add [r1+r0], 3\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "add r0, [127]\n"
        "add r1, [128]\n"
        "add r2, [255]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "add [0], [127]\n"
        "add [127], [128]\n"
        "add [128], [255]\n"
        "add [255], [0]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "add [127+r3], 1\n"
        "add [128+r3], 2\n"
        "add [255+r3], 3\n"
        "add r0, [127+r3]\n"
        "add r1, [128+r3]\n"
        "add r2, [255+r3]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "add [127+r3], 1\n"
        "add [128+r3], 2\n"
        "add [255+r3], 3\n"
        "add [0+r3], [127+r3]\n"
        "add [127+r3], [128+r3]\n"
        "add [128+r3], [255+r3]\n"
        "add [255+r3], [0+r3]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "add r0, [r3]\n"
        "mov r3, 128\n"
        "add r1, [r3]\n"
        "mov r3, 255\n"
        "add r2, [r3]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "add [0], [r3]\n"
        "mov r3, 128\n"
        "add [127], [r3]\n"
        "mov r3, 255\n"
        "add [128], [r3]\n"
        "add [r3], [0]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r0, 1\n"
        "mov r3, 127\n"
        "add r0, [r3+r0]\n"
        "mov [0], r0\n"
        "mov r0, 1\n"
        "mov r3, 128\n"
        "add r1, [r3+r0]\n"
        "mov r3, 255\n"
        "add r2, [r3+r0]\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 1\n"
        "mov [128+r0], 2\n"
        "mov [255+r0], 3\n"
        "mov r3, 127\n"
        "add [0+r0], [r3+r0]\n"
        "mov r3, 128\n"
        "add [127+r0], [r3+r0]\n"
        "mov r3, 255\n"
        "add [128+r0], [r3+r0]\n"
        "add [r3+r0], [0+r0]\n"
        "hlt\n",
        
        "add r0, 4\n"
        "add r0, 5\n"
        "hlt\n",
        
        "add r0, 0\n"
        "hlt\n",
        
        "add r0, 1\n"
        "add r1, 2\n"
        "add r2, 3\n"
        "add r3, 4\n"
        "add r0, r1\n"
        "add r2, r3\n"
        "add r0, r2\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov r1, -3\n"
        "add r0, r1\n"
        "hlt\n",
        
        ".byte 1,2,3,4\n"
        ".entrypoint\n"
        "add r1, 1\n"
        "add r0, [r1]\n"
        "add r0, [r1+r0]\n"
        "add r0, [r1+1]\n"
        "add r0, [1]\n"
        "add [r1], [r1]\n"
        "add [r1], [r1-1]\n"
        "add [r1], [r1+r1]\n"
        "add [r1], [1]\n"
        "add [r1], r1\n"
        "add [r1], 1\n"
        "add [r1+r1], [r1]\n"
        "add [r1+r1], [r1-1]\n"
        "add [r1+r1], [r1+r1]\n"
        "add [r1+r1], [1]\n"
        "add [r1+r1], r1\n"
        "add [r1+r1], 1\n"
        "add [r1-1], [r1]\n"
        "add [r1-1], [r1-1]\n"
        "add [r1-1], [r1+r1]\n"
        "add [r1-1], [1]\n"
        "add [r1-1], r1\n"
        "add [r1-1], 1\n"
        "add [1], [r1]\n"
        "add [1], [r1-1]\n"
        "add [1], [r1+r1]\n"
        "add [1], [1]\n"
        "add [1], r1\n"
        "add [1], 1\n"
        "hlt\n",
        
        "add r0, 127\n"
        "add r0, 1\n"
        "hlt\n",
        
        "add r0, -1\n"
        "add r0, -2\n"
        "hlt\n",
        
        "add r0, 128\n"
        "add r0, 2\n"
        "hlt\n",
        
        "add r0, 255\n"
        "add r0, 1\n"
        "hlt\n",
        
        "add flags, 255\n"
        "hlt\n",
        
        "add pc, skip\n"
        "add r0, 1\n"
        "skip: hlt\n"
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop]];
}

-(void) testSubtraction
{
    const char *Sources[] = {
        ".byte 4\n"
        ".entrypoint\n"
        "sub [0], 4\n"
        "hlt\n",
        
        "sub [127], 1\n"
        "sub [128], 2\n"
        "sub [255], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "sub [127+r0], 1\n"
        "sub [128+r0], 2\n"
        "sub [255+r0], 3\n"
        "hlt\n",
        
        "mov r1, 127\n"
        "sub [r1], 1\n"
        "mov r1, 128\n"
        "sub [r1], 2\n"
        "mov r1, 255\n"
        "sub [r1], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov r1, 127\n"
        "sub [r1+r0], 1\n"
        "mov r1, 128\n"
        "sub [r1+r0], 2\n"
        "mov r1, 255\n"
        "sub [r1+r0], 3\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "sub r0, [127]\n"
        "sub r1, [128]\n"
        "sub r2, [255]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "sub [0], [127]\n"
        "sub [127], [128]\n"
        "sub [128], [255]\n"
        "sub [255], [0]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "sub [127+r3], 1\n"
        "sub [128+r3], 2\n"
        "sub [255+r3], 3\n"
        "sub r0, [127+r3]\n"
        "sub r1, [128+r3]\n"
        "sub r2, [255+r3]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "sub [127+r3], 1\n"
        "sub [128+r3], 2\n"
        "sub [255+r3], 3\n"
        "sub [0+r3], [127+r3]\n"
        "sub [127+r3], [128+r3]\n"
        "sub [128+r3], [255+r3]\n"
        "sub [255+r3], [0+r3]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "sub r0, [r3]\n"
        "mov r3, 128\n"
        "sub r1, [r3]\n"
        "mov r3, 255\n"
        "sub r2, [r3]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "sub [0], [r3]\n"
        "mov r3, 128\n"
        "sub [127], [r3]\n"
        "mov r3, 255\n"
        "sub [128], [r3]\n"
        "sub [r3], [0]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r0, 1\n"
        "mov r3, 127\n"
        "sub r0, [r3+r0]\n"
        "mov [0], r0\n"
        "mov r0, 1\n"
        "mov r3, 128\n"
        "sub r1, [r3+r0]\n"
        "mov r3, 255\n"
        "sub r2, [r3+r0]\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 1\n"
        "mov [128+r0], 2\n"
        "mov [255+r0], 3\n"
        "mov r3, 127\n"
        "sub [0+r0], [r3+r0]\n"
        "mov r3, 128\n"
        "sub [127+r0], [r3+r0]\n"
        "mov r3, 255\n"
        "sub [128+r0], [r3+r0]\n"
        "sub [r3+r0], [0+r0]\n"
        "hlt\n",
        
        "sub r0, 4\n"
        "sub r0, 5\n"
        "hlt\n",
        
        "sub r0, 0\n"
        "hlt\n",
        
        "sub r0, 1\n"
        "sub r1, 2\n"
        "sub r2, 3\n"
        "sub r3, 4\n"
        "sub r0, r1\n"
        "sub r2, r3\n"
        "sub r0, r2\n"
        "hlt\n",
        
        ".byte 1,2,3,4\n"
        ".entrypoint\n"
        "sub r1, 1\n"
        "sub r0, [r1]\n"
        "sub r0, [r1+r0]\n"
        "sub r0, [r1+1]\n"
        "sub r0, [1]\n"
        "sub [r1], [r1]\n"
        "sub [r1], [r1-1]\n"
        "sub [r1], [r1+r1]\n"
        "sub [r1], [1]\n"
        "sub [r1], r1\n"
        "sub [r1], 1\n"
        "sub [r1+r1], [r1]\n"
        "sub [r1+r1], [r1-1]\n"
        "sub [r1+r1], [r1+r1]\n"
        "sub [r1+r1], [1]\n"
        "sub [r1+r1], r1\n"
        "sub [r1+r1], 1\n"
        "sub [r1-1], [r1]\n"
        "sub [r1-1], [r1-1]\n"
        "sub [r1-1], [r1+r1]\n"
        "sub [r1-1], [1]\n"
        "sub [r1-1], r1\n"
        "sub [r1-1], 1\n"
        "sub [1], [r1]\n"
        "sub [1], [r1-1]\n"
        "sub [1], [r1+r1]\n"
        "sub [1], [1]\n"
        "sub [1], r1\n"
        "sub [1], 1\n"
        "hlt\n",
        
        "sub r0, 127\n"
        "sub r0, 1\n"
        "hlt\n",
        
        "sub r0, 127\n"
        "sub r0, -1\n"
        "hlt\n",
        
        "sub r0, 1\n"
        "sub r0, 255\n"
        "hlt\n",
        
        "sub r0, -1\n"
        "sub r0, -2\n"
        "hlt\n",
        
        "sub r0, 0\n"
        "sub r0, 1\n"
        "hlt\n",
        
        "sub r0, 128\n"
        "sub r0, -1\n"
        "hlt\n",
        
        "sub r0, 128\n"
        "sub r0, 1\n"
        "hlt\n",
        
        "sub r0, 255\n"
        "sub r0, 1\n"
        "hlt\n",
        
        "sub flags, 1\n"
        "hlt\n",
        
        "sub pc, -skip\n"
        "sub r0, 1\n"
        "skip: hlt\n"
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop]];
}

-(void) testOr
{
    const char *Sources[] = {
        ".byte 4\n"
        ".entrypoint\n"
        "or [0], 4\n"
        "hlt\n",
        
        "or [127], 1\n"
        "or [128], 2\n"
        "or [255], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "or [127+r0], 1\n"
        "or [128+r0], 2\n"
        "or [255+r0], 3\n"
        "hlt\n",
        
        "mov r1, 127\n"
        "or [r1], 1\n"
        "mov r1, 128\n"
        "or [r1], 2\n"
        "mov r1, 255\n"
        "or [r1], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov r1, 127\n"
        "or [r1+r0], 1\n"
        "mov r1, 128\n"
        "or [r1+r0], 2\n"
        "mov r1, 255\n"
        "or [r1+r0], 3\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "or r0, [127]\n"
        "or r1, [128]\n"
        "or r2, [255]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "or [0], [127]\n"
        "or [127], [128]\n"
        "or [128], [255]\n"
        "or [255], [0]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "or [127+r3], 1\n"
        "or [128+r3], 2\n"
        "or [255+r3], 3\n"
        "or r0, [127+r3]\n"
        "or r1, [128+r3]\n"
        "or r2, [255+r3]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "or [127+r3], 1\n"
        "or [128+r3], 2\n"
        "or [255+r3], 3\n"
        "or [0+r3], [127+r3]\n"
        "or [127+r3], [128+r3]\n"
        "or [128+r3], [255+r3]\n"
        "or [255+r3], [0+r3]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "or r0, [r3]\n"
        "mov r3, 128\n"
        "or r1, [r3]\n"
        "mov r3, 255\n"
        "or r2, [r3]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "or [0], [r3]\n"
        "mov r3, 128\n"
        "or [127], [r3]\n"
        "mov r3, 255\n"
        "or [128], [r3]\n"
        "or [r3], [0]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r0, 1\n"
        "mov r3, 127\n"
        "or r0, [r3+r0]\n"
        "mov [0], r0\n"
        "mov r0, 1\n"
        "mov r3, 128\n"
        "or r1, [r3+r0]\n"
        "mov r3, 255\n"
        "or r2, [r3+r0]\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 1\n"
        "mov [128+r0], 2\n"
        "mov [255+r0], 3\n"
        "mov r3, 127\n"
        "or [0+r0], [r3+r0]\n"
        "mov r3, 128\n"
        "or [127+r0], [r3+r0]\n"
        "mov r3, 255\n"
        "or [128+r0], [r3+r0]\n"
        "or [r3+r0], [0+r0]\n"
        "hlt\n",
        
        "or r0, 4\n"
        "or r0, 5\n"
        "hlt\n",
        
        "or r0, 0\n"
        "hlt\n",
        
        "or r0, 1\n"
        "or r1, 2\n"
        "or r2, 3\n"
        "or r3, 4\n"
        "or r0, r1\n"
        "or r2, r3\n"
        "or r0, r2\n"
        "hlt\n",
        
        ".byte 1,2,3,4\n"
        ".entrypoint\n"
        "or r1, 1\n"
        "or r0, [r1]\n"
        "or r0, [r1+r0]\n"
        "or r0, [r1+1]\n"
        "or r0, [1]\n"
        "or [r1], [r1]\n"
        "or [r1], [r1-1]\n"
        "or [r1], [r1+r1]\n"
        "or [r1], [1]\n"
        "or [r1], r1\n"
        "or [r1], 1\n"
        "or [r1+r1], [r1]\n"
        "or [r1+r1], [r1-1]\n"
        "or [r1+r1], [r1+r1]\n"
        "or [r1+r1], [1]\n"
        "or [r1+r1], r1\n"
        "or [r1+r1], 1\n"
        "or [r1-1], [r1]\n"
        "or [r1-1], [r1-1]\n"
        "or [r1-1], [r1+r1]\n"
        "or [r1-1], [1]\n"
        "or [r1-1], r1\n"
        "or [r1-1], 1\n"
        "or [1], [r1]\n"
        "or [1], [r1-1]\n"
        "or [1], [r1+r1]\n"
        "or [1], [1]\n"
        "or [1], r1\n"
        "or [1], 1\n"
        "hlt\n",
        
        "or r0, 127\n"
        "or r0, 1\n"
        "hlt\n",
        
        "or r0, -1\n"
        "or r0, -2\n"
        "hlt\n",
        
        "or r0, 128\n"
        "or r0, 2\n"
        "hlt\n",
        
        "or r0, 255\n"
        "or r0, 1\n"
        "hlt\n",
        
        "or flags, 255\n"
        "hlt\n",
        
        "or pc, skip\n"
        "or r0, 1\n"
        "skip: hlt\n"
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop]];
}

-(void) testXor
{
    const char *Sources[] = {
        ".byte 4\n"
        ".entrypoint\n"
        "xor [0], 4\n"
        "hlt\n",
        
        "xor [127], 1\n"
        "xor [128], 2\n"
        "xor [255], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "xor [127+r0], 1\n"
        "xor [128+r0], 2\n"
        "xor [255+r0], 3\n"
        "hlt\n",
        
        "mov r1, 127\n"
        "xor [r1], 1\n"
        "mov r1, 128\n"
        "xor [r1], 2\n"
        "mov r1, 255\n"
        "xor [r1], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov r1, 127\n"
        "xor [r1+r0], 1\n"
        "mov r1, 128\n"
        "xor [r1+r0], 2\n"
        "mov r1, 255\n"
        "xor [r1+r0], 3\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "xor r0, [127]\n"
        "xor r1, [128]\n"
        "xor r2, [255]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "xor [0], [127]\n"
        "xor [127], [128]\n"
        "xor [128], [255]\n"
        "xor [255], [0]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "xor [127+r3], 1\n"
        "xor [128+r3], 2\n"
        "xor [255+r3], 3\n"
        "xor r0, [127+r3]\n"
        "xor r1, [128+r3]\n"
        "xor r2, [255+r3]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "xor [127+r3], 1\n"
        "xor [128+r3], 2\n"
        "xor [255+r3], 3\n"
        "xor [0+r3], [127+r3]\n"
        "xor [127+r3], [128+r3]\n"
        "xor [128+r3], [255+r3]\n"
        "xor [255+r3], [0+r3]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "xor r0, [r3]\n"
        "mov r3, 128\n"
        "xor r1, [r3]\n"
        "mov r3, 255\n"
        "xor r2, [r3]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "xor [0], [r3]\n"
        "mov r3, 128\n"
        "xor [127], [r3]\n"
        "mov r3, 255\n"
        "xor [128], [r3]\n"
        "xor [r3], [0]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r0, 1\n"
        "mov r3, 127\n"
        "xor r0, [r3+r0]\n"
        "mov [0], r0\n"
        "mov r0, 1\n"
        "mov r3, 128\n"
        "xor r1, [r3+r0]\n"
        "mov r3, 255\n"
        "xor r2, [r3+r0]\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 1\n"
        "mov [128+r0], 2\n"
        "mov [255+r0], 3\n"
        "mov r3, 127\n"
        "xor [0+r0], [r3+r0]\n"
        "mov r3, 128\n"
        "xor [127+r0], [r3+r0]\n"
        "mov r3, 255\n"
        "xor [128+r0], [r3+r0]\n"
        "xor [r3+r0], [0+r0]\n"
        "hlt\n",
        
        "xor r0, 4\n"
        "xor r0, 5\n"
        "hlt\n",
        
        "xor r0, 0\n"
        "hlt\n",
        
        "xor r0, 1\n"
        "xor r1, 2\n"
        "xor r2, 3\n"
        "xor r3, 4\n"
        "xor r0, r1\n"
        "xor r2, r3\n"
        "xor r0, r2\n"
        "hlt\n",
        
        ".byte 1,2,3,4\n"
        ".entrypoint\n"
        "xor r1, 1\n"
        "xor r0, [r1]\n"
        "xor r0, [r1+r0]\n"
        "xor r0, [r1+1]\n"
        "xor r0, [1]\n"
        "xor [r1], [r1]\n"
        "xor [r1], [r1-1]\n"
        "xor [r1], [r1+r1]\n"
        "xor [r1], [1]\n"
        "xor [r1], r1\n"
        "xor [r1], 1\n"
        "xor [r1+r1], [r1]\n"
        "xor [r1+r1], [r1-1]\n"
        "xor [r1+r1], [r1+r1]\n"
        "xor [r1+r1], [1]\n"
        "xor [r1+r1], r1\n"
        "xor [r1+r1], 1\n"
        "xor [r1-1], [r1]\n"
        "xor [r1-1], [r1-1]\n"
        "xor [r1-1], [r1+r1]\n"
        "xor [r1-1], [1]\n"
        "xor [r1-1], r1\n"
        "xor [r1-1], 1\n"
        "xor [1], [r1]\n"
        "xor [1], [r1-1]\n"
        "xor [1], [r1+r1]\n"
        "xor [1], [1]\n"
        "xor [1], r1\n"
        "xor [1], 1\n"
        "hlt\n",
        
        "xor r0, 127\n"
        "xor r0, 1\n"
        "hlt\n",
        
        "xor r0, -1\n"
        "xor r0, -2\n"
        "hlt\n",
        
        "xor r0, 128\n"
        "xor r0, 2\n"
        "hlt\n",
        
        "xor r0, 255\n"
        "xor r0, 1\n"
        "hlt\n",
        
        "xor flags, 255\n"
        "hlt\n",
        
        "xor pc, skip\n"
        "xor r0, 1\n"
        "skip: hlt\n"
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop]];
}

-(void) testAnd
{
    const char *Sources[] = {
        ".byte 4\n"
        ".entrypoint\n"
        "and [0], 4\n"
        "hlt\n",
        
        "mov [127], 0xff\n"
        "mov [128], 0xff\n"
        "mov [255], 0xff\n"
        "and [127], 1\n"
        "and [128], 2\n"
        "and [255], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 0xff\n"
        "mov [128+r0], 0xff\n"
        "mov [255+r0], 0xff\n"
        "and [127+r0], 1\n"
        "and [128+r0], 2\n"
        "and [255+r0], 3\n"
        "hlt\n",
        
        "mov [127], 0xff\n"
        "mov [128], 0xff\n"
        "mov [255], 0xff\n"
        "mov r1, 127\n"
        "and [r1], 1\n"
        "mov r1, 128\n"
        "and [r1], 2\n"
        "mov r1, 255\n"
        "and [r1], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 0xff\n"
        "mov [128+r0], 0xff\n"
        "mov [255+r0], 0xff\n"
        "mov r1, 127\n"
        "and [r1+r0], 1\n"
        "mov r1, 128\n"
        "and [r1+r0], 2\n"
        "mov r1, 255\n"
        "and [r1+r0], 3\n"
        "hlt\n",
        
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "and r0, [127]\n"
        "and r1, [128]\n"
        "and r2, [255]\n"
        "hlt\n",
        
        "mov [127], 0xf0\n"
        "mov [128], 0x0f\n"
        "mov [255], 0xc3\n"
        "and [0], [127]\n"
        "and [127], [128]\n"
        "and [128], [255]\n"
        "and [255], [0]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "mov [127+r0], 0xff\n"
        "mov [128+r0], 0xff\n"
        "mov [255+r0], 0xff\n"
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "and [127+r3], 1\n"
        "and [128+r3], 2\n"
        "and [255+r3], 3\n"
        "and r0, [127+r3]\n"
        "and r1, [128+r3]\n"
        "and r2, [255+r3]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "mov [127+r3], 0xff\n"
        "mov [128+r3], 0xff\n"
        "mov [255+r3], 0xff\n"
        "and [127+r3], 1\n"
        "and [128+r3], 2\n"
        "and [255+r3], 3\n"
        "and [0+r3], [127+r3]\n"
        "and [127+r3], [128+r3]\n"
        "and [128+r3], [255+r3]\n"
        "and [255+r3], [0+r3]\n"
        "hlt\n",
        
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "and r0, [r3]\n"
        "mov r3, 128\n"
        "and r1, [r3]\n"
        "mov r3, 255\n"
        "and r2, [r3]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 3\n"
        "mov [255], 5\n"
        "mov r3, 127\n"
        "and [0], [r3]\n"
        "mov r3, 128\n"
        "and [127], [r3]\n"
        "mov r3, 255\n"
        "and [128], [r3]\n"
        "and [r3], [0]\n"
        "hlt\n",
        
        "mov r2, 0xff\n"
        "mov r3, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r0, 1\n"
        "mov r3, 127\n"
        "and r0, [r3+r0]\n"
        "mov [0], r0\n"
        "mov r0, 1\n"
        "mov r3, 128\n"
        "and r1, [r3+r0]\n"
        "mov r3, 255\n"
        "and r2, [r3+r0]\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 1\n"
        "mov [128+r0], 3\n"
        "mov [255+r0], 5\n"
        "mov r3, 127\n"
        "and [0+r0], [r3+r0]\n"
        "mov r3, 128\n"
        "and [127+r0], [r3+r0]\n"
        "mov r3, 255\n"
        "and [128+r0], [r3+r0]\n"
        "and [r3+r0], [0+r0]\n"
        "hlt\n",
        
        "and r0, 4\n"
        "and r0, 5\n"
        "hlt\n",
        
        "and r0, 0\n"
        "hlt\n",
        
        "and r0, 1\n"
        "and r1, 2\n"
        "and r2, 3\n"
        "and r3, 4\n"
        "and r0, r1\n"
        "and r2, r3\n"
        "and r0, r2\n"
        "hlt\n",
        
        ".byte 1,2,3,4\n"
        ".entrypoint\n"
        "and r1, 1\n"
        "and r0, [r1]\n"
        "and r0, [r1+r0]\n"
        "and r0, [r1+1]\n"
        "and r0, [1]\n"
        "and [r1], [r1]\n"
        "and [r1], [r1-1]\n"
        "and [r1], [r1+r1]\n"
        "and [r1], [1]\n"
        "and [r1], r1\n"
        "and [r1], 1\n"
        "and [r1+r1], [r1]\n"
        "and [r1+r1], [r1-1]\n"
        "and [r1+r1], [r1+r1]\n"
        "and [r1+r1], [1]\n"
        "and [r1+r1], r1\n"
        "and [r1+r1], 1\n"
        "and [r1-1], [r1]\n"
        "and [r1-1], [r1-1]\n"
        "and [r1-1], [r1+r1]\n"
        "and [r1-1], [1]\n"
        "and [r1-1], r1\n"
        "and [r1-1], 1\n"
        "and [1], [r1]\n"
        "and [1], [r1-1]\n"
        "and [1], [r1+r1]\n"
        "and [1], [1]\n"
        "and [1], r1\n"
        "and [1], 1\n"
        "hlt\n",
        
        "and r0, 127\n"
        "and r0, 1\n"
        "hlt\n",
        
        "and r0, -1\n"
        "and r0, -2\n"
        "hlt\n",
        
        "and r0, 128\n"
        "and r0, 2\n"
        "hlt\n",
        
        "and r0, 255\n"
        "and r0, 1\n"
        "hlt\n",
        
        "and flags, 255\n"
        "hlt\n",
        
        "and pc, skip\n"
        "and r0, 1\n"
        "skip: hlt\n"
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop]];
}

-(void) testCompare
{
    const char *Sources[] = {
        ".byte 4\n"
        ".entrypoint\n"
        "cmp [0], 4\n"
        "hlt\n",
        
        "cmp [127], 1\n"
        "add [50], flags\n"
        "cmp [128], 2\n"
        "add [50], flags\n"
        "cmp [255], 3\n"
        "add [50], flags\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "cmp [127+r0], 1\n"
        "add [50], flags\n"
        "cmp [128+r0], 2\n"
        "add [50], flags\n"
        "cmp [255+r0], 3\n"
        "add [50], flags\n"
        "hlt\n",
        
        "mov r1, 127\n"
        "cmp [r1], 1\n"
        "add [50], flags\n"
        "mov r1, 128\n"
        "cmp [r1], 2\n"
        "add [50], flags\n"
        "mov r1, 255\n"
        "cmp [r1], 3\n"
        "add [50], flags\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov r1, 127\n"
        "cmp [r1+r0], 1\n"
        "add [50], flags\n"
        "mov r1, 128\n"
        "cmp [r1+r0], 2\n"
        "add [50], flags\n"
        "mov r1, 255\n"
        "cmp [r1+r0], 3\n"
        "add [50], flags\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "cmp r0, [127]\n"
        "add [50], flags\n"
        "cmp r1, [128]\n"
        "add [50], flags\n"
        "cmp r2, [255]\n"
        "add [50], flags\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "cmp [0], [127]\n"
        "add [50], flags\n"
        "cmp [127], [128]\n"
        "add [50], flags\n"
        "cmp [128], [255]\n"
        "add [50], flags\n"
        "cmp [255], [0]\n"
        "add [50], flags\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "mov [127+r3], 1\n"
        "mov [128+r3], 2\n"
        "mov [255+r3], 3\n"
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r2, 3\n"
        "cmp r0, [127+r3]\n"
        "add [50], flags\n"
        "cmp r1, [128+r3]\n"
        "add [50], flags\n"
        "cmp r2, [255+r3]\n"
        "add [50], flags\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "mov [127+r3], 1\n"
        "mov [128+r3], 2\n"
        "mov [255+r3], 3\n"
        "cmp [0+r3], [127+r3]\n"
        "add [50], flags\n"
        "cmp [127+r3], [128+r3]\n"
        "add [50], flags\n"
        "cmp [128+r3], [255+r3]\n"
        "add [50], flags\n"
        "cmp [255+r3], [0+r3]\n"
        "add [50], flags\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "cmp r0, [r3]\n"
        "add [50], flags\n"
        "mov r3, 128\n"
        "cmp r1, [r3]\n"
        "add [50], flags\n"
        "mov r3, 255\n"
        "cmp r2, [r3]\n"
        "add [50], flags\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "cmp [0], [r3]\n"
        "add [50], flags\n"
        "mov r3, 128\n"
        "cmp [127], [r3]\n"
        "add [50], flags\n"
        "mov r3, 255\n"
        "cmp [128], [r3]\n"
        "add [50], flags\n"
        "cmp [r3], [0]\n"
        "add [50], flags\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r0, 1\n"
        "mov r3, 127\n"
        "cmp r0, [r3+r0]\n"
        "add [50], flags\n"
        "mov [0], r0\n"
        "mov r0, 1\n"
        "mov r3, 128\n"
        "mov r1, 2\n"
        "cmp r1, [r3+r0]\n"
        "add [50], flags\n"
        "mov r3, 255\n"
        "mov r2, 3\n"
        "cmp r2, [r3+r0]\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 1\n"
        "mov [128+r0], 2\n"
        "mov [255+r0], 3\n"
        "mov r3, 127\n"
        "cmp [0+r0], [r3+r0]\n"
        "add [150], flags\n"
        "mov r3, 128\n"
        "cmp [127+r0], [r3+r0]\n"
        "add [150], flags\n"
        "mov r3, 255\n"
        "cmp [128+r0], [r3+r0]\n"
        "add [150], flags\n"
        "cmp [r3+r0], [0+r0]\n"
        "add [150], flags\n"
        "hlt\n",
        
        "cmp r0, 4\n"
        "cmp r0, 5\n"
        "hlt\n",
        
        "cmp r0, 0\n"
        "hlt\n",
        
        "cmp r0, 1\n"
        "cmp r1, 2\n"
        "cmp r2, 3\n"
        "cmp r3, 4\n"
        "cmp r0, r1\n"
        "cmp r2, r3\n"
        "cmp r0, r2\n"
        "hlt\n",
        
        ".byte 1,2,3,4\n"
        ".entrypoint\n"
        "cmp r1, 1\n"
        "cmp r0, [r1]\n"
        "cmp r0, [r1+r0]\n"
        "cmp r0, [r1+1]\n"
        "cmp r0, [1]\n"
        "cmp [r1], [r1]\n"
        "cmp [r1], [r1-1]\n"
        "cmp [r1], [r1+r1]\n"
        "cmp [r1], [1]\n"
        "cmp [r1], r1\n"
        "cmp [r1], 1\n"
        "cmp [r1+r1], [r1]\n"
        "cmp [r1+r1], [r1-1]\n"
        "cmp [r1+r1], [r1+r1]\n"
        "cmp [r1+r1], [1]\n"
        "cmp [r1+r1], r1\n"
        "cmp [r1+r1], 1\n"
        "cmp [r1-1], [r1]\n"
        "cmp [r1-1], [r1-1]\n"
        "cmp [r1-1], [r1+r1]\n"
        "cmp [r1-1], [1]\n"
        "cmp [r1-1], r1\n"
        "cmp [r1-1], 1\n"
        "cmp [1], [r1]\n"
        "cmp [1], [r1-1]\n"
        "cmp [1], [r1+r1]\n"
        "cmp [1], [1]\n"
        "cmp [1], r1\n"
        "cmp [1], 1\n"
        "hlt\n",
        
        "cmp r0, 127\n"
        "cmp r0, 1\n"
        "hlt\n",
        
        "cmp r0, -1\n"
        "cmp r0, -2\n"
        "hlt\n",
        
        "cmp r0, 128\n"
        "cmp r0, 2\n"
        "hlt\n",
        
        "cmp r0, 255\n"
        "cmp r0, 1\n"
        "hlt\n",
        
        "cmp flags, 255\n"
        "hlt\n",
        
        "cmp pc, skip\n"
        "cmp r0, 1\n"
        "skip: hlt\n"
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop]];
}

-(void) testLeftShift
{
    const char *Sources[] = {
        "mov r0, 5\n"
        "shl r0, 1\n"
        "hlt\n",
        
        "mov r0, 5\n"
        "shl r0, 2\n"
        "hlt\n",
        
        "mov r0, 64\n"
        "shl r0, 1\n"
        "hlt\n",
        
        "mov r0, 128\n"
        "shl r0, 1\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "shl r0, 128\n"
        "hlt\n",
        
        "mov r0, 0\n"
        "shl r0, 3\n"
        "hlt\n",
        
        "mov r0, 0\n"
        "shl r0, 128\n"
        "hlt\n",
        
        "mov r0, 5\n"
        "shl r0, 0\n"
        "hlt\n",
        
        "mov r0, 0\n"
        "shl r0, 0\n"
        "hlt\n",
        
        "mov r0, 128\n"
        "shl r0, 0\n"
        "hlt\n",
        
        "mov r0, 5\n"
        "mov r1, 1\n"
        "shl r0, r1\n"
        "hlt\n",
        
        "mov r0, 5\n"
        "mov r1, 2\n"
        "shl r0, r1\n"
        "hlt\n",
        
        "mov r0, 64\n"
        "mov r1, 1\n"
        "shl r0, r1\n"
        "hlt\n",
        
        "mov r0, 128\n"
        "mov r1, 1\n"
        "shl r0, r1\n"
        "hlt\n",
        
        "mov r0, 128\n"
        "mov r1, 1\n"
        "shl r0, r1\n"
        "hlt\n",
        
        "mov r0, 0\n"
        "mov r1, 3\n"
        "shl r0, r1\n"
        "hlt\n",
        
        "mov r0, 0\n"
        "mov r1, 128\n"
        "shl r0, r1\n"
        "hlt\n",
        
        "mov r0, 5\n"
        "mov r1, 0\n"
        "shl r0, r1\n"
        "hlt\n",
        
        "mov r0, 0\n"
        "mov r1, 0\n"
        "shl r0, r1\n"
        "hlt\n",
        
        "mov r0, 128\n"
        "mov r1, 0\n"
        "shl r0, r1\n"
        "hlt\n",
        
        "mov r0, 5\n"
        "shl r0, r0\n"
        "hlt\n",
        
        "mov r0, 5\n"
        "mov r2, 2\n"
        "shl r0, r2\n"
        "hlt\n",
        
        "mov r0, 5\n"
        "mov r3, 2\n"
        "shl r0, r3\n"
        "hlt\n",
        
        "mov r1, 5\n"
        "mov r0, 2\n"
        "shl r1, r0\n"
        "hlt\n",
        
        "mov r1, 5\n"
        "shl r1, r1\n"
        "hlt\n",
        
        "mov r1, 5\n"
        "mov r2, 2\n"
        "shl r1, r2\n"
        "hlt\n",
        
        "mov r1, 5\n"
        "mov r3, 2\n"
        "shl r1, r3\n"
        "hlt\n",
        
        "mov r2, 5\n"
        "mov r0, 2\n"
        "shl r2, r0\n"
        "hlt\n",
        
        "mov r2, 5\n"
        "mov r1, 2\n"
        "shl r2, r1\n"
        "hlt\n",
        
        "mov r2, 5\n"
        "shl r2, r2\n"
        "hlt\n",
        
        "mov r2, 5\n"
        "mov r3, 2\n"
        "shl r2, r3\n"
        "hlt\n",
        
        "mov r3, 5\n"
        "mov r0, 2\n"
        "shl r3, r0\n"
        "hlt\n",
        
        "mov r3, 5\n"
        "mov r1, 2\n"
        "shl r3, r1\n"
        "hlt\n",
        
        "mov r3, 5\n"
        "mov r2, 2\n"
        "shl r3, r2\n"
        "hlt\n",
        
        "mov r3, 5\n"
        "shl r3, r3\n"
        "hlt\n",
        
        ".byte 1\n"
        ".entrypoint\n"
        "mov r0, 5\n"
        "shl r0, [0]\n"
        "hlt\n",
        
        ".byte 2\n"
        ".entrypoint\n"
        "mov r0, 5\n"
        "shl r0, [0]\n"
        "hlt\n",
        
        ".byte 1\n"
        ".entrypoint\n"
        "mov r0, 64\n"
        "shl r0, [0]\n"
        "hlt\n",
        
        ".byte 1\n"
        ".entrypoint\n"
        "mov r0, 128\n"
        "shl r0, [0]\n"
        "hlt\n",
        
        ".byte 1\n"
        ".entrypoint\n"
        "mov r0, 5\n"
        "shl r0, [r1]\n"
        "hlt\n",
        
        ".byte 2\n"
        ".entrypoint\n"
        "mov r0, 5\n"
        "shl r0, [r1]\n"
        "hlt\n",
        
        ".byte 1\n"
        ".entrypoint\n"
        "mov r0, 64\n"
        "shl r0, [r1]\n"
        "hlt\n",
        
        ".byte 1\n"
        ".entrypoint\n"
        "mov r0, 128\n"
        "shl r0, [r1]\n"
        "hlt\n",
        
        ".byte 0, 1\n"
        ".entrypoint\n"
        "mov r0, 5\n"
        "shl r0, [r1+1]\n"
        "hlt\n",
        
        ".byte 0, 2\n"
        ".entrypoint\n"
        "mov r0, 5\n"
        "shl r0, [r1+1]\n"
        "hlt\n",
        
        ".byte 0, 1\n"
        ".entrypoint\n"
        "mov r0, 64\n"
        "shl r0, [r1+1]\n"
        "hlt\n",
        
        ".byte 0, 1\n"
        ".entrypoint\n"
        "mov r0, 128\n"
        "shl r0, [r1+1]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r0, 5\n"
        "mov r1, 1\n"
        "shl r0, [r1+r1]\n"
        "hlt\n",
        
        ".byte 0, 0, 2\n"
        ".entrypoint\n"
        "mov r0, 5\n"
        "mov r1, 1\n"
        "shl r0, [r1+r1]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r0, 64\n"
        "mov r1, 1\n"
        "shl r0, [r1+r1]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r0, 128\n"
        "mov r1, 1\n"
        "shl r0, [r1+r1]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r1, 128\n"
        "mov r0, 1\n"
        "shl r1, [r0+r0]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r2, 128\n"
        "mov r1, 1\n"
        "shl r2, [r1+r1]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r3, 128\n"
        "mov r1, 1\n"
        "shl r3, [r1+r1]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r0, 1\n"
        "shl r0, [r0+r0]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r1, 1\n"
        "shl r1, [r1+r1]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r2, 1\n"
        "shl r2, [r2+r2]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r3, 1\n"
        "shl r3, [r3+r3]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r3, 1\n"
        "shl r3, [r3+0]\n"
        "hlt\n",
        
//        "mov [127], 0xff\n"
//        "mov [128], 0xff\n"
//        "mov [255], 0xff\n"
//        "shl [127], 1\n"
//        "shl [128], 2\n"
//        "shl [255], 3\n"
//        "hlt\n",
        
//        "mov r0, 1\n"
//        "mov [127+r0], 0xff\n"
//        "mov [128+r0], 0xff\n"
//        "mov [255+r0], 0xff\n"
//        "shl [127+r0], 1\n"
//        "shl [128+r0], 2\n"
//        "shl [255+r0], 3\n"
//        "hlt\n",
        
//        "mov [127], 0xff\n"
//        "mov [128], 0xff\n"
//        "mov [255], 0xff\n"
//        "mov r1, 127\n"
//        "shl [r1], 1\n"
//        "mov r1, 128\n"
//        "shl [r1], 2\n"
//        "mov r1, 255\n"
//        "shl [r1], 3\n"
//        "hlt\n",
        
//        "mov r0, 1\n"
//        "mov [127+r0], 0xff\n"
//        "mov [128+r0], 0xff\n"
//        "mov [255+r0], 0xff\n"
//        "mov r1, 127\n"
//        "shl [r1+r0], 1\n"
//        "mov r1, 128\n"
//        "shl [r1+r0], 2\n"
//        "mov r1, 255\n"
//        "shl [r1+r0], 3\n"
//        "hlt\n",
        
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "shl r0, [127]\n"
        "shl r1, [128]\n"
        "shl r2, [255]\n"
        "hlt\n",
        
//        "mov [127], 0xf0\n"
//        "mov [128], 0x0f\n"
//        "mov [255], 0xc3\n"
//        "shl [0], [127]\n"
//        "shl [127], [128]\n"
//        "shl [128], [255]\n"
//        "shl [255], [0]\n"
//        "hlt\n",
        
//        "mov r3, 1\n"
//        "mov [127+r0], 0xff\n"
//        "mov [128+r0], 0xff\n"
//        "mov [255+r0], 0xff\n"
//        "mov r0, 0xff\n"
//        "mov r1, 0xff\n"
//        "mov r2, 0xff\n"
//        "shl [127+r3], 1\n"
//        "shl [128+r3], 2\n"
//        "shl [255+r3], 3\n"
//        "shl r0, [127+r3]\n"
//        "shl r1, [128+r3]\n"
//        "shl r2, [255+r3]\n"
//        "hlt\n",
        
//        "mov r3, 1\n"
//        "mov [127+r3], 0xff\n"
//        "mov [128+r3], 0xff\n"
//        "mov [255+r3], 0xff\n"
//        "shl [127+r3], 1\n"
//        "shl [128+r3], 2\n"
//        "shl [255+r3], 3\n"
//        "shl [0+r3], [127+r3]\n"
//        "shl [127+r3], [128+r3]\n"
//        "shl [128+r3], [255+r3]\n"
//        "shl [255+r3], [0+r3]\n"
//        "hlt\n",
        
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "shl r0, [r3]\n"
        "mov r3, 128\n"
        "shl r1, [r3]\n"
        "mov r3, 255\n"
        "shl r2, [r3]\n"
        "hlt\n",
        
//        "mov [127], 1\n"
//        "mov [128], 3\n"
//        "mov [255], 5\n"
//        "mov r3, 127\n"
//        "shl [0], [r3]\n"
//        "mov r3, 128\n"
//        "shl [127], [r3]\n"
//        "mov r3, 255\n"
//        "shl [128], [r3]\n"
//        "shl [r3], [0]\n"
//        "hlt\n",
        
        "mov r2, 0xff\n"
        "mov r3, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r0, 1\n"
        "mov r3, 127\n"
        "shl r0, [r3+r0]\n"
        "mov [0], r0\n"
        "mov r0, 1\n"
        "mov r3, 128\n"
        "shl r1, [r3+r0]\n"
        "mov r3, 255\n"
        "shl r2, [r3+r0]\n"
        "hlt\n",
        
//        "mov r0, 1\n"
//        "mov [127+r0], 1\n"
//        "mov [128+r0], 3\n"
//        "mov [255+r0], 5\n"
//        "mov r3, 127\n"
//        "shl [0+r0], [r3+r0]\n"
//        "mov r3, 128\n"
//        "shl [127+r0], [r3+r0]\n"
//        "mov r3, 255\n"
//        "shl [128+r0], [r3+r0]\n"
//        "shl [r3+r0], [0+r0]\n"
//        "hlt\n",
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop]];
}

-(void) testRightShift
{
    const char *Sources[] = {
        "mov r0, 5\n"
        "shr r0, 1\n"
        "hlt\n",
        
        "mov r0, 5\n"
        "shr r0, 2\n"
        "hlt\n",
        
        "mov r0, 64\n"
        "shr r0, 1\n"
        "hlt\n",
        
        "mov r0, 128\n"
        "shr r0, 1\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "shr r0, 128\n"
        "hlt\n",
        
        "mov r0, 0\n"
        "shr r0, 3\n"
        "hlt\n",
        
        "mov r0, 0\n"
        "shr r0, 128\n"
        "hlt\n",
        
        "mov r0, 5\n"
        "shr r0, 0\n"
        "hlt\n",
        
        "mov r0, 0\n"
        "shr r0, 0\n"
        "hlt\n",
        
        "mov r0, 128\n"
        "shr r0, 0\n"
        "hlt\n",
        
        "mov r0, 5\n"
        "mov r1, 1\n"
        "shr r0, r1\n"
        "hlt\n",
        
        "mov r0, 5\n"
        "mov r1, 2\n"
        "shr r0, r1\n"
        "hlt\n",
        
        "mov r0, 64\n"
        "mov r1, 1\n"
        "shr r0, r1\n"
        "hlt\n",
        
        "mov r0, 128\n"
        "mov r1, 1\n"
        "shr r0, r1\n"
        "hlt\n",
        
        "mov r0, 128\n"
        "mov r1, 1\n"
        "shr r0, r1\n"
        "hlt\n",
        
        "mov r0, 0\n"
        "mov r1, 3\n"
        "shr r0, r1\n"
        "hlt\n",
        
        "mov r0, 0\n"
        "mov r1, 128\n"
        "shr r0, r1\n"
        "hlt\n",
        
        "mov r0, 5\n"
        "mov r1, 0\n"
        "shr r0, r1\n"
        "hlt\n",
        
        "mov r0, 0\n"
        "mov r1, 0\n"
        "shr r0, r1\n"
        "hlt\n",
        
        "mov r0, 128\n"
        "mov r1, 0\n"
        "shr r0, r1\n"
        "hlt\n",
        
        "mov r0, 5\n"
        "shr r0, r0\n"
        "hlt\n",
        
        "mov r0, 5\n"
        "mov r2, 2\n"
        "shr r0, r2\n"
        "hlt\n",
        
        "mov r0, 5\n"
        "mov r3, 2\n"
        "shr r0, r3\n"
        "hlt\n",
        
        "mov r1, 5\n"
        "mov r0, 2\n"
        "shr r1, r0\n"
        "hlt\n",
        
        "mov r1, 5\n"
        "shr r1, r1\n"
        "hlt\n",
        
        "mov r1, 5\n"
        "mov r2, 2\n"
        "shr r1, r2\n"
        "hlt\n",
        
        "mov r1, 5\n"
        "mov r3, 2\n"
        "shr r1, r3\n"
        "hlt\n",
        
        "mov r2, 5\n"
        "mov r0, 2\n"
        "shr r2, r0\n"
        "hlt\n",
        
        "mov r2, 5\n"
        "mov r1, 2\n"
        "shr r2, r1\n"
        "hlt\n",
        
        "mov r2, 5\n"
        "shr r2, r2\n"
        "hlt\n",
        
        "mov r2, 5\n"
        "mov r3, 2\n"
        "shr r2, r3\n"
        "hlt\n",
        
        "mov r3, 5\n"
        "mov r0, 2\n"
        "shr r3, r0\n"
        "hlt\n",
        
        "mov r3, 5\n"
        "mov r1, 2\n"
        "shr r3, r1\n"
        "hlt\n",
        
        "mov r3, 5\n"
        "mov r2, 2\n"
        "shr r3, r2\n"
        "hlt\n",
        
        "mov r3, 5\n"
        "shr r3, r3\n"
        "hlt\n",
        
        ".byte 1\n"
        ".entrypoint\n"
        "mov r0, 5\n"
        "shr r0, [0]\n"
        "hlt\n",
        
        ".byte 2\n"
        ".entrypoint\n"
        "mov r0, 5\n"
        "shr r0, [0]\n"
        "hlt\n",
        
        ".byte 1\n"
        ".entrypoint\n"
        "mov r0, 64\n"
        "shr r0, [0]\n"
        "hlt\n",
        
        ".byte 1\n"
        ".entrypoint\n"
        "mov r0, 128\n"
        "shr r0, [0]\n"
        "hlt\n",
        
        ".byte 1\n"
        ".entrypoint\n"
        "mov r0, 5\n"
        "shr r0, [r1]\n"
        "hlt\n",
        
        ".byte 2\n"
        ".entrypoint\n"
        "mov r0, 5\n"
        "shr r0, [r1]\n"
        "hlt\n",
        
        ".byte 1\n"
        ".entrypoint\n"
        "mov r0, 64\n"
        "shr r0, [r1]\n"
        "hlt\n",
        
        ".byte 1\n"
        ".entrypoint\n"
        "mov r0, 128\n"
        "shr r0, [r1]\n"
        "hlt\n",
        
        ".byte 0, 1\n"
        ".entrypoint\n"
        "mov r0, 5\n"
        "shr r0, [r1+1]\n"
        "hlt\n",
        
        ".byte 0, 2\n"
        ".entrypoint\n"
        "mov r0, 5\n"
        "shr r0, [r1+1]\n"
        "hlt\n",
        
        ".byte 0, 1\n"
        ".entrypoint\n"
        "mov r0, 64\n"
        "shr r0, [r1+1]\n"
        "hlt\n",
        
        ".byte 0, 1\n"
        ".entrypoint\n"
        "mov r0, 128\n"
        "shr r0, [r1+1]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r0, 5\n"
        "mov r1, 1\n"
        "shr r0, [r1+r1]\n"
        "hlt\n",
        
        ".byte 0, 0, 2\n"
        ".entrypoint\n"
        "mov r0, 5\n"
        "mov r1, 1\n"
        "shr r0, [r1+r1]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r0, 64\n"
        "mov r1, 1\n"
        "shr r0, [r1+r1]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r0, 128\n"
        "mov r1, 1\n"
        "shr r0, [r1+r1]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r1, 128\n"
        "mov r0, 1\n"
        "shr r1, [r0+r0]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r2, 128\n"
        "mov r1, 1\n"
        "shr r2, [r1+r1]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r3, 128\n"
        "mov r1, 1\n"
        "shr r3, [r1+r1]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r0, 1\n"
        "shr r0, [r0+r0]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r1, 1\n"
        "shr r1, [r1+r1]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r2, 1\n"
        "shr r2, [r2+r2]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r3, 1\n"
        "shr r3, [r3+r3]\n"
        "hlt\n",
        
        ".byte 0, 0, 1\n"
        ".entrypoint\n"
        "mov r3, 1\n"
        "shr r3, [r3+0]\n"
        "hlt\n",
        
//        "mov [127], 0xff\n"
//        "mov [128], 0xff\n"
//        "mov [255], 0xff\n"
//        "shr [127], 1\n"
//        "shr [128], 2\n"
//        "shr [255], 3\n"
//        "hlt\n",
        
//        "mov r0, 1\n"
//        "mov [127+r0], 0xff\n"
//        "mov [128+r0], 0xff\n"
//        "mov [255+r0], 0xff\n"
//        "shr [127+r0], 1\n"
//        "shr [128+r0], 2\n"
//        "shr [255+r0], 3\n"
//        "hlt\n",
        
//        "mov [127], 0xff\n"
//        "mov [128], 0xff\n"
//        "mov [255], 0xff\n"
//        "mov r1, 127\n"
//        "shr [r1], 1\n"
//        "mov r1, 128\n"
//        "shr [r1], 2\n"
//        "mov r1, 255\n"
//        "shr [r1], 3\n"
//        "hlt\n",
        
//        "mov r0, 1\n"
//        "mov [127+r0], 0xff\n"
//        "mov [128+r0], 0xff\n"
//        "mov [255+r0], 0xff\n"
//        "mov r1, 127\n"
//        "shr [r1+r0], 1\n"
//        "mov r1, 128\n"
//        "shr [r1+r0], 2\n"
//        "mov r1, 255\n"
//        "shr [r1+r0], 3\n"
//        "hlt\n",
        
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "shr r0, [127]\n"
        "shr r1, [128]\n"
        "shr r2, [255]\n"
        "hlt\n",
        
//        "mov [127], 0xf0\n"
//        "mov [128], 0x0f\n"
//        "mov [255], 0xc3\n"
//        "shr [0], [127]\n"
//        "shr [127], [128]\n"
//        "shr [128], [255]\n"
//        "shr [255], [0]\n"
//        "hlt\n",
        
//        "mov r3, 1\n"
//        "mov [127+r0], 0xff\n"
//        "mov [128+r0], 0xff\n"
//        "mov [255+r0], 0xff\n"
//        "mov r0, 0xff\n"
//        "mov r1, 0xff\n"
//        "mov r2, 0xff\n"
//        "shr [127+r3], 1\n"
//        "shr [128+r3], 2\n"
//        "shr [255+r3], 3\n"
//        "shr r0, [127+r3]\n"
//        "shr r1, [128+r3]\n"
//        "shr r2, [255+r3]\n"
//        "hlt\n",
        
//        "mov r3, 1\n"
//        "mov [127+r3], 0xff\n"
//        "mov [128+r3], 0xff\n"
//        "mov [255+r3], 0xff\n"
//        "shr [127+r3], 1\n"
//        "shr [128+r3], 2\n"
//        "shr [255+r3], 3\n"
//        "shr [0+r3], [127+r3]\n"
//        "shr [127+r3], [128+r3]\n"
//        "shr [128+r3], [255+r3]\n"
//        "shr [255+r3], [0+r3]\n"
//        "hlt\n",
        
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "shr r0, [r3]\n"
        "mov r3, 128\n"
        "shr r1, [r3]\n"
        "mov r3, 255\n"
        "shr r2, [r3]\n"
        "hlt\n",
        
//        "mov [127], 1\n"
//        "mov [128], 3\n"
//        "mov [255], 5\n"
//        "mov r3, 127\n"
//        "shr [0], [r3]\n"
//        "mov r3, 128\n"
//        "shr [127], [r3]\n"
//        "mov r3, 255\n"
//        "shr [128], [r3]\n"
//        "shr [r3], [0]\n"
//        "hlt\n",
        
        "mov r2, 0xff\n"
        "mov r3, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r0, 1\n"
        "mov r3, 127\n"
        "shr r0, [r3+r0]\n"
        "mov [0], r0\n"
        "mov r0, 1\n"
        "mov r3, 128\n"
        "shr r1, [r3+r0]\n"
        "mov r3, 255\n"
        "shr r2, [r3+r0]\n"
        "hlt\n",
        
//        "mov r0, 1\n"
//        "mov [127+r0], 1\n"
//        "mov [128+r0], 3\n"
//        "mov [255+r0], 5\n"
//        "mov r3, 127\n"
//        "shr [0+r0], [r3+r0]\n"
//        "mov r3, 128\n"
//        "shr [127+r0], [r3+r0]\n"
//        "mov r3, 255\n"
//        "shr [128+r0], [r3+r0]\n"
//        "shr [r3+r0], [0+r0]\n"
//        "hlt\n",
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop]];
}

-(void) testJump
{
    const char *Sources[] = {
        //jmp
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "jmp skip\n"
        "mov r1, 3\n"
        "skip:\n"
        "mov r1, 4\n"
        "jmp repeat\n",
        
        //jz
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "jz repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "mov r2, 248\n"
        "add r0, 1\n"
        "xor r2, r0\n"
        "jz repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "cmp r0, 230\n"
        "jz repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 0xff\n"
        "repeat:\n"
        "add r0, 1\n"
        "mov flags, r0\n"
        "jz repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        //jnz
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "jnz repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "mov r2, 248\n"
        "add r0, 1\n"
        "xor r2, r0\n"
        "jnz repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "cmp r0, 230\n"
        "jnz repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 0xff\n"
        "repeat:\n"
        "add r0, 1\n"
        "mov flags, r0\n"
        "jnz repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        //js
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "js repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "mov r2, 248\n"
        "add r0, 1\n"
        "xor r2, r0\n"
        "js repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "cmp r0, 230\n"
        "js repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 0xff\n"
        "repeat:\n"
        "add r0, 1\n"
        "mov flags, r0\n"
        "js repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        //jns
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "jns repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "mov r2, 248\n"
        "add r0, 1\n"
        "xor r2, r0\n"
        "jns repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "cmp r0, 230\n"
        "jns repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 0xff\n"
        "repeat:\n"
        "add r0, 1\n"
        "mov flags, r0\n"
        "jns repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        //jo
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "jo repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "mov r2, 248\n"
        "add r0, 1\n"
        "xor r2, r0\n"
        "jo repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "cmp r0, 230\n"
        "jo repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 0xff\n"
        "repeat:\n"
        "add r0, 1\n"
        "mov flags, r0\n"
        "jo repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        //jno
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "jno repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "mov r2, 248\n"
        "add r0, 1\n"
        "xor r2, r0\n"
        "jno repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "cmp r0, 230\n"
        "jno repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 0xff\n"
        "repeat:\n"
        "add r0, 1\n"
        "mov flags, r0\n"
        "jno repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        //jul
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "jul repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "mov r2, 248\n"
        "add r0, 1\n"
        "xor r2, r0\n"
        "jul repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "cmp r0, 230\n"
        "jul repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 0xff\n"
        "repeat:\n"
        "add r0, 1\n"
        "mov flags, r0\n"
        "jul repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        //juge
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "juge repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "mov r2, 248\n"
        "add r0, 1\n"
        "xor r2, r0\n"
        "juge repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "cmp r0, 230\n"
        "juge repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 0xff\n"
        "repeat:\n"
        "add r0, 1\n"
        "mov flags, r0\n"
        "juge repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        //jule
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "jule repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "mov r2, 248\n"
        "add r0, 1\n"
        "xor r2, r0\n"
        "jule repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "cmp r0, 230\n"
        "jule repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 0xff\n"
        "repeat:\n"
        "add r0, 1\n"
        "mov flags, r0\n"
        "jule repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        //jug
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "jug repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "mov r2, 248\n"
        "add r0, 1\n"
        "xor r2, r0\n"
        "jug repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "cmp r0, 230\n"
        "jug repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 0xff\n"
        "repeat:\n"
        "add r0, 1\n"
        "mov flags, r0\n"
        "jug repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        //jsl
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "jsl repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "mov r2, 248\n"
        "add r0, 1\n"
        "xor r2, r0\n"
        "jsl repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "cmp r0, 230\n"
        "jsl repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 0xff\n"
        "repeat:\n"
        "add r0, 1\n"
        "mov flags, r0\n"
        "jsl repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        //jsge
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "jsge repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "mov r2, 248\n"
        "add r0, 1\n"
        "xor r2, r0\n"
        "jsge repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "cmp r0, 230\n"
        "jsge repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 0xff\n"
        "repeat:\n"
        "add r0, 1\n"
        "mov flags, r0\n"
        "jsge repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        //jsle
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "jsle repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "mov r2, 248\n"
        "add r0, 1\n"
        "xor r2, r0\n"
        "jsle repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "cmp r0, 230\n"
        "jsle repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 0xff\n"
        "repeat:\n"
        "add r0, 1\n"
        "mov flags, r0\n"
        "jsle repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        //jsg
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "jsg repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "mov r2, 248\n"
        "add r0, 1\n"
        "xor r2, r0\n"
        "jsg repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 2\n"
        "repeat:\n"
        "add r0, 1\n"
        "cmp r0, 230\n"
        "jsg repeat\n"
        "add r3, 1\n"
        "jmp repeat\n",
        
        "mov r0, 0xff\n"
        "repeat:\n"
        "add r0, 1\n"
        "mov flags, r0\n"
        "jsg repeat\n"
        "add r3, 1\n"
        "jmp repeat\n"
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop] Halts: FALSE];
}

-(void) testUnsignedModulo
{
    const char *Sources[] = {
        "umod r0, r0\n"
        "hlt\n",
        
        "mov r0, 4\n"
        "umod r0, r0\n"
        "hlt\n",
        
        "mov r0, 4\n"
        "mov r1, 2\n"
        "umod r0, r1\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov r1, 0\n"
        "umod r0, r1\n"
        "hlt\n",
        
        "mov r0, 129\n"
        "mov r1, 129\n"
        "umod r0, r1\n"
        "hlt\n",
        
        "mov r0, 200\n"
        "mov r1, 129\n"
        "umod r0, r1\n"
        "hlt\n",
        
        "mov r0, 129\n"
        "mov r1, 200\n"
        "umod r0, r1\n"
        "hlt\n",
        
        "mov r0, -128\n"
        "mov r1, -1\n"
        "umod r0, r1\n"
        "hlt\n",
        
        "mov r0, -1\n"
        "mov r1, -128\n"
        "umod r0, r1\n"
        "hlt\n",
        
        "mov r0, -128\n"
        "mov r1, 1\n"
        "umod r0, r1\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov r1, -128\n"
        "umod r0, r1\n"
        "hlt\n",
        
        "umod r0, [r0]\n"
        "hlt\n",
        
        "umod r0, [data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 4\n"
        "umod r0, [data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "umod r0, [r0]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 4\n"
        "umod r1, [r0]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "umod r0, [r0+data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "umod r0, [r0+data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 4\n"
        "umod r1, [r0+data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "umod r0, [r0+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "umod r1, [r0+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "umod r2, [r0+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "umod [r0], r0\n"
        "hlt\n",
        
        "umod [data], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 4\n"
        "umod [data], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "umod [r0], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 4\n"
        "umod [r0], r1\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "umod [r0+data], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "umod [r0+data], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 4\n"
        "umod [r0+data], r1\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "umod [r0+r1], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "umod [r0+r1], r1\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "umod [r0+r1], r2\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "umod [data], [data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data + 1\n"
        "umod [r0], [data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data + 1\n"
        "umod [data], [r0]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "umod [data+r1], [data+r0]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "umod [data+r0], [data+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r3, data\n"
        "umod [r3+r1], [r3+r2]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r3, data\n"
        "umod [r3+r2], [r3+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r3, data\n"
        "umod [r3+r1], [r3+r2]\n"
        "hlt\n"
        "data: .byte 10, 0, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r3, data\n"
        "umod [r3+r2], [r3+r1]\n"
        "hlt\n"
        "data: .byte 10, 0, 30, 40\n",
        
        "mov [127], 0xff\n"
        "mov [128], 0xff\n"
        "mov [255], 0xff\n"
        "umod [127], 1\n"
        "umod [128], 2\n"
        "umod [255], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 0xff\n"
        "mov [128+r0], 0xff\n"
        "mov [255+r0], 0xff\n"
        "umod [127+r0], 1\n"
        "umod [128+r0], 2\n"
        "umod [255+r0], 3\n"
        "hlt\n",
        
        "mov [127], 0xff\n"
        "mov [128], 0xff\n"
        "mov [255], 0xff\n"
        "mov r1, 127\n"
        "umod [r1], 1\n"
        "mov r1, 128\n"
        "umod [r1], 2\n"
        "mov r1, 255\n"
        "umod [r1], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 0xff\n"
        "mov [128+r0], 0xff\n"
        "mov [255+r0], 0xff\n"
        "mov r1, 127\n"
        "umod [r1+r0], 1\n"
        "mov r1, 128\n"
        "umod [r1+r0], 2\n"
        "mov r1, 255\n"
        "umod [r1+r0], 3\n"
        "hlt\n",
        
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "umod r0, [127]\n"
        "umod r1, [128]\n"
        "umod r2, [255]\n"
        "hlt\n",
        
        "mov [127], 0xf0\n"
        "mov [128], 0x0f\n"
        "mov [255], 0xc3\n"
        "umod [0], [127]\n"
        "umod [127], [128]\n"
        "umod [128], [255]\n"
        "umod [255], [0]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "mov [127+r0], 0xff\n"
        "mov [128+r0], 0xff\n"
        "mov [255+r0], 0xff\n"
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "umod [127+r3], 1\n"
        "umod [128+r3], 2\n"
        "umod [255+r3], 3\n"
        "umod r0, [127+r3]\n"
        "umod r1, [128+r3]\n"
        "umod r2, [255+r3]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "mov [127+r3], 0xff\n"
        "mov [128+r3], 0xff\n"
        "mov [255+r3], 0xff\n"
        "umod [127+r3], 1\n"
        "umod [128+r3], 2\n"
        "umod [255+r3], 3\n"
        "umod [0+r3], [127+r3]\n"
        "umod [127+r3], [128+r3]\n"
        "umod [128+r3], [255+r3]\n"
        "umod [255+r3], [0+r3]\n"
        "hlt\n",
        
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "umod r0, [r3]\n"
        "mov r3, 128\n"
        "umod r1, [r3]\n"
        "mov r3, 255\n"
        "umod r2, [r3]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 3\n"
        "mov [255], 5\n"
        "mov r3, 127\n"
        "umod [0], [r3]\n"
        "mov r3, 128\n"
        "umod [127], [r3]\n"
        "mov r3, 255\n"
        "umod [128], [r3]\n"
        "umod [r3], [0]\n"
        "hlt\n",
        
        "mov r2, 0xff\n"
        "mov r3, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r0, 1\n"
        "mov r3, 127\n"
        "umod r0, [r3+r0]\n"
        "mov [0], r0\n"
        "mov r0, 1\n"
        "mov r3, 128\n"
        "umod r1, [r3+r0]\n"
        "mov r3, 255\n"
        "umod r2, [r3+r0]\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 1\n"
        "mov [128+r0], 3\n"
        "mov [255+r0], 5\n"
        "mov r3, 127\n"
        "umod [0+r0], [r3+r0]\n"
        "mov r3, 128\n"
        "umod [127+r0], [r3+r0]\n"
        "mov r3, 255\n"
        "umod [128+r0], [r3+r0]\n"
        "umod [r3+r0], [0+r0]\n"
        "hlt\n",
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop]];
    
    for (size_t Loop = 0; Loop < 256; Loop++)
    {
        for (size_t Loop2 = 0; Loop2 < 256; Loop2++)
        {
            [self run: [[NSString stringWithFormat: @"mov r0, %zu\numod r0, %zu\nhlt\n", Loop, Loop2] UTF8String]];
            [self run: [[NSString stringWithFormat: @".byte %zu\n.entrypoint\numod [0], %zu\nhlt\n", Loop, Loop2] UTF8String]];
            [self run: [[NSString stringWithFormat: @".byte %zu\n.entrypoint\numod [r0], %zu\nhlt\n", Loop, Loop2] UTF8String]];
            [self run: [[NSString stringWithFormat: @".byte 0, 0, 0, %zu\n.entrypoint\nmov r0, 1\numod [r0+2], %zu\nhlt\n", Loop, Loop2] UTF8String]];
            [self run: [[NSString stringWithFormat: @".byte 0, 0, 0, %zu\n.entrypoint\nmov r0, 1\nmov r1, 2\numod [r0+r1], %zu\nhlt\n", Loop, Loop2] UTF8String]];
        }
    }
}

-(void) testSignedModulo
{
    const char *Sources[] = {
        "smod r0, r0\n"
        "hlt\n",
        
        "mov r0, 4\n"
        "smod r0, r0\n"
        "hlt\n",
        
        "mov r0, 4\n"
        "mov r1, 2\n"
        "smod r0, r1\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov r1, 0\n"
        "smod r0, r1\n"
        "hlt\n",
        
        "mov r0, 129\n"
        "mov r1, 129\n"
        "smod r0, r1\n"
        "hlt\n",
        
        "mov r0, 200\n"
        "mov r1, 129\n"
        "smod r0, r1\n"
        "hlt\n",
        
        "mov r0, 129\n"
        "mov r1, 200\n"
        "smod r0, r1\n"
        "hlt\n",
        
        "mov r0, -128\n"
        "mov r1, -1\n"
        "smod r0, r1\n"
        "hlt\n",
        
        "mov r0, -1\n"
        "mov r1, -128\n"
        "smod r0, r1\n"
        "hlt\n",
        
        "mov r0, -128\n"
        "mov r1, 1\n"
        "smod r0, r1\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov r1, -128\n"
        "smod r0, r1\n"
        "hlt\n",
        
        "smod r0, [r0]\n"
        "hlt\n",
        
        "smod r0, [data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 4\n"
        "smod r0, [data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "smod r0, [r0]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 4\n"
        "smod r1, [r0]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "smod r0, [r0+data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "smod r0, [r0+data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 4\n"
        "smod r1, [r0+data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "smod r0, [r0+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "smod r1, [r0+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "smod r2, [r0+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, -1\n"
        "mov r1, data\n"
        "smod r0, [r1+1]\n"
        "hlt\n"
        "data: .byte -128\n",
        
        "mov r0, -128\n"
        "mov r1, data\n"
        "smod r0, [r1+1]\n"
        "hlt\n"
        "data: .byte -1\n",
        
        "mov r0, 1\n"
        "mov r1, data\n"
        "smod r0, [r1+1]\n"
        "hlt\n"
        "data: .byte -128\n",
        
        "mov r0, -128\n"
        "mov r1, data\n"
        "smod r0, [r1+1]\n"
        "hlt\n"
        "data: .byte 1\n",
        
        "smod [r0], r0\n"
        "hlt\n",
        
        "smod [data], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 4\n"
        "smod [data], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "smod [r0], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 4\n"
        "smod [r0], r1\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "smod [r0+data], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "smod [r0+data], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 4\n"
        "smod [r0+data], r1\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "smod [r0+r1], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "smod [r0+r1], r1\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "smod [r0+r1], r2\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, -1\n"
        "smod [r0], r1\n"
        "hlt\n"
        "data: .byte -128\n",
        
        "mov r0, data\n"
        "mov r1, -128\n"
        "smod [r0], r1\n"
        "hlt\n"
        "data: .byte -1\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "smod [r0], r1\n"
        "hlt\n"
        "data: .byte -128\n",
        
        "mov r0, data\n"
        "mov r1, -128\n"
        "smod [r0], r1\n"
        "hlt\n"
        "data: .byte 1\n",
        
        "smod [data], [data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data + 1\n"
        "smod [r0], [data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data + 1\n"
        "smod [data], [r0]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "smod [data+r1], [data+r0]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "smod [data+r0], [data+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r3, data\n"
        "smod [r3+r1], [r3+r2]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r3, data\n"
        "smod [r3+r2], [r3+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r3, data\n"
        "smod [r3+r1], [r3+r2]\n"
        "hlt\n"
        "data: .byte 10, 0, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r3, data\n"
        "smod [r3+r2], [r3+r1]\n"
        "hlt\n"
        "data: .byte 10, 0, 30, 40\n",
        
        "mov r0, data\n"
        "smod [r0], [r0+1]\n"
        "hlt\n"
        "data: .byte -128, -1\n",
        
        "mov r0, data\n"
        "smod [r0+1], [r0]\n"
        "hlt\n"
        "data: .byte -128, -1\n",
        
        "mov r0, data\n"
        "smod [r0], [r0+1]\n"
        "hlt\n"
        "data: .byte -128, 1\n",
        
        "mov r0, data\n"
        "smod [r0+1], [r0]\n"
        "hlt\n"
        "data: .byte -128, 1\n",
        
        "mov [127], 0xff\n"
        "mov [128], 0xff\n"
        "mov [255], 0xff\n"
        "smod [127], 1\n"
        "smod [128], 2\n"
        "smod [255], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 0xff\n"
        "mov [128+r0], 0xff\n"
        "mov [255+r0], 0xff\n"
        "smod [127+r0], 1\n"
        "smod [128+r0], 2\n"
        "smod [255+r0], 3\n"
        "hlt\n",
        
        "mov [127], 0xff\n"
        "mov [128], 0xff\n"
        "mov [255], 0xff\n"
        "mov r1, 127\n"
        "smod [r1], 1\n"
        "mov r1, 128\n"
        "smod [r1], 2\n"
        "mov r1, 255\n"
        "smod [r1], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 0xff\n"
        "mov [128+r0], 0xff\n"
        "mov [255+r0], 0xff\n"
        "mov r1, 127\n"
        "smod [r1+r0], 1\n"
        "mov r1, 128\n"
        "smod [r1+r0], 2\n"
        "mov r1, 255\n"
        "smod [r1+r0], 3\n"
        "hlt\n",
        
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "smod r0, [127]\n"
        "smod r1, [128]\n"
        "smod r2, [255]\n"
        "hlt\n",
        
        "mov [127], 0xf0\n"
        "mov [128], 0x0f\n"
        "mov [255], 0xc3\n"
        "smod [0], [127]\n"
        "smod [127], [128]\n"
        "smod [128], [255]\n"
        "smod [255], [0]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "mov [127+r0], 0xff\n"
        "mov [128+r0], 0xff\n"
        "mov [255+r0], 0xff\n"
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "smod [127+r3], 1\n"
        "smod [128+r3], 2\n"
        "smod [255+r3], 3\n"
        "smod r0, [127+r3]\n"
        "smod r1, [128+r3]\n"
        "smod r2, [255+r3]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "mov [127+r3], 0xff\n"
        "mov [128+r3], 0xff\n"
        "mov [255+r3], 0xff\n"
        "smod [127+r3], 1\n"
        "smod [128+r3], 2\n"
        "smod [255+r3], 3\n"
        "smod [0+r3], [127+r3]\n"
        "smod [127+r3], [128+r3]\n"
        "smod [128+r3], [255+r3]\n"
        "smod [255+r3], [0+r3]\n"
        "hlt\n",
        
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "smod r0, [r3]\n"
        "mov r3, 128\n"
        "smod r1, [r3]\n"
        "mov r3, 255\n"
        "smod r2, [r3]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 3\n"
        "mov [255], 5\n"
        "mov r3, 127\n"
        "smod [0], [r3]\n"
        "mov r3, 128\n"
        "smod [127], [r3]\n"
        "mov r3, 255\n"
        "smod [128], [r3]\n"
        "smod [r3], [0]\n"
        "hlt\n",
        
        "mov r2, 0xff\n"
        "mov r3, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r0, 1\n"
        "mov r3, 127\n"
        "smod r0, [r3+r0]\n"
        "mov [0], r0\n"
        "mov r0, 1\n"
        "mov r3, 128\n"
        "smod r1, [r3+r0]\n"
        "mov r3, 255\n"
        "smod r2, [r3+r0]\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 1\n"
        "mov [128+r0], 3\n"
        "mov [255+r0], 5\n"
        "mov r3, 127\n"
        "smod [0+r0], [r3+r0]\n"
        "mov r3, 128\n"
        "smod [127+r0], [r3+r0]\n"
        "mov r3, 255\n"
        "smod [128+r0], [r3+r0]\n"
        "smod [r3+r0], [0+r0]\n"
        "hlt\n",
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop]];
    
    for (size_t Loop = 0; Loop < 256; Loop++)
    {
        for (size_t Loop2 = 0; Loop2 < 256; Loop2++)
        {
            [self run: [[NSString stringWithFormat: @"mov r0, %zu\nsmod r0, %zu\nhlt\n", Loop, Loop2] UTF8String]];
            [self run: [[NSString stringWithFormat: @".byte %zu\n.entrypoint\nsmod [0], %zu\nhlt\n", Loop, Loop2] UTF8String]];
            [self run: [[NSString stringWithFormat: @".byte %zu\n.entrypoint\nsmod [r0], %zu\nhlt\n", Loop, Loop2] UTF8String]];
            [self run: [[NSString stringWithFormat: @".byte 0, 0, 0, %zu\n.entrypoint\nmov r0, 1\nsmod [r0+2], %zu\nhlt\n", Loop, Loop2] UTF8String]];
            [self run: [[NSString stringWithFormat: @".byte 0, 0, 0, %zu\n.entrypoint\nmov r0, 1\nmov r1, 2\nsmod [r0+r1], %zu\nhlt\n", Loop, Loop2] UTF8String]];
        }
    }
}

-(void) testUnsignedDivision
{
    const char *Sources[] = {
        "udiv r0, r0\n"
        "hlt\n",
        
        "mov r0, 4\n"
        "udiv r0, r0\n"
        "hlt\n",
        
        "mov r0, 4\n"
        "mov r1, 2\n"
        "udiv r0, r1\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov r1, 0\n"
        "udiv r0, r1\n"
        "hlt\n",
        
        "mov r0, 129\n"
        "mov r1, 129\n"
        "udiv r0, r1\n"
        "hlt\n",
        
        "mov r0, 200\n"
        "mov r1, 129\n"
        "udiv r0, r1\n"
        "hlt\n",
        
        "mov r0, 129\n"
        "mov r1, 200\n"
        "udiv r0, r1\n"
        "hlt\n",
        
        "mov r0, -128\n"
        "mov r1, -1\n"
        "udiv r0, r1\n"
        "hlt\n",
        
        "mov r0, -1\n"
        "mov r1, -128\n"
        "udiv r0, r1\n"
        "hlt\n",
        
        "mov r0, -128\n"
        "mov r1, 1\n"
        "udiv r0, r1\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov r1, -128\n"
        "udiv r0, r1\n"
        "hlt\n",
        
        "udiv r0, [r0]\n"
        "hlt\n",
        
        "udiv r0, [data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 4\n"
        "udiv r0, [data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "udiv r0, [r0]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 4\n"
        "udiv r1, [r0]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "udiv r0, [r0+data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "udiv r0, [r0+data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 4\n"
        "udiv r1, [r0+data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "udiv r0, [r0+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "udiv r1, [r0+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "udiv r2, [r0+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, -1\n"
        "mov r1, data\n"
        "udiv r0, [r1+1]\n"
        "hlt\n"
        "data: .byte -128\n",
        
        "mov r0, -128\n"
        "mov r1, data\n"
        "udiv r0, [r1+1]\n"
        "hlt\n"
        "data: .byte -1\n",
        
        "mov r0, 1\n"
        "mov r1, data\n"
        "udiv r0, [r1+1]\n"
        "hlt\n"
        "data: .byte -128\n",
        
        "mov r0, -128\n"
        "mov r1, data\n"
        "udiv r0, [r1+1]\n"
        "hlt\n"
        "data: .byte 1\n",
        
        "udiv [r0], r0\n"
        "hlt\n",
        
        "udiv [data], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 4\n"
        "udiv [data], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "udiv [r0], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 4\n"
        "udiv [r0], r1\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "udiv [r0+data], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "udiv [r0+data], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 4\n"
        "udiv [r0+data], r1\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "udiv [r0+r1], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "udiv [r0+r1], r1\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "udiv [r0+r1], r2\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, -1\n"
        "udiv [r0], r1\n"
        "hlt\n"
        "data: .byte -128\n",
        
        "mov r0, data\n"
        "mov r1, -128\n"
        "udiv [r0], r1\n"
        "hlt\n"
        "data: .byte -1\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "udiv [r0], r1\n"
        "hlt\n"
        "data: .byte -128\n",
        
        "mov r0, data\n"
        "mov r1, -128\n"
        "udiv [r0], r1\n"
        "hlt\n"
        "data: .byte 1\n",
        
        "udiv [data], [data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data + 1\n"
        "udiv [r0], [data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data + 1\n"
        "udiv [data], [r0]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "udiv [data+r1], [data+r0]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "udiv [data+r0], [data+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r3, data\n"
        "udiv [r3+r1], [r3+r2]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r3, data\n"
        "udiv [r3+r2], [r3+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r3, data\n"
        "udiv [r3+r1], [r3+r2]\n"
        "hlt\n"
        "data: .byte 10, 0, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r3, data\n"
        "udiv [r3+r2], [r3+r1]\n"
        "hlt\n"
        "data: .byte 10, 0, 30, 40\n",
        
        "mov r0, data\n"
        "udiv [r0], [r0+1]\n"
        "hlt\n"
        "data: .byte -128, -1\n",
        
        "mov r0, data\n"
        "udiv [r0+1], [r0]\n"
        "hlt\n"
        "data: .byte -128, -1\n",
        
        "mov r0, data\n"
        "udiv [r0], [r0+1]\n"
        "hlt\n"
        "data: .byte -128, 1\n",
        
        "mov r0, data\n"
        "udiv [r0+1], [r0]\n"
        "hlt\n"
        "data: .byte -128, 1\n",
        
        "mov [127], 0xff\n"
        "mov [128], 0xff\n"
        "mov [255], 0xff\n"
        "udiv [127], 1\n"
        "udiv [128], 2\n"
        "udiv [255], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 0xff\n"
        "mov [128+r0], 0xff\n"
        "mov [255+r0], 0xff\n"
        "udiv [127+r0], 1\n"
        "udiv [128+r0], 2\n"
        "udiv [255+r0], 3\n"
        "hlt\n",
        
        "mov [127], 0xff\n"
        "mov [128], 0xff\n"
        "mov [255], 0xff\n"
        "mov r1, 127\n"
        "udiv [r1], 1\n"
        "mov r1, 128\n"
        "udiv [r1], 2\n"
        "mov r1, 255\n"
        "udiv [r1], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 0xff\n"
        "mov [128+r0], 0xff\n"
        "mov [255+r0], 0xff\n"
        "mov r1, 127\n"
        "udiv [r1+r0], 1\n"
        "mov r1, 128\n"
        "udiv [r1+r0], 2\n"
        "mov r1, 255\n"
        "udiv [r1+r0], 3\n"
        "hlt\n",
        
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "udiv r0, [127]\n"
        "udiv r1, [128]\n"
        "udiv r2, [255]\n"
        "hlt\n",
        
        "mov [127], 0xf0\n"
        "mov [128], 0x0f\n"
        "mov [255], 0xc3\n"
        "udiv [0], [127]\n"
        "udiv [127], [128]\n"
        "udiv [128], [255]\n"
        "udiv [255], [0]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "mov [127+r0], 0xff\n"
        "mov [128+r0], 0xff\n"
        "mov [255+r0], 0xff\n"
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "udiv [127+r3], 1\n"
        "udiv [128+r3], 2\n"
        "udiv [255+r3], 3\n"
        "udiv r0, [127+r3]\n"
        "udiv r1, [128+r3]\n"
        "udiv r2, [255+r3]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "mov [127+r3], 0xff\n"
        "mov [128+r3], 0xff\n"
        "mov [255+r3], 0xff\n"
        "udiv [127+r3], 1\n"
        "udiv [128+r3], 2\n"
        "udiv [255+r3], 3\n"
        "udiv [0+r3], [127+r3]\n"
        "udiv [127+r3], [128+r3]\n"
        "udiv [128+r3], [255+r3]\n"
        "udiv [255+r3], [0+r3]\n"
        "hlt\n",
        
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "udiv r0, [r3]\n"
        "mov r3, 128\n"
        "udiv r1, [r3]\n"
        "mov r3, 255\n"
        "udiv r2, [r3]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 3\n"
        "mov [255], 5\n"
        "mov r3, 127\n"
        "udiv [0], [r3]\n"
        "mov r3, 128\n"
        "udiv [127], [r3]\n"
        "mov r3, 255\n"
        "udiv [128], [r3]\n"
        "udiv [r3], [0]\n"
        "hlt\n",
        
        "mov r2, 0xff\n"
        "mov r3, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r0, 1\n"
        "mov r3, 127\n"
        "udiv r0, [r3+r0]\n"
        "mov [0], r0\n"
        "mov r0, 1\n"
        "mov r3, 128\n"
        "udiv r1, [r3+r0]\n"
        "mov r3, 255\n"
        "udiv r2, [r3+r0]\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 1\n"
        "mov [128+r0], 3\n"
        "mov [255+r0], 5\n"
        "mov r3, 127\n"
        "udiv [0+r0], [r3+r0]\n"
        "mov r3, 128\n"
        "udiv [127+r0], [r3+r0]\n"
        "mov r3, 255\n"
        "udiv [128+r0], [r3+r0]\n"
        "udiv [r3+r0], [0+r0]\n"
        "hlt\n",
        
        ".byte 0, 0, 0\n"
        ".entrypoint\n"
        "udiv r0, 0\n"
        "udiv r0, 1\n"
        "mov r0, 1\n"
        "udiv r0, 0\n"
        "udiv r0, 1\n"
        "udiv [0], 0\n"
        "udiv [0], 1\n"
        "mov [0], 1\n"
        "udiv [0], 0\n"
        "udiv [0], 1\n"
        "udiv [1], [2]\n"
        "udiv [1], [0]\n"
        "mov [1], 1\n"
        "udiv [1], [2]\n"
        "udiv [1], [0]\n"
        "udiv r1, [2]\n"
        "udiv r1, [0]\n"
        "udiv r0, [2]\n"
        "udiv r0, [0]\n"
        "udiv [2], r1\n"
        "udiv [2], r0\n"
        "mov [2], 1\n"
        "udiv [2], r1\n"
        "udiv [2], r0\n"
        "hlt\n",
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop]];
    
    for (size_t Loop = 0; Loop < 256; Loop++)
    {
        for (size_t Loop2 = 0; Loop2 < 256; Loop2++)
        {
            [self run: [[NSString stringWithFormat: @"mov r0, %zu\nudiv r0, %zu\nhlt\n", Loop, Loop2] UTF8String]];
            [self run: [[NSString stringWithFormat: @".byte %zu\n.entrypoint\nudiv [0], %zu\nhlt\n", Loop, Loop2] UTF8String]];
            [self run: [[NSString stringWithFormat: @".byte %zu\n.entrypoint\nudiv [r0], %zu\nhlt\n", Loop, Loop2] UTF8String]];
            [self run: [[NSString stringWithFormat: @".byte 0, 0, 0, %zu\n.entrypoint\nmov r0, 1\nudiv [r0+2], %zu\nhlt\n", Loop, Loop2] UTF8String]];
            [self run: [[NSString stringWithFormat: @".byte 0, 0, 0, %zu\n.entrypoint\nmov r0, 1\nmov r1, 2\nudiv [r0+r1], %zu\nhlt\n", Loop, Loop2] UTF8String]];
        }
    }
}

-(void) testSignedDivision
{
    const char *Sources[] = {
        "sdiv r0, r0\n"
        "hlt\n",
        
        "mov r0, 4\n"
        "sdiv r0, r0\n"
        "hlt\n",
        
        "mov r0, 4\n"
        "mov r1, 2\n"
        "sdiv r0, r1\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov r1, 0\n"
        "sdiv r0, r1\n"
        "hlt\n",
        
        "mov r0, 129\n"
        "mov r1, 129\n"
        "sdiv r0, r1\n"
        "hlt\n",
        
        "mov r0, 200\n"
        "mov r1, 129\n"
        "sdiv r0, r1\n"
        "hlt\n",
        
        "mov r0, 129\n"
        "mov r1, 200\n"
        "sdiv r0, r1\n"
        "hlt\n",
        
        "mov r0, -128\n"
        "mov r1, -1\n"
        "sdiv r0, r1\n"
        "hlt\n",
        
        "mov r0, -1\n"
        "mov r1, -128\n"
        "sdiv r0, r1\n"
        "hlt\n",
        
        "mov r0, -128\n"
        "mov r1, 1\n"
        "sdiv r0, r1\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov r1, -128\n"
        "sdiv r0, r1\n"
        "hlt\n",
        
        "sdiv r0, [r0]\n"
        "hlt\n",
        
        "sdiv r0, [data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 4\n"
        "sdiv r0, [data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "sdiv r0, [r0]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 4\n"
        "sdiv r1, [r0]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "sdiv r0, [r0+data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "sdiv r0, [r0+data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 4\n"
        "sdiv r1, [r0+data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "sdiv r0, [r0+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "sdiv r1, [r0+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "sdiv r2, [r0+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, -1\n"
        "mov r1, data\n"
        "sdiv r0, [r1+1]\n"
        "hlt\n"
        "data: .byte -128\n",
        
        "mov r0, -128\n"
        "mov r1, data\n"
        "sdiv r0, [r1+1]\n"
        "hlt\n"
        "data: .byte -1\n",
        
        "mov r0, 1\n"
        "mov r1, data\n"
        "sdiv r0, [r1+1]\n"
        "hlt\n"
        "data: .byte -128\n",
        
        "mov r0, -128\n"
        "mov r1, data\n"
        "sdiv r0, [r1+1]\n"
        "hlt\n"
        "data: .byte 1\n",
        
        "sdiv [r0], r0\n"
        "hlt\n",
        
        "sdiv [data], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 4\n"
        "sdiv [data], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "sdiv [r0], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 4\n"
        "sdiv [r0], r1\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "sdiv [r0+data], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "sdiv [r0+data], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 4\n"
        "sdiv [r0+data], r1\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "sdiv [r0+r1], r0\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "sdiv [r0+r1], r1\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "sdiv [r0+r1], r2\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data\n"
        "mov r1, -1\n"
        "sdiv [r0], r1\n"
        "hlt\n"
        "data: .byte -128\n",
        
        "mov r0, data\n"
        "mov r1, -128\n"
        "sdiv [r0], r1\n"
        "hlt\n"
        "data: .byte -1\n",
        
        "mov r0, data\n"
        "mov r1, 1\n"
        "sdiv [r0], r1\n"
        "hlt\n"
        "data: .byte -128\n",
        
        "mov r0, data\n"
        "mov r1, -128\n"
        "sdiv [r0], r1\n"
        "hlt\n"
        "data: .byte 1\n",
        
        "sdiv [data], [data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data + 1\n"
        "sdiv [r0], [data]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, data + 1\n"
        "sdiv [data], [r0]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "sdiv [data+r1], [data+r0]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "sdiv [data+r0], [data+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r3, data\n"
        "sdiv [r3+r1], [r3+r2]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r3, data\n"
        "sdiv [r3+r2], [r3+r1]\n"
        "hlt\n"
        "data: .byte 10, 20, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r3, data\n"
        "sdiv [r3+r1], [r3+r2]\n"
        "hlt\n"
        "data: .byte 10, 0, 30, 40\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "mov r3, data\n"
        "sdiv [r3+r2], [r3+r1]\n"
        "hlt\n"
        "data: .byte 10, 0, 30, 40\n",
        
        "mov r0, data\n"
        "sdiv [r0], [r0+1]\n"
        "hlt\n"
        "data: .byte -128, -1\n",
        
        "mov r0, data\n"
        "sdiv [r0+1], [r0]\n"
        "hlt\n"
        "data: .byte -128, -1\n",
        
        "mov r0, data\n"
        "sdiv [r0], [r0+1]\n"
        "hlt\n"
        "data: .byte -128, 1\n",
        
        "mov r0, data\n"
        "sdiv [r0+1], [r0]\n"
        "hlt\n"
        "data: .byte -128, 1\n",
        
        "mov [127], 0xff\n"
        "mov [128], 0xff\n"
        "mov [255], 0xff\n"
        "sdiv [127], 1\n"
        "sdiv [128], 2\n"
        "sdiv [255], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 0xff\n"
        "mov [128+r0], 0xff\n"
        "mov [255+r0], 0xff\n"
        "sdiv [127+r0], 1\n"
        "sdiv [128+r0], 2\n"
        "sdiv [255+r0], 3\n"
        "hlt\n",
        
        "mov [127], 0xff\n"
        "mov [128], 0xff\n"
        "mov [255], 0xff\n"
        "mov r1, 127\n"
        "sdiv [r1], 1\n"
        "mov r1, 128\n"
        "sdiv [r1], 2\n"
        "mov r1, 255\n"
        "sdiv [r1], 3\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 0xff\n"
        "mov [128+r0], 0xff\n"
        "mov [255+r0], 0xff\n"
        "mov r1, 127\n"
        "sdiv [r1+r0], 1\n"
        "mov r1, 128\n"
        "sdiv [r1+r0], 2\n"
        "mov r1, 255\n"
        "sdiv [r1+r0], 3\n"
        "hlt\n",
        
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "sdiv r0, [127]\n"
        "sdiv r1, [128]\n"
        "sdiv r2, [255]\n"
        "hlt\n",
        
        "mov [127], 0xf0\n"
        "mov [128], 0x0f\n"
        "mov [255], 0xc3\n"
        "sdiv [0], [127]\n"
        "sdiv [127], [128]\n"
        "sdiv [128], [255]\n"
        "sdiv [255], [0]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "mov [127+r0], 0xff\n"
        "mov [128+r0], 0xff\n"
        "mov [255+r0], 0xff\n"
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "sdiv [127+r3], 1\n"
        "sdiv [128+r3], 2\n"
        "sdiv [255+r3], 3\n"
        "sdiv r0, [127+r3]\n"
        "sdiv r1, [128+r3]\n"
        "sdiv r2, [255+r3]\n"
        "hlt\n",
        
        "mov r3, 1\n"
        "mov [127+r3], 0xff\n"
        "mov [128+r3], 0xff\n"
        "mov [255+r3], 0xff\n"
        "sdiv [127+r3], 1\n"
        "sdiv [128+r3], 2\n"
        "sdiv [255+r3], 3\n"
        "sdiv [0+r3], [127+r3]\n"
        "sdiv [127+r3], [128+r3]\n"
        "sdiv [128+r3], [255+r3]\n"
        "sdiv [255+r3], [0+r3]\n"
        "hlt\n",
        
        "mov r0, 0xff\n"
        "mov r1, 0xff\n"
        "mov r2, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r3, 127\n"
        "sdiv r0, [r3]\n"
        "mov r3, 128\n"
        "sdiv r1, [r3]\n"
        "mov r3, 255\n"
        "sdiv r2, [r3]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 3\n"
        "mov [255], 5\n"
        "mov r3, 127\n"
        "sdiv [0], [r3]\n"
        "mov r3, 128\n"
        "sdiv [127], [r3]\n"
        "mov r3, 255\n"
        "sdiv [128], [r3]\n"
        "sdiv [r3], [0]\n"
        "hlt\n",
        
        "mov r2, 0xff\n"
        "mov r3, 0xff\n"
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r0, 1\n"
        "mov r3, 127\n"
        "sdiv r0, [r3+r0]\n"
        "mov [0], r0\n"
        "mov r0, 1\n"
        "mov r3, 128\n"
        "sdiv r1, [r3+r0]\n"
        "mov r3, 255\n"
        "sdiv r2, [r3+r0]\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 1\n"
        "mov [128+r0], 3\n"
        "mov [255+r0], 5\n"
        "mov r3, 127\n"
        "sdiv [0+r0], [r3+r0]\n"
        "mov r3, 128\n"
        "sdiv [127+r0], [r3+r0]\n"
        "mov r3, 255\n"
        "sdiv [128+r0], [r3+r0]\n"
        "sdiv [r3+r0], [0+r0]\n"
        "hlt\n",
        
        ".byte 0, 0, 0\n"
        ".entrypoint\n"
        "sdiv r0, 0\n"
        "sdiv r0, 1\n"
        "mov r0, 1\n"
        "sdiv r0, 0\n"
        "sdiv r0, 1\n"
        "sdiv [0], 0\n"
        "sdiv [0], 1\n"
        "mov [0], 1\n"
        "sdiv [0], 0\n"
        "sdiv [0], 1\n"
        "sdiv [1], [2]\n"
        "sdiv [1], [0]\n"
        "mov [1], 1\n"
        "sdiv [1], [2]\n"
        "sdiv [1], [0]\n"
        "sdiv r1, [2]\n"
        "sdiv r1, [0]\n"
        "sdiv r0, [2]\n"
        "sdiv r0, [0]\n"
        "sdiv [2], r1\n"
        "sdiv [2], r0\n"
        "mov [2], 1\n"
        "sdiv [2], r1\n"
        "sdiv [2], r0\n"
        "hlt\n",
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop]];
    
    for (size_t Loop = 0; Loop < 256; Loop++)
    {
        for (size_t Loop2 = 0; Loop2 < 256; Loop2++)
        {
            [self run: [[NSString stringWithFormat: @"mov r0, %zu\nsdiv r0, %zu\nhlt\n", Loop, Loop2] UTF8String]];
            [self run: [[NSString stringWithFormat: @".byte %zu\n.entrypoint\nsdiv [0], %zu\nhlt\n", Loop, Loop2] UTF8String]];
            [self run: [[NSString stringWithFormat: @".byte %zu\n.entrypoint\nsdiv [r0], %zu\nhlt\n", Loop, Loop2] UTF8String]];
            [self run: [[NSString stringWithFormat: @".byte 0, 0, 0, %zu\n.entrypoint\nmov r0, 1\nsdiv [r0+2], %zu\nhlt\n", Loop, Loop2] UTF8String]];
            [self run: [[NSString stringWithFormat: @".byte 0, 0, 0, %zu\n.entrypoint\nmov r0, 1\nmov r1, 2\nsdiv [r0+r1], %zu\nhlt\n", Loop, Loop2] UTF8String]];
        }
    }
}

-(void) testNegate
{
    const char *Sources[] = {
        "neg r0\n"
        "hlt\n",
        
        "mov r0, 4\n"
        "neg r0\n"
        "hlt\n",
        
        "mov r0, 127\n"
        "neg r0\n"
        "hlt\n",
        
        "mov r0, 128\n"
        "neg r0\n"
        "hlt\n",
        
        "mov r0, 255\n"
        "neg r0\n"
        "hlt\n",
        
        "neg [data]\n"
        "hlt\n"
        "data: .byte 4, 127, 128, 255\n",
        
        "mov r0, data + 1\n"
        "neg [r0]\n"
        "hlt\n"
        "data: .byte 4, 127, 128, 255\n",
        
        "mov r0, data + 1\n"
        "neg [data]\n"
        "hlt\n"
        "data: .byte 4, 127, 128, 255\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "neg [data+r1]\n"
        "hlt\n"
        "data: .byte 4, 127, 128, 255\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "neg [data+r0]\n"
        "hlt\n"
        "data: .byte 4, 127, 128, 255\n",
        
        "mov r1, 2\n"
        "mov r3, data\n"
        "neg [r3+r1]\n"
        "hlt\n"
        "data: .byte 4, 127, 128, 255\n",
        
        "mov r1, 2\n"
        "mov r3, data\n"
        "neg [r3+r2]\n"
        "hlt\n"
        "data: .byte 4, 127, 128, 255\n",
        
        "mov r1, 2\n"
        "mov r3, data\n"
        "neg [r3+r1]\n"
        "hlt\n"
        "data: .byte 10, 0, 30, 40\n",
        
        "mov r1, 2\n"
        "mov r3, data\n"
        "neg [r3+r2]\n"
        "hlt\n"
        "data: .byte 10, 0, 30, 40\n",
        
        "mov r0, data\n"
        "neg [r0]\n"
        "hlt\n"
        "data: .byte -128, -1\n",
        
        "mov r0, data\n"
        "neg [r0+1]\n"
        "hlt\n"
        "data: .byte -128, -1\n",
        
        "mov r0, data\n"
        "neg [r0]\n"
        "hlt\n"
        "data: .byte -128, 1\n",
        
        "mov r0, data\n"
        "neg [r0+1]\n"
        "hlt\n"
        "data: .byte -128, 1\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "neg [127]\n"
        "neg [128]\n"
        "neg [255]\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 1\n"
        "mov [128+r0], 2\n"
        "mov [255+r0], 3\n"
        "neg [127+r0]\n"
        "neg [128+r0]\n"
        "neg [255+r0]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r1, 127\n"
        "neg [r1]\n"
        "mov r1, 128\n"
        "neg [r1]\n"
        "mov r1, 255\n"
        "neg [r1]\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 1\n"
        "mov [128+r0], 2\n"
        "mov [255+r0], 3\n"
        "mov r1, 127\n"
        "neg [r1+r0]\n"
        "mov r1, 128\n"
        "neg [r1+r0]\n"
        "mov r1, 255\n"
        "neg [r1+r0]\n"
        "hlt\n",
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop]];
}

-(void) testNot
{
    const char *Sources[] = {
        "not r0\n"
        "hlt\n",
        
        "mov r0, 4\n"
        "not r0\n"
        "hlt\n",
        
        "mov r0, 127\n"
        "not r0\n"
        "hlt\n",
        
        "mov r0, 128\n"
        "not r0\n"
        "hlt\n",
        
        "mov r0, 255\n"
        "not r0\n"
        "hlt\n",
        
        "not [data]\n"
        "hlt\n"
        "data: .byte 4, 127, 128, 255\n",
        
        "mov r0, data + 1\n"
        "not [r0]\n"
        "hlt\n"
        "data: .byte 4, 127, 128, 255\n",
        
        "mov r0, data + 1\n"
        "not [data]\n"
        "hlt\n"
        "data: .byte 4, 127, 128, 255\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "not [data+r1]\n"
        "hlt\n"
        "data: .byte 4, 127, 128, 255\n",
        
        "mov r0, 1\n"
        "mov r1, 2\n"
        "not [data+r0]\n"
        "hlt\n"
        "data: .byte 4, 127, 128, 255\n",
        
        "mov r1, 2\n"
        "mov r3, data\n"
        "not [r3+r1]\n"
        "hlt\n"
        "data: .byte 4, 127, 128, 255\n",
        
        "mov r1, 2\n"
        "mov r3, data\n"
        "not [r3+r2]\n"
        "hlt\n"
        "data: .byte 4, 127, 128, 255\n",
        
        "mov r1, 2\n"
        "mov r3, data\n"
        "not [r3+r1]\n"
        "hlt\n"
        "data: .byte 10, 0, 30, 40\n",
        
        "mov r1, 2\n"
        "mov r3, data\n"
        "not [r3+r2]\n"
        "hlt\n"
        "data: .byte 10, 0, 30, 40\n",
        
        "mov r0, data\n"
        "not [r0]\n"
        "hlt\n"
        "data: .byte -128, -1\n",
        
        "mov r0, data\n"
        "not [r0+1]\n"
        "hlt\n"
        "data: .byte -128, -1\n",
        
        "mov r0, data\n"
        "not [r0]\n"
        "hlt\n"
        "data: .byte -128, 1\n",
        
        "mov r0, data\n"
        "not [r0+1]\n"
        "hlt\n"
        "data: .byte -128, 1\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "not [127]\n"
        "not [128]\n"
        "not [255]\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 1\n"
        "mov [128+r0], 2\n"
        "mov [255+r0], 3\n"
        "not [127+r0]\n"
        "not [128+r0]\n"
        "not [255+r0]\n"
        "hlt\n",
        
        "mov [127], 1\n"
        "mov [128], 2\n"
        "mov [255], 3\n"
        "mov r1, 127\n"
        "not [r1]\n"
        "mov r1, 128\n"
        "not [r1]\n"
        "mov r1, 255\n"
        "not [r1]\n"
        "hlt\n",
        
        "mov r0, 1\n"
        "mov [127+r0], 1\n"
        "mov [128+r0], 2\n"
        "mov [255+r0], 3\n"
        "mov r1, 127\n"
        "not [r1+r0]\n"
        "mov r1, 128\n"
        "not [r1+r0]\n"
        "mov r1, 255\n"
        "not [r1+r0]\n"
        "hlt\n",
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop]];
}

-(void) testNoOperation
{
    const char *Sources[] = {
        "nop\n"
        "hlt\n",
        
        "nop\n"
        "nop\n"
        "hlt\n",
        
        "nop\n"
        "nop\n"
        "nop\n"
        "nop\n"
        "nop\n"
        "nop\n"
        "hlt\n"
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop]];
}

-(void) testPartials
{
    const char *Sources[] = {
        "mov r1, 1\n"
        "add r1, r1\n"
        "jmp 4\n"
        ".byte 2 << 2\n"
        "mov r2, 2\n"
        "hlt\n"
        ".byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n"
        ".byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n"
        ".byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n"
        ".byte 0,0,0,0,0,0,0\n"
        "mov r2, 3\n"
        "hlt\n",
        
        "mov r1, -1\n"
        "add r1, r1\n"
        "jmp 4\n"
        ".byte 2 << 2\n"
        "mov r2, 2\n"
        "hlt\n"
        ".byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n"
        ".byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n"
        ".byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\n"
        ".byte 0,0,0,0,0,0,0\n"
        "mov r2, 3\n"
        "hlt\n"
    };
    
    for (size_t Loop = 0; Loop < sizeof(Sources) / sizeof(typeof(*Sources)); Loop++) [self run: Sources[Loop]];
}

-(void) testInvalidation
{
    const char *Source =
        "nop\n"
        "nop\n"
        "nop\n"
        "nop\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchExecutionGraph Graph = HKHubArchExecutionGraphCreate(CC_STD_ALLOCATOR, Binary->data, Binary->entrypoint);
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchJIT JIT = HKHubArchJITCreate(CC_STD_ALLOCATOR, Graph, 0);
    HKHubArchExecutionGraphDestroy(Graph);
    
    HKHubArchProcessorSetCycles(Processor, 5);
    
    for (size_t PrevCycles = 0; PrevCycles != Processor->cycles; )
    {
        PrevCycles = Processor->cycles;
        HKHubArchJITCall(JIT, Processor);
    }
    
    XCTAssertEqual(Processor->state.pc, 4, "Should have the correct value");
    XCTAssertEqual(Processor->cycles, 1, "Should have the correct value");
    
    
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 5);
    HKHubArchJITInvalidateBlocks(JIT, 1, 2);
    
    for (size_t PrevCycles = 0; PrevCycles != Processor->cycles; )
    {
        PrevCycles = Processor->cycles;
        HKHubArchJITCall(JIT, Processor);
    }
    
    XCTAssertEqual(Processor->state.pc, 1, "Should have the correct value");
    XCTAssertEqual(Processor->cycles, 4, "Should have the correct value");
    
    
    Processor->state.pc = 2;
    HKHubArchProcessorSetCycles(Processor, 5);
    
    for (size_t PrevCycles = 0; PrevCycles != Processor->cycles; )
    {
        PrevCycles = Processor->cycles;
        HKHubArchJITCall(JIT, Processor);
    }
    
    XCTAssertEqual(Processor->state.pc, 2, "Should have the correct value");
    XCTAssertEqual(Processor->cycles, 5, "Should have the correct value");
    
    
    Processor->state.pc = 3;
    HKHubArchProcessorSetCycles(Processor, 5);
    
    for (size_t PrevCycles = 0; PrevCycles != Processor->cycles; )
    {
        PrevCycles = Processor->cycles;
        HKHubArchJITCall(JIT, Processor);
    }
    
    XCTAssertEqual(Processor->state.pc, 4, "Should have the correct value");
    XCTAssertEqual(Processor->cycles, 4, "Should have the correct value");
    
    HKHubArchJITDestroy(JIT);
    
    HKHubArchProcessorDestroy(Processor);
}

-(void) testPartialInvalidation
{
    const char *Source =
        "mov r1, 1\n"
        "add r1, 2\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchExecutionGraph Graph = HKHubArchExecutionGraphCreate(CC_STD_ALLOCATOR, Binary->data, Binary->entrypoint);
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchJIT JIT = HKHubArchJITCreate(CC_STD_ALLOCATOR, Graph, 0);
    HKHubArchExecutionGraphDestroy(Graph);
    
    HKHubArchProcessorSetCycles(Processor, 100);
    
    for (size_t PrevCycles = 0; PrevCycles != Processor->cycles; )
    {
        PrevCycles = Processor->cycles;
        HKHubArchJITCall(JIT, Processor);
    }
    
    XCTAssertEqual(Processor->state.r[1], 3, "Should have the correct value");
    XCTAssertEqual(Processor->state.pc, 6, "Should have the correct value");
    XCTAssertEqual(Processor->cycles, 91, "Should have the correct value");
    
    
    Processor->state.r[1] = 0;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 5);
    HKHubArchJITInvalidateBlocks(JIT, 1, 1);
    
    for (size_t PrevCycles = 0; PrevCycles != Processor->cycles; )
    {
        PrevCycles = Processor->cycles;
        HKHubArchJITCall(JIT, Processor);
    }
    
    XCTAssertEqual(Processor->state.pc, 0, "Should have the correct value");
    XCTAssertEqual(Processor->cycles, 5, "Should have the correct value");
    
    
    Processor->state.pc = 3;
    HKHubArchProcessorSetCycles(Processor, 100);
    
    for (size_t PrevCycles = 0; PrevCycles != Processor->cycles; )
    {
        PrevCycles = Processor->cycles;
        HKHubArchJITCall(JIT, Processor);
    }
    
    XCTAssertEqual(Processor->state.r[1], 2, "Should have the correct value");
    XCTAssertEqual(Processor->state.pc, 6, "Should have the correct value");
    XCTAssertEqual(Processor->cycles, 95, "Should have the correct value");
    
    HKHubArchJITDestroy(JIT);
    
    HKHubArchProcessorDestroy(Processor);
}

-(void) testAutoInvalidation
{
    const char *Source =
        "mov r0, 5\n"
        "or [Modify], 4 << 2\n"
        "Modify:\n"
        "add r0, 1\n"
        "add r0, 2\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchExecutionGraph Graph = HKHubArchExecutionGraphCreate(CC_STD_ALLOCATOR, Binary->data, Binary->entrypoint);
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    
    HKHubArchJIT JIT = HKHubArchJITCreate(CC_STD_ALLOCATOR, Graph, 0);
    
    HKHubArchProcessorSetCycles(Processor, 100);
    
    for (size_t PrevCycles = 0; PrevCycles != Processor->cycles; )
    {
        PrevCycles = Processor->cycles;
        HKHubArchJITCall(JIT, Processor);
    }
    
    XCTAssertEqual(Processor->state.pc, 13, "Should have the correct value");
    XCTAssertEqual(Processor->cycles, 79, "Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 8, "Should have the correct value");
    
    HKHubArchJITDestroy(JIT);
    
    
    JIT = HKHubArchJITCreate(CC_STD_ALLOCATOR, Graph, 0);
    
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 100);
    
    for (size_t PrevCycles = 0; PrevCycles != Processor->cycles; )
    {
        PrevCycles = Processor->cycles;
        HKHubArchJITCall(JIT, Processor);
    }
    
    XCTAssertEqual(Processor->state.pc, 13, "Should have the correct value");
    XCTAssertEqual(Processor->cycles, 79, "Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 8, "Should have the correct value");
    
    HKHubArchJITDestroy(JIT);
    
    
    JIT = HKHubArchJITCreate(CC_STD_ALLOCATOR, Graph, HKHubArchJITOptionsWatchMemory);
    
    Processor->cache.jit = JIT;
    Processor->state.pc = 0;
    HKHubArchProcessorSetCycles(Processor, 100);
    
    for (size_t PrevCycles = 0; PrevCycles != Processor->cycles; )
    {
        PrevCycles = Processor->cycles;
        HKHubArchJITCall(JIT, Processor);
    }
    
    XCTAssertEqual(Processor->state.pc, 7, "Should have the correct value");
    XCTAssertEqual(Processor->cycles, 89, "Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 5, "Should have the correct value");
    
    HKHubArchProcessorSetDebugMode(Processor, HKHubArchProcessorDebugModePause);
    HKHubArchProcessorStep(Processor, 1);
    HKHubArchProcessorRun(Processor);
    HKHubArchProcessorSetDebugMode(Processor, HKHubArchProcessorDebugModeContinue);
    
    XCTAssertEqual(Processor->state.pc, 10, "Should have the correct value");
    XCTAssertEqual(Processor->cycles, 84, "Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 4, "Should have the correct value");
    
    for (size_t PrevCycles = 0; PrevCycles != Processor->cycles; )
    {
        PrevCycles = Processor->cycles;
        HKHubArchJITCall(JIT, Processor);
    }
    
    XCTAssertEqual(Processor->state.pc, 13, "Should have the correct value");
    XCTAssertEqual(Processor->cycles, 79, "Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 6, "Should have the correct value");
    
    Processor->cache.jit = NULL;
    HKHubArchJITDestroy(JIT);
    
    HKHubArchExecutionGraphDestroy(Graph);
    
    HKHubArchProcessorDestroy(Processor);
    
    
    Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchProcessorCache(Processor, 0);
    HKHubArchProcessorSetCycles(Processor, 100);
    HKHubArchProcessorRun(Processor);
    
    XCTAssertEqual(Processor->state.pc, 13, "Should have the correct value");
    XCTAssertEqual(Processor->cycles, 78, "Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 8, "Should have the correct value");
    
    HKHubArchProcessorDestroy(Processor);
    
    
    Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchProcessorCache(Processor, HKHubArchJITOptionsWatchMemory);
    HKHubArchProcessorSetCycles(Processor, 100);
    HKHubArchProcessorRun(Processor);
    
    XCTAssertEqual(Processor->state.pc, 13, "Should have the correct value");
    XCTAssertEqual(Processor->cycles, 78, "Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 6, "Should have the correct value");
    
    HKHubArchProcessorDestroy(Processor);
    
    
    Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchProcessorCache(Processor, HKHubArchJITOptionsWatchMemory | HKHubArchJITOptionsCache);
    HKHubArchProcessorSetCycles(Processor, 100);
    HKHubArchProcessorRun(Processor);
    
    XCTAssertEqual(Processor->state.pc, 13, "Should have the correct value");
    XCTAssertEqual(Processor->cycles, 78, "Should have the correct value");
    XCTAssertEqual(Processor->state.r[0], 6, "Should have the correct value");
    
    HKHubArchProcessorDestroy(Processor);
    HKHubArchBinaryDestroy(Binary);
}

@end
