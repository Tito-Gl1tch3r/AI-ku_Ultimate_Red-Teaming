/*
 *  Copyright (c) 2021, Stefan Johnson
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
#import "HubModuleDebugController.h"
#import "HubModuleKeyboard.h"

#define HKHubArchAssemblyPrintError(err) if (Errors) { HKHubArchAssemblyPrintError(err); CCCollectionDestroy(err); err = NULL; }

@interface HubModuleDebugController : XCTestCase

@end

@implementation HubModuleDebugController

-(void) testQueryAPI
{
    HKHubArchScheduler Scheduler = HKHubArchSchedulerCreate(CC_STD_ALLOCATOR);
    HKHubModule DebugController = HKHubModuleDebugControllerCreate(CC_STD_ALLOCATOR);
    
    const char *Source =
        "loop:\n"
        "add r0, 1\n"
        "jmp loop\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor TempProcessor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubModuleDebugControllerConnectProcessor(DebugController, TempProcessor, 0);
    HKHubArchSchedulerAddProcessor(Scheduler, TempProcessor);
    
    for (int Loop = 1; Loop < 5; Loop++)
    {
        Binary->data[2] += Loop;
        
        HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
        
        HKHubModuleDebugControllerConnectProcessor(DebugController, Processor, 0);
        
        HKHubArchSchedulerAddProcessor(Scheduler, Processor);
        HKHubArchProcessorDestroy(Processor);
    }
    
    HKHubArchBinaryDestroy(Binary);
    
    HKHubModule Keyboard = HKHubModuleKeyboardCreate(CC_STD_ALLOCATOR);
    HKHubModuleDebugControllerConnectModule(DebugController, Keyboard, CC_STRING("keyboard"));
    HKHubModuleKeyboardEnterKey(Keyboard, 1);
    HKHubModuleKeyboardEnterKey(Keyboard, 2);
    HKHubModuleKeyboardEnterKey(Keyboard, 3);
    HKHubModuleKeyboardEnterKey(Keyboard, 4);
    for (int Loop = 0; Loop < 251; Loop++) HKHubModuleKeyboardEnterKey(Keyboard, 0);
    HKHubModuleKeyboardEnterKey(Keyboard, 5);
    HKHubModuleKeyboardEnterKey(Keyboard, 6);
    HKHubModuleKeyboardEnterKey(Keyboard, 7);
    HKHubModuleKeyboardEnterKey(Keyboard, 8);
    HKHubModuleKeyboardEnterKey(Keyboard, 9);
    
     //[0:4] device count (count:16)
    Source =
        "device_count:\n"
        ".byte -1, -1\n"
        "device_count_query:\n"
        ".byte 0\n"
        ".entrypoint\n"
        "send r0, 1, [device_count_query]\n"
        "recv r0, [device_count]\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchPortConnection Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(Processor, 0), HKHubModuleGetPort(DebugController, HK_HUB_MODULE_DEBUG_CONTROLLER_QUERY_PORT | 0));
    
    HKHubArchProcessorConnect(Processor, 0, Conn);
    HKHubModuleConnect(DebugController, HK_HUB_MODULE_DEBUG_CONTROLLER_QUERY_PORT | 0, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    HKHubArchSchedulerAddProcessor(Scheduler, Processor);
    
    HKHubArchSchedulerRun(Scheduler, 10.0);
    
    //device_count
    XCTAssertEqual(Processor->memory[0], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[1], 6, @"Should be the correct value");
    
    
    //[1:4] [device:12] memory size (size:16)
    Source =
        "proc_memory_size:\n"
        ".byte -1, -2\n"
        "mod_memory_size:\n"
        ".byte -1, -2\n"
        "null_memory_size:\n"
        ".byte -1, -2\n"
        "proc_memory_size_query:\n"
        ".byte (1 << 4) | 0, 0\n"
        "mod_memory_size_query:\n"
        ".byte (1 << 4) | 0, 5\n"
        "null_memory_size_query:\n"
        ".byte (1 << 4) | 0xf, 0xff\n"
        ".entrypoint\n"
        "send r0, 2, [proc_memory_size_query]\n"
        "recv r0, [proc_memory_size]\n"
        "send r0, 2, [mod_memory_size_query]\n"
        "recv r0, [mod_memory_size]\n"
        "send r0, 2, [null_memory_size_query]\n"
        "recv r0, [null_memory_size]\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchSchedulerRun(Scheduler, 10.0);
    
    //proc_memory_size
    XCTAssertEqual(Processor->memory[0], 1, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[1], 0, @"Should be the correct value");
    //mod_memory_size
    XCTAssertEqual(Processor->memory[2], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[3], 0xff, @"Should be the correct value");
    //null_memory_size
    XCTAssertEqual(Processor->memory[4], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[5], 0xfe, @"Should be the correct value");
    
    
    //[2:4] [device:12] read memory [offset:8] [size:8] ... (bytes:sum sizes)
    Source =
        "proc_read_memory:\n"
        ".byte -1, -2, -3, -4\n"
        "mod_read_memory:\n"
        ".byte -1, -2, -3, -4\n"
        "null_read_memory:\n"
        ".byte -1, -2, -3, -4\n"
        "split_proc_read_memory:\n"
        ".byte -1, -2, -3, -4\n"
        "split_mod_read_memory:\n"
        ".byte -1, -2, -3, -4\n"
        "proc_read_memory_query:\n"
        ".byte (2 << 4) | 0, 0, 0, 4\n"
        "mod_read_memory_query:\n"
        ".byte (2 << 4) | 0, 5, 0, 4\n"
        "null_read_memory_query:\n"
        ".byte (2 << 4) | 0, 0xff, 0, 4\n"
        "split_proc_read_memory_query:\n"
        ".byte (2 << 4) | 0, 0, 1, 1, 2, 0, 0xff, 3\n"
        "split_mod_read_memory_query:\n"
        ".byte (2 << 4) | 0, 5, 1, 1, 2, 0, 0xff, 3\n"
        ".entrypoint\n"
        "send r0, 4, [proc_read_memory_query]\n"
        "recv r0, [proc_read_memory]\n"
        "send r0, 4, [mod_read_memory_query]\n"
        "recv r0, [mod_read_memory]\n"
        "send r0, 4, [null_read_memory_query]\n"
        "recv r0, [null_read_memory]\n"
        "send r0, 8, [split_proc_read_memory_query]\n"
        "recv r0, [split_proc_read_memory]\n"
        "send r0, 8, [split_mod_read_memory_query]\n"
        "recv r0, [split_mod_read_memory]\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchSchedulerRun(Scheduler, 10.0);
    
    //proc_read_memory
    XCTAssertEqual(Processor->memory[0], TempProcessor->memory[0], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[1], TempProcessor->memory[1], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[2], TempProcessor->memory[2], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[3], TempProcessor->memory[3], @"Should be the correct value");
    //mod_read_memory
    XCTAssertEqual(Processor->memory[4], 1, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[5], 2, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[6], 3, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[7], 4, @"Should be the correct value");
    //null_read_memory
    XCTAssertEqual(Processor->memory[8], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[9], 0xfe, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[10], 0xfd, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[11], 0xfc, @"Should be the correct value");
    //split_proc_read_memory
    XCTAssertEqual(Processor->memory[12], TempProcessor->memory[1], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[13], TempProcessor->memory[255], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[14], TempProcessor->memory[0], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[15], TempProcessor->memory[1], @"Should be the correct value");
    //split_mod_read_memory
    XCTAssertEqual(Processor->memory[16], 2, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[17], 5, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[18], 6, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[19], 7, @"Should be the correct value");
    
    
    //[3:4] [device:12] read memory [offset:16] [size:8] ... (bytes:sum sizes)
    Source =
        "proc_read_memory16:\n"
        ".byte -1, -2, -3, -4\n"
        "mod_read_memory16:\n"
        ".byte -1, -2, -3, -4\n"
        "null_read_memory16:\n"
        ".byte -1, -2, -3, -4\n"
        "split_proc_read_memory16:\n"
        ".byte -1, -2, -3, -4\n"
        "split_mod_read_memory16:\n"
        ".byte -1, -2, -3, -4\n"
        "proc_read_memory_query16:\n"
        ".byte (3 << 4) | 0, 0, 1, 0, 4\n"
        "mod_read_memory_query16:\n"
        ".byte (3 << 4) | 0, 5, 1, 0, 4\n"
        "null_read_memory_query16:\n"
        ".byte (3 << 4) | 0, 0xff, 0, 0, 4\n"
        "split_proc_read_memory_query16:\n"
        ".byte (3 << 4) | 0, 0, 1, 1, 1, 0, 2, 0, 0, 0xff, 3\n"
        "split_mod_read_memory_query16:\n"
        ".byte (3 << 4) | 0, 5, 0, 1, 1, 0, 2, 0, 1, 0, 3\n"
        ".entrypoint\n"
        "send r0, 5, [proc_read_memory_query16]\n"
        "recv r0, [proc_read_memory16]\n"
        "send r0, 5, [mod_read_memory_query16]\n"
        "recv r0, [mod_read_memory16]\n"
        "send r0, 5, [null_read_memory_query16]\n"
        "recv r0, [null_read_memory16]\n"
        "send r0, 11, [split_proc_read_memory_query16]\n"
        "recv r0, [split_proc_read_memory16]\n"
        "send r0, 11, [split_mod_read_memory_query16]\n"
        "recv r0, [split_mod_read_memory16]\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchSchedulerRun(Scheduler, 10.0);
    
    //proc_read_memory16
    XCTAssertEqual(Processor->memory[0], TempProcessor->memory[0], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[1], TempProcessor->memory[1], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[2], TempProcessor->memory[2], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[3], TempProcessor->memory[3], @"Should be the correct value");
    //mod_read_memory16
    XCTAssertEqual(Processor->memory[4], 6, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[5], 7, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[6], 8, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[7], 9, @"Should be the correct value");
    //null_read_memory16
    XCTAssertEqual(Processor->memory[8], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[9], 0xfe, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[10], 0xfd, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[11], 0xfc, @"Should be the correct value");
    //split_proc_read_memory16
    XCTAssertEqual(Processor->memory[12], TempProcessor->memory[1], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[13], TempProcessor->memory[255], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[14], TempProcessor->memory[0], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[15], TempProcessor->memory[1], @"Should be the correct value");
    //split_mod_read_memory16
    XCTAssertEqual(Processor->memory[16], 2, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[17], 6, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[18], 7, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[19], 8, @"Should be the correct value");
    
    
    //[4:4] [device:12] read registers [_:2, r0:1?, r1:1?, r2:1?, r3:1?, flags:1?, pc:1?, defaults to 0x3f] (r0:8?, r1:8?, r2:8?, r3:8?, flags:8?, pc:8?)
    Source =
        "proc_all_regs:\n"
        ".byte -1, -2, -3, -4, -5, -6\n"
        "mod_all_regs:\n"
        ".byte -1, -2, -3, -4, -5, -6\n"
        "null_all_regs:\n"
        ".byte -1, -2, -3, -4, -5, -6\n"
        "proc_r0_and_pc:\n"
        ".byte -1, -2\n"
        "mod_r0_and_pc:\n"
        ".byte -1, -2\n"
        "null_r0_and_pc:\n"
        ".byte -1, -2\n"
        "proc_all_regs_query:\n"
        ".byte (4 << 4) | 0, 0\n"
        "mod_all_regs_query:\n"
        ".byte (4 << 4) | 0, 5\n"
        "null_all_regs_query:\n"
        ".byte (4 << 4) | 0, 0xff\n"
        "proc_r0_and_pc_query:\n"
        ".byte (4 << 4) | 0, 0, (1 << 5) | 1 \n"
        "mod_r0_and_pc_query:\n"
        ".byte (4 << 4) | 0, 5, (1 << 5) | 1 \n"
        "null_r0_and_pc_query:\n"
        ".byte (4 << 4) | 0, 0xff, (1 << 5) | 1 \n"
        ".entrypoint\n"
        "send r0, 2, [proc_all_regs_query]\n"
        "recv r0, [proc_all_regs]\n"
        "send r0, 2, [mod_all_regs_query]\n"
        "recv r0, [mod_all_regs]\n"
        "send r0, 2, [null_all_regs_query]\n"
        "recv r0, [null_all_regs]\n"
        "send r0, 4, [proc_r0_and_pc_query]\n"
        "recv r0, [proc_r0_and_pc]\n"
        "send r0, 4, [mod_r0_and_pc_query]\n"
        "recv r0, [mod_r0_and_pc]\n"
        "send r0, 4, [null_r0_and_pc_query]\n"
        "recv r0, [null_r0_and_pc]\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    TempProcessor->state.r[0] = 1;
    TempProcessor->state.r[1] = 2;
    TempProcessor->state.r[2] = 3;
    TempProcessor->state.r[3] = 4;
    TempProcessor->state.flags = 5;
    TempProcessor->state.pc = 6;
    
    HKHubArchSchedulerRun(Scheduler, 10.0);
    
    //proc_all_regs
    XCTAssertEqual(Processor->memory[0], TempProcessor->state.r[0], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[1], TempProcessor->state.r[1], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[2], TempProcessor->state.r[2], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[3], TempProcessor->state.r[3], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[4], TempProcessor->state.flags, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[5], TempProcessor->state.pc, @"Should be the correct value");
    //mod_all_regs
    XCTAssertEqual(Processor->memory[6], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[7], 0xfe, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[8], 0xfd, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[9], 0xfc, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[10], 0xfb, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[11], 0xfa, @"Should be the correct value");
    //null_all_regs
    XCTAssertEqual(Processor->memory[12], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[13], 0xfe, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[14], 0xfd, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[15], 0xfc, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[16], 0xfb, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[17], 0xfa, @"Should be the correct value");
    //proc_r0_and_pc
    XCTAssertEqual(Processor->memory[18], TempProcessor->state.r[0], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[19], TempProcessor->state.pc, @"Should be the correct value");
    //mod_r0_and_pc
    XCTAssertEqual(Processor->memory[20], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[21], 0xfe, @"Should be the correct value");
    //null_r0_and_pc
    XCTAssertEqual(Processor->memory[22], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[23], 0xfe, @"Should be the correct value");
    
    TempProcessor->state.r[0] = 0;
    TempProcessor->state.r[1] = 0;
    TempProcessor->state.r[2] = 0;
    TempProcessor->state.r[3] = 0;
    TempProcessor->state.flags = 0;
    TempProcessor->state.pc = 0;
    
    
    //[5:4] [device:12] read breakpoints [offset:8? ... defaults to every offset] (r:1 ..., w:1 ...)
    Source =
        "proc_all_brks:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        "mod_all_brks:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        "null_all_brks:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        "proc_0_and_2:\n"
        ".byte -1\n"
        "mod_0_and_2:\n"
        ".byte -1\n"
        "null_0_and_2:\n"
        ".byte -1\n"
        "proc_all_brks_query:\n"
        ".byte (5 << 4) | 0, 0\n"
        "mod_all_brks_query:\n"
        ".byte (5 << 4) | 0, 5\n"
        "null_all_brks_query:\n"
        ".byte (5 << 4) | 0, 0xff\n"
        "proc_0_and_2_query:\n"
        ".byte (5 << 4) | 0, 0, 0, 2 \n"
        "mod_0_and_2_query:\n"
        ".byte (5 << 4) | 0, 5, 0, 2 \n"
        "null_0_and_2_query:\n"
        ".byte (5 << 4) | 0, 0xff, 0, 2 \n"
        ".entrypoint\n"
        "send r0, 2, [proc_all_brks_query]\n"
        "recv r0, [proc_all_brks]\n"
        "send r0, 2, [mod_all_brks_query]\n"
        "recv r0, [mod_all_brks]\n"
        "send r0, 2, [null_all_brks_query]\n"
        "recv r0, [null_all_brks]\n"
        "send r0, 4, [proc_0_and_2_query]\n"
        "recv r0, [proc_0_and_2]\n"
        "send r0, 4, [mod_0_and_2_query]\n"
        "recv r0, [mod_0_and_2]\n"
        "send r0, 4, [null_0_and_2_query]\n"
        "recv r0, [null_0_and_2]\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    
    HKHubArchSchedulerRun(Scheduler, 10.0);
    
    //proc_all_brks
    for (int Loop = 0; Loop < 4; Loop++)
    {
        for (int Loop2 = 0; Loop2 < 16; Loop2++)
        {
            XCTAssertEqual(Processor->memory[(Loop * 16) + Loop2], 0, @"Should be the correct value");
        }
    }
    //mod_all_brks
    for (int Loop = 4; Loop < 8; Loop++)
    {
        for (int Loop2 = 0; Loop2 < 16; Loop2++)
        {
            XCTAssertEqual(Processor->memory[(Loop * 16) + Loop2], (uint8_t)-(Loop2 + 1), @"Should be the correct value");
        }
    }
    //null_all_brks
    for (int Loop = 8; Loop < 12; Loop++)
    {
        for (int Loop2 = 0; Loop2 < 16; Loop2++)
        {
            XCTAssertEqual(Processor->memory[(Loop * 16) + Loop2], (uint8_t)-(Loop2 + 1), @"Should be the correct value");
        }
    }
    //proc_0_and_2
    XCTAssertEqual(Processor->memory[192], 0, @"Should be the correct value");
    //mod_0_and_2
    XCTAssertEqual(Processor->memory[193], 0xff, @"Should be the correct value");
    //null_0_and_2
    XCTAssertEqual(Processor->memory[194], 0xff, @"Should be the correct value");
    
    HKHubArchProcessorSetBreakpoint(TempProcessor, HKHubArchProcessorDebugBreakpointRead, 0);
    HKHubArchProcessorSetBreakpoint(TempProcessor, HKHubArchProcessorDebugBreakpointWrite | HKHubArchProcessorDebugBreakpointRead, 2);
    HKHubArchProcessorSetBreakpoint(TempProcessor, HKHubArchProcessorDebugBreakpointRead, 255);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchSchedulerRun(Scheduler, 10.0);
    
    //proc_all_brks
    XCTAssertEqual(Processor->memory[0], 76, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[63], 1, @"Should be the correct value");
    //proc_0_and_2
    XCTAssertEqual(Processor->memory[192], 112, @"Should be the correct value");
    
    HKHubArchProcessorClearBreakpoints(TempProcessor);
    
    //[6:4] [device:12] read ports (256 bits)
    //[6:4] [device:12] read ports [port:8 ...] (receiving port:8, connected:1, _:3, device:12)
    Source =
        "proc_all_ports:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        "mod_all_ports:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        "null_all_ports:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        "proc_0_and_2:\n"
        ".byte -1, -2, -3, -4, -5, -6\n"
        "mod_0_and_2:\n"
        ".byte -1, -2, -3, -4, -5, -6\n"
        "null_0_and_2:\n"
        ".byte -1, -2, -3, -4, -5, -6\n"
        "proc_all_ports_query:\n"
        ".byte (6 << 4) | 0, 0\n"
        "mod_all_ports_query:\n"
        ".byte (6 << 4) | 0, 5\n"
        "null_all_ports_query:\n"
        ".byte (6 << 4) | 0, 0xff\n"
        "proc_0_and_2_query:\n"
        ".byte (6 << 4) | 0, 0, 0, 2 \n"
        "mod_0_and_2_query:\n"
        ".byte (6 << 4) | 0, 5, 0, 2 \n"
        "null_0_and_2_query:\n"
        ".byte (6 << 4) | 0, 0xff, 0, 2 \n"
        ".entrypoint\n"
        "send r0, 2, [proc_all_ports_query]\n"
        "recv r0, [proc_all_ports]\n"
        "send r0, 2, [mod_all_ports_query]\n"
        "recv r0, [mod_all_ports]\n"
        "send r0, 2, [null_all_ports_query]\n"
        "recv r0, [null_all_ports]\n"
        "send r0, 4, [proc_0_and_2_query]\n"
        "recv r0, [proc_0_and_2]\n"
        "send r0, 4, [mod_0_and_2_query]\n"
        "recv r0, [mod_0_and_2]\n"
        "send r0, 4, [null_0_and_2_query]\n"
        "recv r0, [null_0_and_2]\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    
    HKHubArchSchedulerRun(Scheduler, 10.0);
    
    //proc_all_ports
    for (int Loop = 0; Loop < 2; Loop++)
    {
        for (int Loop2 = 0; Loop2 < 16; Loop2++)
        {
            XCTAssertEqual(Processor->memory[(Loop * 16) + Loop2], 0, @"Should be the correct value");
        }
    }
    //mod_all_ports
    for (int Loop = 2; Loop < 4; Loop++)
    {
        for (int Loop2 = 0; Loop2 < 16; Loop2++)
        {
            XCTAssertEqual(Processor->memory[(Loop * 16) + Loop2], (uint8_t)-(Loop2 + 1), @"Should be the correct value");
        }
    }
    //null_all_ports
    for (int Loop = 4; Loop < 6; Loop++)
    {
        for (int Loop2 = 0; Loop2 < 16; Loop2++)
        {
            XCTAssertEqual(Processor->memory[(Loop * 16) + Loop2], (uint8_t)-(Loop2 + 1), @"Should be the correct value");
        }
    }
    //proc_0_and_2
    XCTAssertEqual(Processor->memory[96], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[97], 0xf, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[98], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[99], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[100], 0xf, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[101], 0xff, @"Should be the correct value");
    //mod_0_and_2
    XCTAssertEqual(Processor->memory[102], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[103], 0xfe, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[104], 0xfd, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[105], 0xfc, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[106], 0xfb, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[107], 0xfa, @"Should be the correct value");
    //null_0_and_2
    XCTAssertEqual(Processor->memory[108], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[109], 0xfe, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[110], 0xfd, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[111], 0xfc, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[112], 0xfb, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[113], 0xfa, @"Should be the correct value");
    
    Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(Processor, 1), HKHubArchProcessorGetPort(TempProcessor, 0));
    
    HKHubArchProcessorConnect(Processor, 1, Conn);
    HKHubArchProcessorConnect(TempProcessor, 0, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubModuleGetPort(Keyboard, 29), HKHubArchProcessorGetPort(TempProcessor, 2));
    
    HKHubModuleConnect(Keyboard, 29, Conn);
    HKHubArchProcessorConnect(TempProcessor, 2, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchSchedulerRun(Scheduler, 10.0);
    
    //proc_all_ports
    XCTAssertEqual(Processor->memory[0], 160, @"Should be the correct value");
    //proc_0_and_2
    XCTAssertEqual(Processor->memory[96], 1, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[97], 0x8f, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[98], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[99], 29, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[100], 0x80, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[101], 5, @"Should be the correct value");
    
    //[7:4] [device:12] toggle break [offset:8] [_:6] [wr:2] ... (xors wr)
    //[8:4] [device:12] pause
    //[9:4] [device:12] continue
    //[a:4] [device:12] step [count:8?]
    //[a:4] [device:12] step [count:16?]
    //[b:4] [device:12] mode (_:7, paused/running: 1 bit)
    Source =
        "proc_r0:\n"
        ".byte -1\n"
        "proc_mode:\n"
        ".byte -1, -2\n"
        "mod_mode:\n"
        ".byte -1, -2\n"
        "null_mode:\n"
        ".byte -1, -2\n"
        "proc_r0_query:\n"
        ".byte (4 << 4) | 0, 0, 1 << 5\n"
        "proc_break:\n"
        ".byte (7 << 4) | 0, 0, 0, 1\n"
        "mod_break:\n"
        ".byte (7 << 4) | 0, 5, 0, 1\n"
        "null_break:\n"
        ".byte (7 << 4) | 0, 0xff, 0, 1\n"
        "proc_pause:\n"
        ".byte (8 << 4) | 0, 0\n"
        "mod_pause:\n"
        ".byte (8 << 4) | 0, 5\n"
        "null_pause:\n"
        ".byte (8 << 4) | 0, 0xff\n"
        "proc_continue:\n"
        ".byte (9 << 4) | 0, 0\n"
        "mod_continue:\n"
        ".byte (9 << 4) | 0, 5\n"
        "null_continue:\n"
        ".byte (9 << 4) | 0, 0xff\n"
        "proc_step1:\n"
        ".byte (10 << 4) | 0, 0\n"
        "mod_step1:\n"
        ".byte (10 << 4) | 0, 5\n"
        "null_step1:\n"
        ".byte (10 << 4) | 0, 0xff\n"
        "proc_step2:\n"
        ".byte (10 << 4) | 0, 0, 2\n"
        "mod_step2:\n"
        ".byte (10 << 4) | 0, 5, 2\n"
        "null_step2:\n"
        ".byte (10 << 4) | 0, 0xff, 2\n"
        "proc_step260:\n"
        ".byte (10 << 4) | 0, 0, 1, 4\n"
        "mod_step260:\n"
        ".byte (10 << 4) | 0, 5, 1, 4\n"
        "null_step260:\n"
        ".byte (10 << 4) | 0, 0xff, 1, 4\n"
        "proc_mode_query:\n"
        ".byte (11 << 4) | 0, 0\n"
        "mod_mode_query:\n"
        ".byte (11 << 4) | 0, 5\n"
        "null_mode_query:\n"
        ".byte (11 << 4) | 0, 0xff\n"
    
        ".entrypoint\n"
        "send r0, 2, [proc_step1]\n"
        "send r0, 2, [mod_step1]\n"
        "send r0, 2, [null_step1]\n"
        "hlt\n"
        "send r0, 3, [proc_step2]\n"
        "send r0, 3, [mod_step2]\n"
        "send r0, 3, [null_step2]\n"
        "hlt\n"
        "send r0, 4, [proc_step260]\n"
        "send r0, 4, [mod_step260]\n"
        "send r0, 4, [null_step260]\n"
        "hlt\n"
        "send r0, 4, [proc_break]\n"
        "send r0, 4, [mod_break]\n"
        "send r0, 4, [null_break]\n"
        "send r0, 2, [proc_continue]\n"
        "send r0, 2, [mod_continue]\n"
        "send r0, 2, [null_continue]\n"
        "hlt\n"
        "send r0, 4, [proc_break]\n"
        "send r0, 4, [mod_break]\n"
        "send r0, 4, [null_break]\n"
        "send r0, 3, [proc_r0_query]\n"
        "recv r0, [proc_r0]\n"
        "send r0, 2, [proc_continue]\n"
        "send r0, 2, [mod_continue]\n"
        "send r0, 2, [null_continue]\n"
        "hlt\n"
        "send r0, 2, [proc_mode_query]\n"
        "recv r0, [proc_mode]\n"
        "send r0, 2, [mod_mode_query]\n"
        "recv r0, [mod_mode]\n"
        "send r0, 2, [null_mode_query]\n"
        "recv r0, [null_mode]\n"
        "send r0, 2, [proc_pause]\n"
        "send r0, 2, [mod_pause]\n"
        "send r0, 2, [null_pause]\n"
        "send r0, 2, [proc_mode_query]\n"
        "recv r0, [proc_mode + 1]\n"
        "send r0, 2, [mod_mode_query]\n"
        "recv r0, [mod_mode + 1]\n"
        "send r0, 2, [null_mode_query]\n"
        "recv r0, [null_mode + 1]\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchSchedulerRun(Scheduler, 10.0); Processor->memory[Processor->state.pc] = 0xf8; Processor->status = HKHubArchProcessorStatusRunning;
    HKHubArchSchedulerRun(Scheduler, 10.0); Processor->memory[Processor->state.pc] = 0xf8; Processor->status = HKHubArchProcessorStatusRunning;
    HKHubArchSchedulerRun(Scheduler, 10.0); Processor->memory[Processor->state.pc] = 0xf8; Processor->status = HKHubArchProcessorStatusRunning;
    HKHubArchSchedulerRun(Scheduler, 10.0); Processor->memory[Processor->state.pc] = 0xf8; Processor->status = HKHubArchProcessorStatusRunning;
    HKHubArchSchedulerRun(Scheduler, 10.0); Processor->memory[Processor->state.pc] = 0xf8; Processor->status = HKHubArchProcessorStatusRunning;
    HKHubArchSchedulerRun(Scheduler, 10.0);
    
    //proc_r0
    XCTAssertEqual(Processor->memory[0], 132, @"Should be the correct value");
    //proc_mode:
    XCTAssertEqual(Processor->memory[1], HKHubArchProcessorDebugModePause, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[2], HKHubArchProcessorDebugModeContinue, @"Should be the correct value");
    //mod_mode:
    XCTAssertEqual(Processor->memory[3], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[4], 0xfe, @"Should be the correct value");
    //null_mode:
    XCTAssertEqual(Processor->memory[5], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[6], 0xfe, @"Should be the correct value");
    
    //[c:4] [device:12] name [size:8? defaults to 256] (string:256?)
    Source =
        "proc_short_name:\n"
        ".byte -1, -2, -3, -4\n"
        "mod_short_name:\n"
        ".byte -1, -2, -3, -4\n"
        "null_short_name:\n"
        ".byte -1, -2, -3, -4\n"
        "proc_name:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        "mod_name:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        "null_name:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14, -15, -16\n"
        "proc_name_query:\n"
        ".byte (12 << 4) | 0, 0\n"
        "mod_name_query:\n"
        ".byte (12 << 4) | 0, 5\n"
        "null_name_query:\n"
        ".byte (12 << 4) | 0, 0xff\n"
        "proc_short_name_query:\n"
        ".byte (12 << 4) | 0, 0, 3\n"
        "mod_short_name_query:\n"
        ".byte (12 << 4) | 0, 5, 3\n"
        "null_short_name_query:\n"
        ".byte (12 << 4) | 0, 0xff, 3\n"
        ".entrypoint\n"
        "send r0, 2, [proc_name_query]\n"
        "recv r0, [proc_name]\n"
        "send r0, 2, [mod_name_query]\n"
        "recv r0, [mod_name]\n"
        "send r0, 2, [null_name_query]\n"
        "recv r0, [null_name]\n"
        "send r0, 3, [proc_short_name_query]\n"
        "recv r0, [proc_short_name]\n"
        "send r0, 3, [mod_short_name_query]\n"
        "recv r0, [mod_short_name]\n"
        "send r0, 3, [null_short_name_query]\n"
        "recv r0, [null_short_name]\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchSchedulerRun(Scheduler, 10.0);
    
    //proc_short_name:
    XCTAssertEqual(Processor->memory[0], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[1], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[2], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[3], 0xfc, @"Should be the correct value");
    //mod_short_name:
    XCTAssertEqual(Processor->memory[4], 'k', @"Should be the correct value");
    XCTAssertEqual(Processor->memory[5], 'e', @"Should be the correct value");
    XCTAssertEqual(Processor->memory[6], 'y', @"Should be the correct value");
    XCTAssertEqual(Processor->memory[7], 0xfc, @"Should be the correct value");
    //null_short_name:
    XCTAssertEqual(Processor->memory[8], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[9], 0xfe, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[10], 0xfd, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[11], 0xfc, @"Should be the correct value");
    
    HKHubArchProcessorDestroy(TempProcessor);
    HKHubArchProcessorDestroy(Processor);
    HKHubModuleDestroy(Keyboard);
    HKHubModuleDestroy(DebugController);
    HKHubArchSchedulerDestroy(Scheduler);
}

-(void) testEventAPI
{
    HKHubArchScheduler Scheduler = HKHubArchSchedulerCreate(CC_STD_ALLOCATOR);
    HKHubModule DebugController = HKHubModuleDebugControllerCreate(CC_STD_ALLOCATOR);
    
    const char *Source =
        "loop:\n"
        "add r0, 1\n"
        "mov [0xff], r0\n"
        "jmp loop\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor TempProcessor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubModuleDebugControllerConnectProcessor(DebugController, TempProcessor, 0);
    HKHubArchSchedulerAddProcessor(Scheduler, TempProcessor);
    
    for (int Loop = 1; Loop < 5; Loop++)
    {
        Binary->data[2] += Loop;
        
        HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
        
        HKHubModuleDebugControllerConnectProcessor(DebugController, Processor, 0);
        
        HKHubArchSchedulerAddProcessor(Scheduler, Processor);
        HKHubArchProcessorDestroy(Processor);
    }
    
    HKHubArchBinaryDestroy(Binary);
    
    HKHubModule Keyboard = HKHubModuleKeyboardCreate(CC_STD_ALLOCATOR);
    HKHubModuleDebugControllerConnectModule(DebugController, Keyboard, CC_STRING("keyboard"));
    HKHubModuleKeyboardEnterKey(Keyboard, 1);
    HKHubModuleKeyboardEnterKey(Keyboard, 2);
    HKHubModuleKeyboardEnterKey(Keyboard, 3);
    HKHubModuleKeyboardEnterKey(Keyboard, 4);
    for (int Loop = 0; Loop < 251; Loop++) HKHubModuleKeyboardEnterKey(Keyboard, 0);
    HKHubModuleKeyboardEnterKey(Keyboard, 5);
    HKHubModuleKeyboardEnterKey(Keyboard, 6);
    HKHubModuleKeyboardEnterKey(Keyboard, 7);
    HKHubModuleKeyboardEnterKey(Keyboard, 8);
    HKHubModuleKeyboardEnterKey(Keyboard, 9);
    
    Source =
        "device_connected:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14\n"
        "op:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7\n"
        "modify:\n"
        ".byte -1, -2, -3\n"
        "mod_data:\n"
        ".byte -1, -2, -3\n"
        "modify2:\n"
        ".byte -1, -2, -3\n"
        "mod_data2:\n"
        ".byte -1, -2, -3\n"
        "modify3:\n"
        ".byte -1, -2, -3\n"
        "mod_data3:\n"
        ".byte -1, -2, -3\n"
        "op2:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7\n"
        "modify4:\n"
        ".byte -1, -2, -3, -4\n"
        "mod_data4:\n"
        ".byte -1, -2, -3\n"
        "modify5:\n"
        ".byte -1, -2, -3\n"
        "mod_data5:\n"
        ".byte -1, -2, -3\n"
        "op3:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7\n"
        "modify6:\n"
        ".byte -1, -2, -3\n"
        "mod_data6:\n"
        ".byte -1, -2, -3\n"
        "leftover:\n"
        ".byte -1, -2\n"
        ".entrypoint\n"
        "recv r0, [device_connected]\n"
        "recv r0, [device_connected + 2]\n"
        "recv r0, [device_connected + 4]\n"
        "recv r0, [device_connected + 6]\n"
        "recv r0, [device_connected + 8]\n"
        "recv r0, [device_connected + 10]\n"
        "recv r0, [device_connected + 12]\n"
        "hlt\n"
        "recv r0, [op]\n"
        "recv r0, [modify]\n"
        "recv r0, [mod_data]\n"
        "recv r0, [modify2]\n"
        "recv r0, [mod_data2]\n"
        "recv r0, [modify3]\n"
        "recv r0, [mod_data3]\n"
        "recv r0, [op2]\n"
        "recv r0, [modify4]\n"
        "recv r0, [mod_data4]\n"
        "recv r0, [modify5]\n"
        "recv r0, [mod_data5]\n"
        "recv r0, [op3]\n"
        "recv r0, [modify6]\n"
        "recv r0, [mod_data6]\n"
        "recv r0, [leftover]\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchPortConnection Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(Processor, 0), HKHubModuleGetPort(DebugController, 0));
    
    HKHubArchProcessorConnect(Processor, 0, Conn);
    HKHubModuleConnect(DebugController, 0, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    HKHubArchSchedulerAddProcessor(Scheduler, Processor);
    
    HKHubArchSchedulerRun(Scheduler, 10.0);
    HKHubArchProcessorStep(TempProcessor, 3);
    HKHubArchSchedulerRun(Scheduler, 10.0); Processor->memory[Processor->state.pc] = 0xf8; Processor->status = HKHubArchProcessorStatusRunning;
    HKHubArchSchedulerRun(Scheduler, 10.0);
    
    //device_connected
    XCTAssertEqual(Processor->memory[0], 0x80, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[1], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[2], 0x80, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[3], 1, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[4], 0x80, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[5], 2, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[6], 0x80, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[7], 3, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[8], 0x80, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[9], 4, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[10], 0x80, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[11], 5, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[12], 0xf3, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[13], 0xf2, @"Should be the correct value");
    
    //op
    XCTAssertEqual(Processor->memory[14], 0x40, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[15], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[16], TempProcessor->memory[0], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[17], TempProcessor->memory[1], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[18], TempProcessor->memory[2], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[19], 0xfa, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[20], 0xf9, @"Should be the correct value");
    //modify
    XCTAssertEqual(Processor->memory[21], 0x50, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[22], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[23], HKHubArchInstructionRegisterR0, @"Should be the correct value");
    //mod_data
    XCTAssertEqual(Processor->memory[24], 0x70, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[25], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[26], 1, @"Should be the correct value");
    //modify2
    XCTAssertEqual(Processor->memory[27], 0x50, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[28], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[29], HKHubArchInstructionRegisterFlags, @"Should be the correct value");
    //mod_data2
    XCTAssertEqual(Processor->memory[30], 0x70, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[31], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[32], 0, @"Should be the correct value");
    //modify3
    XCTAssertEqual(Processor->memory[33], 0x50, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[34], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[35], HKHubArchInstructionRegisterPC, @"Should be the correct value");
    //mod_data3
    XCTAssertEqual(Processor->memory[36], 0x70, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[37], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[38], 3, @"Should be the correct value");
    //op2
    XCTAssertEqual(Processor->memory[39], 0x40, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[40], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[41], TempProcessor->memory[3], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[42], TempProcessor->memory[4], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[43], TempProcessor->memory[5], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[44], 0xfa, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[45], 0xf9, @"Should be the correct value");
    //modify4
    XCTAssertEqual(Processor->memory[46], 0x60, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[47], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[48], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[49], 1, @"Should be the correct value");
    //mod_data4
    XCTAssertEqual(Processor->memory[50], 0x70, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[51], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[52], 1, @"Should be the correct value");
    //modify5
    XCTAssertEqual(Processor->memory[53], 0x50, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[54], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[55], HKHubArchInstructionRegisterPC, @"Should be the correct value");
    //mod_data5
    XCTAssertEqual(Processor->memory[56], 0x70, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[57], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[58], 6, @"Should be the correct value");
    //op3
    XCTAssertEqual(Processor->memory[59], 0x40, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[60], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[61], TempProcessor->memory[6], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[62], TempProcessor->memory[7], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[63], 0xfb, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[64], 0xfa, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[65], 0xf9, @"Should be the correct value");
    //modify6
    XCTAssertEqual(Processor->memory[66], 0x50, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[67], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[68], HKHubArchInstructionRegisterPC, @"Should be the correct value");
    //mod_data6
    XCTAssertEqual(Processor->memory[69], 0x70, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[70], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[71], 0, @"Should be the correct value");
    //leftover
    XCTAssertEqual(Processor->memory[72], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[73], 0xfe, @"Should be the correct value");
    
    //[2:4] [device:12] change breakpoint [offset:8] [_:6] [w:1] [r:1]
    //[3:4] [device:12] change [port:8] [receiving port: 8, connected:1, _:3, device:12]
    Source =
        "break1:\n"
        ".byte -1, -2, -3, -4\n"
        "break2:\n"
        ".byte -1, -2, -3, -4\n"
        "break3:\n"
        ".byte -1, -2, -3, -4\n"
        "port1:\n"
        ".byte -1, -2, -3, -4, -5, -6\n"
        "port2:\n"
        ".byte -1, -2, -3, -4, -5, -6\n"
        "port3:\n"
        ".byte -1, -2, -3, -4, -5, -6\n"
        "leftover:\n"
        ".byte -1, -2\n"
        ".entrypoint\n"
        "recv r0, [break1]\n"
        "recv r0, [break2]\n"
        "recv r0, [break3]\n"
        "recv r0, [port1]\n"
        "recv r0, [port2]\n"
        "recv r0, [port3]\n"
        "recv r0, [leftover]\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessorReset(Processor, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchProcessorSetBreakpoint(TempProcessor, HKHubArchProcessorDebugBreakpointRead, 0);
    HKHubArchProcessorSetBreakpoint(TempProcessor, HKHubArchProcessorDebugBreakpointWrite | HKHubArchProcessorDebugBreakpointRead, 2);
    HKHubArchProcessorSetBreakpoint(TempProcessor, HKHubArchProcessorDebugBreakpointRead, 255);
    Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(Processor, 1), HKHubArchProcessorGetPort(TempProcessor, 0));
    
    HKHubArchProcessorConnect(Processor, 1, Conn);
    HKHubArchProcessorConnect(TempProcessor, 0, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubModuleGetPort(Keyboard, 29), HKHubArchProcessorGetPort(TempProcessor, 2));
    
    HKHubModuleConnect(Keyboard, 29, Conn);
    HKHubArchProcessorConnect(TempProcessor, 2, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    HKHubArchSchedulerRun(Scheduler, 10.0);
    
    //break1
    XCTAssertEqual(Processor->memory[0], 0x20, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[1], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[2], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[3], HKHubArchProcessorDebugBreakpointRead, @"Should be the correct value");
    //break2
    XCTAssertEqual(Processor->memory[4], 0x20, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[5], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[6], 2, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[7], HKHubArchProcessorDebugBreakpointWrite | HKHubArchProcessorDebugBreakpointRead, @"Should be the correct value");
    //break3
    XCTAssertEqual(Processor->memory[8], 0x20, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[9], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[10], 255, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[11], HKHubArchProcessorDebugBreakpointRead, @"Should be the correct value");
    //port1
    XCTAssertEqual(Processor->memory[12], 0x30, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[13], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[14], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[15], 1, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[16], 0x8f, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[17], 0xff, @"Should be the correct value");
    //port2
    XCTAssertEqual(Processor->memory[18], 0x30, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[19], 5, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[20], 29, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[21], 2, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[22], 0x80, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[23], 0, @"Should be the correct value");
    //port3
    XCTAssertEqual(Processor->memory[24], 0x30, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[25], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[26], 2, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[27], 29, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[28], 0x80, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[29], 5, @"Should be the correct value");
    //leftover
    XCTAssertEqual(Processor->memory[30], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[31], 0xfe, @"Should be the correct value");
    
    HKHubArchProcessorDestroy(TempProcessor);
    HKHubArchProcessorDestroy(Processor);
    HKHubModuleDestroy(Keyboard);
    HKHubModuleDestroy(DebugController);
    HKHubArchSchedulerDestroy(Scheduler);
}

-(void) testEventAPIFiltering
{
    HKHubArchScheduler Scheduler = HKHubArchSchedulerCreate(CC_STD_ALLOCATOR);
    HKHubModule DebugController = HKHubModuleDebugControllerCreate(CC_STD_ALLOCATOR);
    
    const char *Source =
        "loop:\n"
        "add r0, 1\n"
        "mov [0xff], r0\n"
        "jmp loop\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor TempProcessor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubModuleDebugControllerConnectProcessor(DebugController, TempProcessor, 0);
    HKHubArchSchedulerAddProcessor(Scheduler, TempProcessor);
    
    for (int Loop = 1; Loop < 5; Loop++)
    {
        Binary->data[2] += Loop;
        
        HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
        
        HKHubModuleDebugControllerConnectProcessor(DebugController, Processor, 0);
        
        HKHubArchSchedulerAddProcessor(Scheduler, Processor);
        HKHubArchProcessorDestroy(Processor);
    }
    
    HKHubArchBinaryDestroy(Binary);
    
    HKHubModule Keyboard = HKHubModuleKeyboardCreate(CC_STD_ALLOCATOR);
    HKHubModuleDebugControllerConnectModule(DebugController, Keyboard, CC_STRING("keyboard"));
    HKHubModuleKeyboardEnterKey(Keyboard, 1);
    HKHubModuleKeyboardEnterKey(Keyboard, 2);
    HKHubModuleKeyboardEnterKey(Keyboard, 3);
    HKHubModuleKeyboardEnterKey(Keyboard, 4);
    for (int Loop = 0; Loop < 251; Loop++) HKHubModuleKeyboardEnterKey(Keyboard, 0);
    HKHubModuleKeyboardEnterKey(Keyboard, 5);
    HKHubModuleKeyboardEnterKey(Keyboard, 6);
    HKHubModuleKeyboardEnterKey(Keyboard, 7);
    HKHubModuleKeyboardEnterKey(Keyboard, 8);
    HKHubModuleKeyboardEnterKey(Keyboard, 9);
    
    Source =
        "device_connected:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7, -8, -9, -10, -11, -12, -13, -14\n"
        "op:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7\n"
        "op2:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7\n"
        "op3:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7\n"
        "leftover:\n"
        ".byte -1, -2\n"
        "op4:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7\n"
        "op5:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7\n"
        "op6:\n"
        ".byte -1, -2, -3, -4, -5, -6, -7\n"
        "modify:\n"
        ".byte -1, -2, -3\n"
        "cmd_filter1:\n"
        ".byte (0 << 4) | 8\n"
        "cmd_filter2:\n"
        ".byte (0 << 4) | 4\n"
        "dev_filter1:\n"
        ".byte (2 << 4) | 0, 0\n"
        "dev_filter2:\n"
        ".byte (2 << 4) | 0, 5\n"
        ".entrypoint\n"
        "send r0, 1, [cmd_filter1]\n"
        "send r0, 1, [cmd_filter2]\n"
        "send r0, 2, [dev_filter1]\n"
        "send r0, 2, [dev_filter2]\n"
        "recv r0, [device_connected]\n"
        "recv r0, [device_connected + 2]\n"
        "recv r0, [device_connected + 4]\n"
        "recv r0, [device_connected + 6]\n"
        "recv r0, [device_connected + 8]\n"
        "recv r0, [device_connected + 10]\n"
        "recv r0, [device_connected + 12]\n"
        "hlt\n"
        "recv r0, [op]\n"
        "recv r0, [op2]\n"
        "recv r0, [op3]\n"
        "recv r0, [leftover]\n"
        "hlt\n"
        "or [cmd_filter2], (1 << 4)\n"
        "send r0, 1, [cmd_filter2]\n"
        "recv r0, [op4]\n"
        "or [cmd_filter1], (1 << 4)\n"
        "send r0, 1, [cmd_filter1]\n"
        "recv r0, [op5]\n"
        "hlt\n"
        "recv r0, [op6]\n"
        "recv r0, [modify]\n"
        "hlt\n"
    ;
    
    AST = HKHubArchAssemblyParse(Source);
    
    Errors = NULL;
    Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    HKHubArchPortConnection Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(Processor, 0), HKHubModuleGetPort(DebugController, 0));
    
    HKHubArchProcessorConnect(Processor, 0, Conn);
    HKHubModuleConnect(DebugController, 0, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    HKHubArchSchedulerAddProcessor(Scheduler, Processor);
    
    HKHubArchSchedulerRun(Scheduler, 10.0);
    HKHubArchProcessorStep(TempProcessor, 3);
    HKHubArchSchedulerRun(Scheduler, 10.0); Processor->memory[Processor->state.pc] = 0xf8; Processor->status = HKHubArchProcessorStatusRunning;
    HKHubArchSchedulerRun(Scheduler, 10.0);
    
    //device_connected
    XCTAssertEqual(Processor->memory[0], 0x80, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[1], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[2], 0x80, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[3], 5, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[4], 0xfb, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[5], 0xfa, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[6], 0xf9, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[7], 0xf8, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[8], 0xf7, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[9], 0xf6, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[10], 0xf5, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[11], 0xf4, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[12], 0xf3, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[13], 0xf2, @"Should be the correct value");
    
    //op
    XCTAssertEqual(Processor->memory[14], 0x40, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[15], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[16], TempProcessor->memory[0], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[17], TempProcessor->memory[1], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[18], TempProcessor->memory[2], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[19], 0xfa, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[20], 0xf9, @"Should be the correct value");
    //op2
    XCTAssertEqual(Processor->memory[21], 0x40, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[22], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[23], TempProcessor->memory[3], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[24], TempProcessor->memory[4], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[25], TempProcessor->memory[5], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[26], 0xfa, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[27], 0xf9, @"Should be the correct value");
    //op3
    XCTAssertEqual(Processor->memory[28], 0x40, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[29], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[30], TempProcessor->memory[6], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[31], TempProcessor->memory[7], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[32], 0xfb, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[33], 0xfa, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[34], 0xf9, @"Should be the correct value");
    //leftover
    XCTAssertEqual(Processor->memory[35], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[36], 0xfe, @"Should be the correct value");
    
    HKHubArchProcessorStep(TempProcessor, 2);
    HKHubArchSchedulerRun(Scheduler, 10.0); Processor->memory[Processor->state.pc] = 0xf8; Processor->status = HKHubArchProcessorStatusRunning;
    HKHubArchSchedulerRun(Scheduler, 10.0);
    
    //op4
    XCTAssertEqual(Processor->memory[37], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[38], 0xfe, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[39], 0xfd, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[40], 0xfc, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[41], 0xfb, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[42], 0xfa, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[43], 0xf9, @"Should be the correct value");
    //op5
    XCTAssertEqual(Processor->memory[44], 0xff, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[45], 0xfe, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[46], 0xfd, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[47], 0xfc, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[48], 0xfb, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[49], 0xfa, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[50], 0xf9, @"Should be the correct value");
    
    HKHubArchProcessorStep(TempProcessor, 1);
    HKHubArchSchedulerRun(Scheduler, 10.0); Processor->memory[Processor->state.pc] = 0xf8; Processor->status = HKHubArchProcessorStatusRunning;
    HKHubArchSchedulerRun(Scheduler, 10.0);
    
    //op6
    XCTAssertEqual(Processor->memory[51], 0x40, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[52], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[53], TempProcessor->memory[6], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[54], TempProcessor->memory[7], @"Should be the correct value");
    XCTAssertEqual(Processor->memory[55], 0xfb, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[56], 0xfa, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[57], 0xf9, @"Should be the correct value");
    //modify
    XCTAssertEqual(Processor->memory[58], 0x50, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[59], 0, @"Should be the correct value");
    XCTAssertEqual(Processor->memory[60], HKHubArchInstructionRegisterPC, @"Should be the correct value");
    
    HKHubArchProcessorDestroy(TempProcessor);
    HKHubArchProcessorDestroy(Processor);
    HKHubModuleDestroy(Keyboard);
    HKHubModuleDestroy(DebugController);
    HKHubArchSchedulerDestroy(Scheduler);
}

@end
