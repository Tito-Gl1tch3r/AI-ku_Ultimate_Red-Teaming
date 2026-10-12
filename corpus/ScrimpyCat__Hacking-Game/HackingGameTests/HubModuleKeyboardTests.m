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

#import <XCTest/XCTest.h>
#import "HubArchProcessor.h"
#import "HubArchAssembly.h"
#import "HubModuleKeyboard.h"

#define HKHubArchAssemblyPrintError(err) if (Errors) { HKHubArchAssemblyPrintError(err); CCCollectionDestroy(err); err = NULL; }

@interface HubModuleKeyboardTests : XCTestCase

@end

@implementation HubModuleKeyboardTests


-(void) testBufferingInput
{
    const char *Source =
        ".define keyboard, 0\n"
        "data: .byte 0, 0, 0, 0, 0\n"
        ".entrypoint\n"
        "repeat:\n"
        "recv keyboard, [data+r0]\n"
        "jz repeat\n"
        "add r0, 1\n"
        "jmp repeat\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubModule Keyboard = HKHubModuleKeyboardCreate(CC_STD_ALLOCATOR);
    
    HKHubArchPortConnection Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(Processor, 0), HKHubModuleGetPort(Keyboard, 0));
    
    HKHubArchProcessorConnect(Processor, 0, Conn);
    HKHubModuleConnect(Keyboard, 0, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    
    HKHubArchProcessorSetCycles(Processor, 50);
    HKHubArchProcessorRun(Processor);
    
    
    XCTAssertEqual(Processor->memory[0], 0, @"Should not receive any input");
    XCTAssertEqual(Processor->memory[1], 0, @"Should not receive any input");
    XCTAssertEqual(Processor->memory[2], 0, @"Should not receive any input");
    XCTAssertEqual(Processor->memory[3], 0, @"Should not receive any input");
    XCTAssertEqual(Processor->memory[4], 0, @"Should not receive any input");
    XCTAssertEqual(Processor->state.r[0], 0, @"Should not receive any input");
    
    HKHubModuleKeyboardEnterKey(Keyboard, 1);
    HKHubModuleKeyboardEnterKey(Keyboard, 2);
    HKHubArchProcessorSetCycles(Processor, 50);
    HKHubArchProcessorRun(Processor);
    
    XCTAssertEqual(Processor->memory[0], 1, @"Should receive input");
    XCTAssertEqual(Processor->memory[1], 2, @"Should receive input");
    XCTAssertEqual(Processor->memory[2], 0, @"Should not receive any input");
    XCTAssertEqual(Processor->memory[3], 0, @"Should not receive any input");
    XCTAssertEqual(Processor->memory[4], 0, @"Should not receive any input");
    XCTAssertEqual(Processor->state.r[0], 2, @"Should receive 2 inputs");
    
    HKHubModuleKeyboardEnterKey(Keyboard, 3);
    HKHubArchProcessorSetCycles(Processor, 50);
    HKHubArchProcessorRun(Processor);
    
    XCTAssertEqual(Processor->memory[0], 1, @"Should receive input");
    XCTAssertEqual(Processor->memory[1], 2, @"Should receive input");
    XCTAssertEqual(Processor->memory[2], 3, @"Should not receive any input");
    XCTAssertEqual(Processor->memory[3], 0, @"Should not receive any input");
    XCTAssertEqual(Processor->memory[4], 0, @"Should not receive any input");
    XCTAssertEqual(Processor->state.r[0], 3, @"Should receive 1 more inputs");
    
    
    HKHubModuleKeyboardEnterKey(Keyboard, 4);
    HKHubModuleKeyboardEnterKey(Keyboard, 5);
    
    CCData Memory = HKHubModuleGetMemory(Keyboard);
    XCTAssertEqual(CCDataGetSize(Memory), 2, @"Should be the correct size");
    
    uint8_t RawKeys[2];
    CCDataReadBuffer(Memory, 0, sizeof(RawKeys), RawKeys);
    XCTAssertEqual(RawKeys[0], 4, @"Should be the correct raw pixel");
    XCTAssertEqual(RawKeys[1], 5, @"Should be the correct raw pixel");
    CCDataWriteBuffer(Memory, 0, 2, (uint8_t[2]){ 0xff, 0xfe });
    
    HKHubArchProcessorSetCycles(Processor, 50);
    HKHubArchProcessorRun(Processor);
    
    XCTAssertEqual(Processor->memory[0], 1, @"Should receive input");
    XCTAssertEqual(Processor->memory[1], 2, @"Should receive input");
    XCTAssertEqual(Processor->memory[2], 3, @"Should not receive any input");
    XCTAssertEqual(Processor->memory[3], 0xff, @"Should not receive any input");
    XCTAssertEqual(Processor->memory[4], 0xfe, @"Should not receive any input");
    XCTAssertEqual(Processor->state.r[0], 5, @"Should receive 2 more inputs");
    
    
    HKHubModuleDestroy(Keyboard);
}

@end
