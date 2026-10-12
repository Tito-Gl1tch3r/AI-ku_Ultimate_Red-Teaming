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

#include "HubArchExecutionGraph.h"
#include "HubArchInstruction.h"

static CCLinkedList(HKHubArchExecutionGraphInstruction) HKHubArchExecutionGraphAddNode(HKHubArchExecutionGraph Graph, CCLinkedList(HKHubArchExecutionGraphInstruction) InstructionGraphTail, HKHubArchInstructionState *Instruction, HKHubArchExecutionGraphRange *Range, uint8_t PC, uint8_t NextPC)
{
    CCLinkedListNode *Node = CCLinkedListCreateNode(CC_STD_ALLOCATOR, sizeof(HKHubArchExecutionGraphInstruction), &(HKHubArchExecutionGraphInstruction){
        .offset = PC,
        .state = *Instruction,
        .jump = NULL
    });
    
    if (!InstructionGraphTail)
    {
        InstructionGraphTail = Node;
        CCArrayAppendElement(Graph->block, &Node);
    }
    
    else InstructionGraphTail = CCLinkedListAppend(InstructionGraphTail, Node);
    
    const uint8_t Count = Range->count + (NextPC - PC);
    Range->count = Range->count < Count ? Count : UINT8_MAX;
    
    return InstructionGraphTail;
}

static CCLinkedList(HKHubArchExecutionGraphInstruction) HKHubArchExecutionGraphGenerate(HKHubArchExecutionGraph Graph, uint8_t Memory[256], uint8_t PC)
{
    for (size_t Loop = 0, Count = CCArrayGetCount(Graph->range); Loop < Count; Loop++)
    {
        HKHubArchExecutionGraphRange *Range = CCArrayGetElementAtIndex(Graph->range, Loop);
        if ((Range->start <= PC) && ((Range->start + Range->count) > PC))
        {
            CCLinkedList(HKHubArchExecutionGraphInstruction) *Instruction = CCArrayGetElementAtIndex(Graph->block, Loop);
            return *Instruction;
        }
    }
    
    CCLinkedList(HKHubArchExecutionGraphInstruction) InstructionGraphHead = NULL, InstructionGraphTail = NULL;
    const size_t Index = CCArrayAppendElement(Graph->range, &(HKHubArchExecutionGraphRange){ .start = PC, .count = 0 });
    HKHubArchExecutionGraphRange *Range = CCArrayGetElementAtIndex(Graph->range, Index);
    
    for (uint8_t NextPC = 0; ; PC = NextPC)
    {
        HKHubArchInstructionState Instruction;
        NextPC = HKHubArchInstructionDecode(PC, Memory, &Instruction);
        
        if (Instruction.opcode != -1)
        {
            InstructionGraphTail = HKHubArchExecutionGraphAddNode(Graph, InstructionGraphTail, &Instruction, Range, PC, NextPC);
            if (!InstructionGraphHead) InstructionGraphHead = InstructionGraphTail;
            
            if (!HKHubArchInstructionPredictableFlow(&Instruction))
            {
                HKHubArchInstructionControlFlow Flow = HKHubArchInstructionGetControlFlow(&Instruction);
                switch (Flow & HKHubArchInstructionControlFlowEffectMask)
                {
                    case HKHubArchInstructionControlFlowEffectBranch:
                        CCAssertLog(Instruction.operand[0].type == HKHubArchInstructionOperandI &&
                                    Instruction.operand[1].type == HKHubArchInstructionOperandNA &&
                                    Instruction.operand[2].type == HKHubArchInstructionOperandNA, "Branch instruction operands have changed");
                        
                        ((HKHubArchExecutionGraphInstruction*)CCLinkedListGetNodeData(InstructionGraphTail))->jump = HKHubArchExecutionGraphGenerate(Graph, Memory, PC + Instruction.operand[0].value);
                        
                        if ((Flow & HKHubArchInstructionControlFlowEvaluationMask) == HKHubArchInstructionControlFlowEvaluationUnconditional) return InstructionGraphHead;
                        break;
                        
                    case HKHubArchInstructionControlFlowEffectPause:
                        return InstructionGraphHead;
                        
                    default:
                        break;
                }
            }
        }
        
        else break;
        
        for (size_t Loop = 0, Count = CCArrayGetCount(Graph->range); Loop < Count; Loop++)
        {
            HKHubArchExecutionGraphRange *BlockRange = CCArrayGetElementAtIndex(Graph->range, Loop);
            if ((BlockRange->start <= NextPC) && ((BlockRange->start + BlockRange->count) > NextPC))
            {
                if (Count != 1)
                {
                    CCLinkedList(HKHubArchExecutionGraphInstruction) *Block = CCArrayGetElementAtIndex(Graph->block, Loop);
                    CCLinkedListPrepend(*Block, InstructionGraphTail);
                    *Block = InstructionGraphHead;
                    
                    BlockRange->start = Range->start;
                    BlockRange->count += Range->count;
                    
                    CCArrayRemoveElementAtIndex(Graph->range, Index);
                    CCArrayRemoveElementAtIndex(Graph->block, Index);
                }
                
                return InstructionGraphHead;
            }
        }
    }
    
    if (!Range->count) CCArrayRemoveElementAtIndex(Graph->range, CCArrayGetCount(Graph->range) - 1);
    
    return InstructionGraphHead;
}

static void HKHubArchExecutionGraphDestructor(HKHubArchExecutionGraph Graph)
{
    CCEnumerable Enumerable;
    CCArrayGetEnumerable(Graph->block, &Enumerable);
    
    for (CCLinkedList(HKHubArchExecutionGraphInstruction) *Node = CCEnumerableGetCurrent(&Enumerable); Node; Node = CCEnumerableNext(&Enumerable))
    {
        CCLinkedListDestroy(*Node);
    }
    
    CCArrayDestroy(Graph->block);
    CCArrayDestroy(Graph->range);
}

HKHubArchExecutionGraph HKHubArchExecutionGraphCreate(CCAllocatorType Allocator, uint8_t Memory[256], uint8_t PC)
{
    CCAssertLog(Memory, "Memory must not be null");
    
    HKHubArchExecutionGraph Graph = CCMalloc(Allocator, sizeof(HKHubArchExecutionGraphInfo), NULL, CC_DEFAULT_ERROR_CALLBACK);
    
    if (Graph)
    {
        *Graph = (HKHubArchExecutionGraphInfo){
            .block = CCArrayCreate(CC_STD_ALLOCATOR, sizeof(CCLinkedList), 4),
            .range = CCArrayCreate(CC_STD_ALLOCATOR, sizeof(HKHubArchExecutionGraphRange), 4)
        };
        
        HKHubArchExecutionGraphGenerate(Graph, Memory, PC);
        
        for (size_t Loop = 0, Count = CCArrayGetCount(Graph->block); Loop < Count; Loop++)
        {
            CCLinkedList(HKHubArchExecutionGraphInstruction) *Block = CCArrayGetElementAtIndex(Graph->block, Loop);
            *Block = CCLinkedListGetHead(*Block);
        }
        
        CCMemorySetDestructor(Graph, (CCMemoryDestructorCallback)HKHubArchExecutionGraphDestructor);
    }
    
    else CC_LOG_ERROR("Failed to create the execution graph, due to allocation failure (%zu)", sizeof(HKHubArchExecutionGraphInfo));
    
    return Graph;
}

void HKHubArchExecutionGraphDestroy(HKHubArchExecutionGraph Graph)
{
    CCAssertLog(Graph, "Graph must not be null");
    
    CCFree(Graph);
}
