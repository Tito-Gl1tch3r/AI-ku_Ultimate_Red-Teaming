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

#define HKHubArchAssemblyPrintError(err) if (Errors) { HKHubArchAssemblyPrintError(err); CCCollectionDestroy(err); err = NULL; }

@interface HubArchCacheTests : XCTestCase

@end

@implementation HubArchCacheTests

-(void) testSimpleFlow
{
    const char *Source =
        "data: .byte 2\n"
        ".entrypoint\n"
        "mov r0, [data]\n"
        "add r0, 2\n"
        "jmp skip\n"
        "sub r0, 2\n"
        "skip:\n"
        "sub [data], 1\n"
        "jnz skip\n"
        "nop\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    
    HKHubArchProcessorCache(Processor, 0);
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->range), 2, @"Should have the correct number of execution ranges");
    
    HKHubArchExecutionGraphRange *Range = CCArrayGetElementAtIndex(Processor->cache.graph->range, 0);
    XCTAssertEqual(Range->start, 1, @"Should have the correct start");
    XCTAssertEqual(Range->count, 8, @"Should have the correct count");
    
    Range = CCArrayGetElementAtIndex(Processor->cache.graph->range, 1);
    XCTAssertEqual(Range->start, 12, @"Should have the correct start");
    XCTAssertEqual(Range->count, 8, @"Should have the correct count");
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->block), 2, @"Should have the correct number of execution paths");
    
    CCLinkedListNode *Node = *(CCLinkedListNode**)CCArrayGetElementAtIndex(Processor->cache.graph->block, 0);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 1, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("mov r0,[0x00]")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 4, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("add r0,0x02")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 7, @"Should have the correct offset");
        XCTAssertNotEqual(GraphNode->jump, NULL, @"Should jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("jmp 0x05")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
        
        {
            CCLinkedListNode *Node = GraphNode->jump, *Skip = GraphNode->jump;
            XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
            if (Node)
            {
                const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
                XCTAssertEqual(GraphNode->offset, 12, @"Should have the correct offset");
                XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
                
                CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
                XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("sub [0x00],0x01")), @"Should have the correct instruction");
                CCStringDestroy(Instruction);
            }
            
            Node = CCLinkedListEnumerateNext(Node);
            XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
            if (Node)
            {
                const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
                XCTAssertEqual(GraphNode->offset, 16, @"Should have the correct offset");
                XCTAssertEqual(GraphNode->jump, Skip, @"Should jump to another node");
                
                CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
                XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("jnz 0xfc")), @"Should have the correct instruction");
                CCStringDestroy(Instruction);
            }
            
            Node = CCLinkedListEnumerateNext(Node);
            XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
            if (Node)
            {
                const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
                XCTAssertEqual(GraphNode->offset, 18, @"Should have the correct offset");
                XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
                
                CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
                XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("nop")), @"Should have the correct instruction");
                CCStringDestroy(Instruction);
            }
            
            Node = CCLinkedListEnumerateNext(Node);
            XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
            if (Node)
            {
                const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
                XCTAssertEqual(GraphNode->offset, 19, @"Should have the correct offset");
                XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
                
                CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
                XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("hlt")), @"Should have the correct instruction");
                CCStringDestroy(Instruction);
            }
            
            Node = CCLinkedListEnumerateNext(Node);
            XCTAssertEqual(Node, NULL, @"Should not have another graph node");
        }
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertEqual(Node, NULL, @"Should not have another graph node");
    
    HKHubArchBinaryDestroy(Binary);
    HKHubArchProcessorDestroy(Processor);
}

-(void) testPingPongFlow
{
    const char *Source =
        "a:\n"
        "add r0, r1\n"
        "jmp b\n"
        "b:\n"
        "sub r0, r1\n"
        "jmp a\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    
    HKHubArchProcessorCache(Processor, 0);
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->range), 2, @"Should have the correct number of execution ranges");
    
    HKHubArchExecutionGraphRange *Range = CCArrayGetElementAtIndex(Processor->cache.graph->range, 0);
    XCTAssertEqual(Range->start, 0, @"Should have the correct start");
    XCTAssertEqual(Range->count, 4, @"Should have the correct count");
    
    Range = CCArrayGetElementAtIndex(Processor->cache.graph->range, 1);
    XCTAssertEqual(Range->start, 4, @"Should have the correct start");
    XCTAssertEqual(Range->count, 4, @"Should have the correct count");
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->block), 2, @"Should have the correct number of execution paths");
    
    CCLinkedListNode *Node = *(CCLinkedListNode**)CCArrayGetElementAtIndex(Processor->cache.graph->block, 0);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 0, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("add r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    CCLinkedListNode *A = Node;
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 2, @"Should have the correct offset");
        XCTAssertNotEqual(GraphNode->jump, NULL, @"Should jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("jmp 0x02")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
        
        {
            CCLinkedListNode *Node = GraphNode->jump;
            XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
            if (Node)
            {
                const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
                XCTAssertEqual(GraphNode->offset, 4, @"Should have the correct offset");
                XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
                
                CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
                XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("sub r0,r1")), @"Should have the correct instruction");
                CCStringDestroy(Instruction);
            }
            
            Node = CCLinkedListEnumerateNext(Node);
            XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
            if (Node)
            {
                const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
                XCTAssertEqual(GraphNode->offset, 6, @"Should have the correct offset");
                XCTAssertEqual(GraphNode->jump, A, @"Should jump to another node");
                
                CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
                XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("jmp 0xfa")), @"Should have the correct instruction");
                CCStringDestroy(Instruction);
            }
            
            Node = CCLinkedListEnumerateNext(Node);
            XCTAssertEqual(Node, NULL, @"Should not have another graph node");
        }
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertEqual(Node, NULL, @"Should not have another graph node");
    
    HKHubArchBinaryDestroy(Binary);
    HKHubArchProcessorDestroy(Processor);
}

-(void) testPingPongFlowPartialEntry
{
    const char *Source =
        "a:\n"
        "add r0, r1\n"
        ".entrypoint\n"
        "jmp b\n"
        "b:\n"
        "sub r0, r1\n"
        "jmp a\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    
    HKHubArchProcessorCache(Processor, 0);
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->range), 2, @"Should have the correct number of execution ranges");
    
    HKHubArchExecutionGraphRange *Range = CCArrayGetElementAtIndex(Processor->cache.graph->range, 0);
    XCTAssertEqual(Range->start, 0, @"Should have the correct start");
    XCTAssertEqual(Range->count, 4, @"Should have the correct count");
    
    Range = CCArrayGetElementAtIndex(Processor->cache.graph->range, 1);
    XCTAssertEqual(Range->start, 4, @"Should have the correct start");
    XCTAssertEqual(Range->count, 4, @"Should have the correct count");
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->block), 2, @"Should have the correct number of execution paths");
    
    CCLinkedListNode *Node = *(CCLinkedListNode**)CCArrayGetElementAtIndex(Processor->cache.graph->block, 0);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 0, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("add r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    CCLinkedListNode *A = Node;
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 2, @"Should have the correct offset");
        XCTAssertNotEqual(GraphNode->jump, NULL, @"Should jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("jmp 0x02")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
        
        {
            CCLinkedListNode *Node = GraphNode->jump;
            XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
            if (Node)
            {
                const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
                XCTAssertEqual(GraphNode->offset, 4, @"Should have the correct offset");
                XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
                
                CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
                XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("sub r0,r1")), @"Should have the correct instruction");
                CCStringDestroy(Instruction);
            }
            
            Node = CCLinkedListEnumerateNext(Node);
            XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
            if (Node)
            {
                const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
                XCTAssertEqual(GraphNode->offset, 6, @"Should have the correct offset");
                XCTAssertEqual(GraphNode->jump, A, @"Should jump to another node");
                
                CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
                XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("jmp 0xfa")), @"Should have the correct instruction");
                CCStringDestroy(Instruction);
            }
            
            Node = CCLinkedListEnumerateNext(Node);
            XCTAssertEqual(Node, NULL, @"Should not have another graph node");
        }
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertEqual(Node, NULL, @"Should not have another graph node");
    
    HKHubArchBinaryDestroy(Binary);
    HKHubArchProcessorDestroy(Processor);
}

-(void) testLoopFlow
{
    const char *Source =
        "start:\n"
        "add r0, r1\n"
        ".entrypoint\n"
        "sub r0, r1\n"
        "jmp start\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    
    HKHubArchProcessorCache(Processor, 0);
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->range), 1, @"Should have the correct number of execution ranges");
    
    HKHubArchExecutionGraphRange *Range = CCArrayGetElementAtIndex(Processor->cache.graph->range, 0);
    XCTAssertEqual(Range->start, 0, @"Should have the correct start");
    XCTAssertEqual(Range->count, 6, @"Should have the correct count");
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->block), 1, @"Should have the correct number of execution paths");
    
    CCLinkedListNode *Node = *(CCLinkedListNode**)CCArrayGetElementAtIndex(Processor->cache.graph->block, 0);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 0, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("add r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    CCLinkedListNode *Start = Node;
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 2, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("sub r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 4, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, Start, @"Should jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("jmp 0xfc")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertEqual(Node, NULL, @"Should not have another graph node");
    
    HKHubArchBinaryDestroy(Binary);
    HKHubArchProcessorDestroy(Processor);
}

-(void) testRolloverFlow
{
    const char *Source =
        "add r0, r1\n"
        "jmp start\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".entrypoint\n"
        "start:\n"
        "sub r0, r1\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    
    HKHubArchProcessorCache(Processor, 0);
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->range), 1, @"Should have the correct number of execution ranges");
    
    HKHubArchExecutionGraphRange *Range = CCArrayGetElementAtIndex(Processor->cache.graph->range, 0);
    XCTAssertEqual(Range->start, 254, @"Should have the correct start");
    XCTAssertEqual(Range->count, 6, @"Should have the correct count");
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->block), 1, @"Should have the correct number of execution paths");
    
    CCLinkedListNode *Node = *(CCLinkedListNode**)CCArrayGetElementAtIndex(Processor->cache.graph->block, 0);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 254, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("sub r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    CCLinkedListNode *Start = Node;
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 0, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("add r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 2, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, Start, @"Should jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("jmp 0xfc")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertEqual(Node, NULL, @"Should not have another graph node");
    
    HKHubArchBinaryDestroy(Binary);
    HKHubArchProcessorDestroy(Processor);
}

-(void) testRolloverFlowReverseStart
{
    const char *Source =
        "add r0, r1\n"
        "jmp start\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        ".byte 0, 0, 0, 0, 0, 0, 0, 0, 0, 0\n"
        "start:\n"
        "sub r0, r1\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    
    HKHubArchProcessorCache(Processor, 0);
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->range), 1, @"Should have the correct number of execution ranges");
    
    HKHubArchExecutionGraphRange *Range = CCArrayGetElementAtIndex(Processor->cache.graph->range, 0);
    XCTAssertEqual(Range->start, 254, @"Should have the correct start");
    XCTAssertEqual(Range->count, 6, @"Should have the correct count");
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->block), 1, @"Should have the correct number of execution paths");
    
    CCLinkedListNode *Node = *(CCLinkedListNode**)CCArrayGetElementAtIndex(Processor->cache.graph->block, 0);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 254, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("sub r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    CCLinkedListNode *Start = Node;
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 0, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("add r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 2, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, Start, @"Should jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("jmp 0xfc")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertEqual(Node, NULL, @"Should not have another graph node");
    
    HKHubArchBinaryDestroy(Binary);
    HKHubArchProcessorDestroy(Processor);
}

-(void) testRolloverLoopFlow
{
    const char *Source =
        "add r0, r1\n"
        "jz start\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".entrypoint\n"
        "start:\n"
        "sub r0, r1\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    
    HKHubArchProcessorCache(Processor, 0);
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->range), 1, @"Should have the correct number of execution ranges");
    
    HKHubArchExecutionGraphRange *Range = CCArrayGetElementAtIndex(Processor->cache.graph->range, 0);
    XCTAssertEqual(Range->start, 254, @"Should have the correct start");
    XCTAssertEqual(Range->count, 255, @"Should have the correct count");
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->block), 1, @"Should have the correct number of execution paths");
    
    CCLinkedListNode *Node = *(CCLinkedListNode**)CCArrayGetElementAtIndex(Processor->cache.graph->block, 0);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 254, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("sub r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    CCLinkedListNode *Start = Node;
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 0, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("add r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 2, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, Start, @"Should jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("jz 0xfc")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    for (size_t Loop = 0; Loop < 250; Loop++)
    {
        Node = CCLinkedListEnumerateNext(Node);
        XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
        if (Node)
        {
            const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
            XCTAssertEqual(GraphNode->offset, 4 + Loop, @"Should have the correct offset");
            XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
            
            CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
            XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("nop")), @"Should have the correct instruction");
            CCStringDestroy(Instruction);
        }
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertEqual(Node, NULL, @"Should not have another graph node");
    
    HKHubArchBinaryDestroy(Binary);
    HKHubArchProcessorDestroy(Processor);
}

-(void) testRolloverLoopFlowReverseStart
{
    const char *Source =
        "add r0, r1\n"
        "jz start\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        "start:\n"
        "sub r0, r1\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    
    HKHubArchProcessorCache(Processor, 0);
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->range), 1, @"Should have the correct number of execution ranges");
    
    HKHubArchExecutionGraphRange *Range = CCArrayGetElementAtIndex(Processor->cache.graph->range, 0);
    XCTAssertEqual(Range->start, 254, @"Should have the correct start");
    XCTAssertEqual(Range->count, 255, @"Should have the correct count");
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->block), 1, @"Should have the correct number of execution paths");
    
    CCLinkedListNode *Node = *(CCLinkedListNode**)CCArrayGetElementAtIndex(Processor->cache.graph->block, 0);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 254, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("sub r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    CCLinkedListNode *Start = Node;
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 0, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("add r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 2, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, Start, @"Should jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("jz 0xfc")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    for (size_t Loop = 0; Loop < 250; Loop++)
    {
        Node = CCLinkedListEnumerateNext(Node);
        XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
        if (Node)
        {
            const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
            XCTAssertEqual(GraphNode->offset, 4 + Loop, @"Should have the correct offset");
            XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
            
            CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
            XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("nop")), @"Should have the correct instruction");
            CCStringDestroy(Instruction);
        }
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertEqual(Node, NULL, @"Should not have another graph node");
    
    HKHubArchBinaryDestroy(Binary);
    HKHubArchProcessorDestroy(Processor);
}

-(void) testRolloverLoopWithoutJumpFlow
{
    const char *Source =
        "add r0, r1\n"
        "xor r0, r1\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".entrypoint\n"
        "sub r0, r1\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    
    HKHubArchProcessorCache(Processor, 0);
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->range), 1, @"Should have the correct number of execution ranges");
    
    HKHubArchExecutionGraphRange *Range = CCArrayGetElementAtIndex(Processor->cache.graph->range, 0);
    XCTAssertEqual(Range->start, 254, @"Should have the correct start");
    XCTAssertEqual(Range->count, 255, @"Should have the correct count");
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->block), 1, @"Should have the correct number of execution paths");
    
    CCLinkedListNode *Node = *(CCLinkedListNode**)CCArrayGetElementAtIndex(Processor->cache.graph->block, 0);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 254, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("sub r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 0, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("add r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 2, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("xor r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    for (size_t Loop = 0; Loop < 250; Loop++)
    {
        Node = CCLinkedListEnumerateNext(Node);
        XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
        if (Node)
        {
            const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
            XCTAssertEqual(GraphNode->offset, 4 + Loop, @"Should have the correct offset");
            XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
            
            CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
            XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("nop")), @"Should have the correct instruction");
            CCStringDestroy(Instruction);
        }
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertEqual(Node, NULL, @"Should not have another graph node");
    
    HKHubArchBinaryDestroy(Binary);
    HKHubArchProcessorDestroy(Processor);
}

-(void) testRolloverLoopWithoutJumpFlowReverseStart
{
    const char *Source =
        "add r0, r1\n"
        "xor r0, r1\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        ".byte 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8, 0xf8\n"
        "sub r0, r1\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    
    HKHubArchProcessorCache(Processor, 0);
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->range), 1, @"Should have the correct number of execution ranges");
    
    HKHubArchExecutionGraphRange *Range = CCArrayGetElementAtIndex(Processor->cache.graph->range, 0);
    XCTAssertEqual(Range->start, 0, @"Should have the correct start");
    XCTAssertEqual(Range->count, 255, @"Should have the correct count");
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->block), 1, @"Should have the correct number of execution paths");
    
    CCLinkedListNode *Node = *(CCLinkedListNode**)CCArrayGetElementAtIndex(Processor->cache.graph->block, 0);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 0, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("add r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 2, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("xor r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    for (size_t Loop = 0; Loop < 250; Loop++)
    {
        Node = CCLinkedListEnumerateNext(Node);
        XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
        if (Node)
        {
            const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
            XCTAssertEqual(GraphNode->offset, 4 + Loop, @"Should have the correct offset");
            XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
            
            CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
            XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("nop")), @"Should have the correct instruction");
            CCStringDestroy(Instruction);
        }
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 254, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("sub r0,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertEqual(Node, NULL, @"Should not have another graph node");
    
    HKHubArchBinaryDestroy(Binary);
    HKHubArchProcessorDestroy(Processor);
}

-(void) testPartialFlow
{
    const char *Source =
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
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    
    HKHubArchProcessorCache(Processor, 0);
    
//    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->range), 1, @"Should have the correct number of execution ranges");
    
//    HKHubArchExecutionGraphRange *Range = CCArrayGetElementAtIndex(Processor->cache.graph->range, 0);
//    XCTAssertEqual(Range->start, 0, @"Should have the correct start");
//    XCTAssertEqual(Range->count, 255, @"Should have the correct count");
    
    XCTAssertEqual(CCArrayGetCount(Processor->cache.graph->block), 1, @"Should have the correct number of execution paths");
    
    CCLinkedListNode *Node = *(CCLinkedListNode**)CCArrayGetElementAtIndex(Processor->cache.graph->block, 0);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 0, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("mov r1,0x01")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 3, @"Should have the correct offset");
        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("add r1,r1")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
    if (Node)
    {
        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
        XCTAssertEqual(GraphNode->offset, 5, @"Should have the correct offset");
        XCTAssertNotEqual(GraphNode->jump, NULL, @"Should jump to another node");
        
        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("jmp 0xff")), @"Should have the correct instruction");
        CCStringDestroy(Instruction);
        
        {
            CCLinkedListNode *Node = GraphNode->jump;
            XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
            if (Node)
            {
                const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
                XCTAssertEqual(GraphNode->offset, 4, @"Should have the correct offset");
                XCTAssertNotEqual(GraphNode->jump, NULL, @"Should jump to another node");
                
                CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
                XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("jsl 0x3f")), @"Should have the correct instruction");
                CCStringDestroy(Instruction);
                
                {
                    CCLinkedListNode *Node = GraphNode->jump;
                    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
                    if (Node)
                    {
                        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
                        XCTAssertEqual(GraphNode->offset, 0x43, @"Should have the correct offset");
                        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
                        
                        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
                        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("mov r2,0x03")), @"Should have the correct instruction");
                        CCStringDestroy(Instruction);
                    }
                    
                    Node = CCLinkedListEnumerateNext(Node);
                    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
                    if (Node)
                    {
                        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
                        XCTAssertEqual(GraphNode->offset, 0x46, @"Should have the correct offset");
                        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
                        
                        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
                        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("hlt")), @"Should have the correct instruction");
                        CCStringDestroy(Instruction);
                    }
                    
                    Node = CCLinkedListEnumerateNext(Node);
                    XCTAssertEqual(Node, NULL, @"Should not have another graph node");
                }
            }
            
            Node = CCLinkedListEnumerateNext(Node);
            XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
            if (Node)
            {
                const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
                XCTAssertEqual(GraphNode->offset, 6, @"Should have the correct offset");
                XCTAssertNotEqual(GraphNode->jump, NULL, @"Should jump to another node");
                
                CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
                XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("jmp 0x02")), @"Should have the correct instruction");
                CCStringDestroy(Instruction);
                
                {
                    CCLinkedListNode *Node = GraphNode->jump;
                    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
                    if (Node)
                    {
                        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
                        XCTAssertEqual(GraphNode->offset, 8, @"Should have the correct offset");
                        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
                        
                        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
                        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("mov r2,0x02")), @"Should have the correct instruction");
                        CCStringDestroy(Instruction);
                    }
                    
                    Node = CCLinkedListEnumerateNext(Node);
                    XCTAssertNotEqual(Node, NULL, @"Should have the correct graph node");
                    if (Node)
                    {
                        const HKHubArchExecutionGraphInstruction *GraphNode = CCLinkedListGetNodeData(Node);
                        XCTAssertEqual(GraphNode->offset, 0x0b, @"Should have the correct offset");
                        XCTAssertEqual(GraphNode->jump, NULL, @"Should not jump to another node");
                        
                        CCString Instruction = HKHubArchInstructionDisassemble(&GraphNode->state);
                        XCTAssertTrue(CCStringEqual(Instruction, CC_STRING("hlt")), @"Should have the correct instruction");
                        CCStringDestroy(Instruction);
                    }
                    
                    Node = CCLinkedListEnumerateNext(Node);
                    XCTAssertEqual(Node, NULL, @"Should not have another graph node");
                }
            }
            
            Node = CCLinkedListEnumerateNext(Node);
            XCTAssertEqual(Node, NULL, @"Should not have another graph node");
        }
    }
    
    Node = CCLinkedListEnumerateNext(Node);
    XCTAssertEqual(Node, NULL, @"Should not have another graph node");
    
    HKHubArchBinaryDestroy(Binary);
    HKHubArchProcessorDestroy(Processor);
}

@end
