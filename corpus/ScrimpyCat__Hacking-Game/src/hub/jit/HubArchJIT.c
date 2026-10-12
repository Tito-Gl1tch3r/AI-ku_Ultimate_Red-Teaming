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

#include "HubArchJIT.h"
#include "HubArchProcessor.h"
#include "HubArchInstruction.h"

#if CC_PLATFORM_OS_X
#include <mach/mach.h>
#include <mach/mach_vm.h>

#if CC_HARDWARE_ARCH_X86_64
#define HK_HUB_ARCH_JIT 1
#endif
#endif

extern _Bool HKHubArchJITGenerateBlock(HKHubArchJIT JIT, HKHubArchJITBlock *JITBlock, void *Ptr, CCLinkedList(HKHubArchExecutionGraphInstruction) Block, HKHubArchJITOptions Options);
extern void HKHubArchJITRemoveEntry(void *Entry);

static void *HKHubArchJITAllocateExecutable(size_t Size)
{
#if CC_PLATFORM_OS_X
    //TODO: Setup an allocator, then allocate a large chunk and reference check the blocks (so any that can be shared will be).
    mach_vm_address_t Address = 0;
    mach_error_t err = mach_vm_allocate(mach_task_self(), &Address, Size, VM_FLAGS_ANYWHERE);
    if (err == KERN_SUCCESS)
    {
        err = mach_vm_protect(mach_task_self(), Address, Size, FALSE, VM_PROT_ALL);
        if (err == KERN_SUCCESS)
        {
            return (void*)Address;
        }
        
        else
        {
            mach_error("mach_vm_protect", err);
            CC_LOG_ERROR("Failed to allocate executable memory, due to memory protection error (%u)", err);
            
            mach_vm_deallocate(mach_task_self(), Address, Size);
        }
    }
    
    else
    {
        mach_error("mach_vm_allocate", err);
        CC_LOG_ERROR("Failed to allocate executable memory, due to allocation failure (%zu)", Size);
    }
#endif
    
    return NULL;
}

static void HKHubArchJITDeallocateExecutable(void *Ptr, size_t Size)
{
#if CC_PLATFORM_OS_X
    mach_vm_deallocate(mach_task_self(), (mach_vm_address_t)Ptr, Size);
#endif
}

CC_ARRAY_DECLARE(HKHubArchInstructionState);

static void HKHubArchJITBlockAssetRegister(CCArray(HKHubArchInstructionState) Instructions, HKHubArchJITBlock *CC_RETAIN(Block));
static CC_NEW HKHubArchJITBlock *HKHubArchJITBlockAssetCreate(CCLinkedList(HKHubArchExecutionGraphInstruction) Instructions);

#define HK_HUB_ARCH_JIT_BLOCK_SIZE 1024

static void HKHubArchJITBlockDestructor(HKHubArchJITBlock *Block)
{
    CCArrayDestroy(Block->map);
    HKHubArchJITDeallocateExecutable((void*)Block->code, HK_HUB_ARCH_JIT_BLOCK_SIZE);
}

static void HKHubArchJITGenerate(HKHubArchJIT JIT, HKHubArchExecutionGraph Graph, HKHubArchJITOptions Options)
{
    const _Bool Cache = Options & HKHubArchJITOptionsCache;
    for (size_t Loop = 0, Count = CCArrayGetCount(Graph->block); Loop < Count; Loop++)
    {
        CCLinkedList(HKHubArchExecutionGraphInstruction) Instruction = *(CCLinkedList*)CCArrayGetElementAtIndex(Graph->block, Loop);
        HKHubArchJITBlock *CachedBlock = HKHubArchJITBlockAssetCreate(Instruction);
        
        if (CachedBlock)
        {
            for (size_t Loop = 0, Index = 0, Count = CCArrayGetCount(CachedBlock->map); Loop < Count; Loop++)
            {
                const HKHubArchJITBlockRelativeEntry *Entry = CCArrayGetElementAtIndex(CachedBlock->map, Loop);
                for ( ; Entry->index != Index; Index++) Instruction = CCLinkedListEnumerateNext(Instruction);
                
                CCDictionarySetValue(JIT->map, &(uint8_t){ ((HKHubArchExecutionGraphInstruction*)CCLinkedListGetNodeData(Instruction))->offset }, &(HKHubArchJITBlockReferenceEntry){ .entry = Entry->entry, .block = CCRetain(CachedBlock), .size = HKHubArchInstructionSizeOfEncoding(&((HKHubArchExecutionGraphInstruction*)CCLinkedListGetNodeData(Instruction))->state) });
            }
            
            CCFree(CachedBlock);
        }
        
        else
        {
            const size_t Size = HK_HUB_ARCH_JIT_BLOCK_SIZE; // TODO: calculate size required?
            void *Ptr = HKHubArchJITAllocateExecutable(Size);
            if (Ptr)
            {
                HKHubArchJITBlock Block = { .code = (uintptr_t)Ptr, .map = CCArrayCreate(CC_STD_ALLOCATOR, sizeof(HKHubArchJITBlockRelativeEntry), 4), .cached = Cache };
                
#if CC_HARDWARE_ARCH_X86_64
                const _Bool Generated = HKHubArchJITGenerateBlock(JIT, &Block, Ptr, Instruction, Options);
#endif
                
                if (Generated)
                {
                    CCArray(HKHubArchInstructionState) Instructions = NULL;
                    
                    CC_SAFE_Malloc(CachedBlock, sizeof(HKHubArchJITBlock),
                                   CCArrayDestroy(Block.map);
                                   HKHubArchJITDeallocateExecutable(Ptr, Size);
                                   continue;
                                   );
                    
                    *CachedBlock = Block;
                    
                    CCMemorySetDestructor(CachedBlock, (CCMemoryDestructorCallback)HKHubArchJITBlockDestructor);
                    
                    if (Cache)
                    {
                        Instructions = CCArrayCreate(CC_STD_ALLOCATOR, sizeof(HKHubArchInstructionState), 8);
                        CCArrayAppendElement(Instructions, &((HKHubArchExecutionGraphInstruction*)CCLinkedListGetNodeData(Instruction))->state);
                    }
                    
                    for (size_t Loop = 0, Index = 0, Count = CCArrayGetCount(Block.map); Loop < Count; Loop++)
                    {
                        const HKHubArchJITBlockRelativeEntry *Entry = CCArrayGetElementAtIndex(Block.map, Loop);
                        for ( ; Entry->index != Index; Index++)
                        {
                            Instruction = CCLinkedListEnumerateNext(Instruction);
                            if (Cache) CCArrayAppendElement(Instructions, &((HKHubArchExecutionGraphInstruction*)CCLinkedListGetNodeData(Instruction))->state);
                        }
                        
                        CCDictionarySetValue(JIT->map, &(uint8_t){ ((HKHubArchExecutionGraphInstruction*)CCLinkedListGetNodeData(Instruction))->offset }, &(HKHubArchJITBlockReferenceEntry){ .entry = Entry->entry, .block = CCRetain(CachedBlock), .size = HKHubArchInstructionSizeOfEncoding(&((HKHubArchExecutionGraphInstruction*)CCLinkedListGetNodeData(Instruction))->state) });
                    }
                    
                    if (Cache)
                    {
                        while ((Instruction = CCLinkedListEnumerateNext(Instruction))) CCArrayAppendElement(Instructions, &((HKHubArchExecutionGraphInstruction*)CCLinkedListGetNodeData(Instruction))->state);
                        
                        HKHubArchJITBlockAssetRegister(Instructions, CachedBlock);
                    }
                    
                    CCFree(CachedBlock);
                }
                
                else
                {
                    CCArrayDestroy(Block.map);
                    HKHubArchJITDeallocateExecutable(Ptr, Size);
                }
            }
        }
    }
}

static void HKHubArchJITDestructor(HKHubArchJIT JIT)
{
    CCDictionaryDestroy(JIT->map);
}

void HKHubArchJITBlockReferenceEntryElementDestructor(CCDictionary Dictionary, HKHubArchJITBlockReferenceEntry *Element)
{
    CCFree(Element->block);
}

HKHubArchJIT HKHubArchJITCreate(CCAllocatorType Allocator, HKHubArchExecutionGraph Graph, HKHubArchJITOptions Options)
{
    CCAssertLog(Graph, "Graph must not be null");
    
#if HK_HUB_ARCH_JIT
    HKHubArchJIT JIT = CCMalloc(Allocator, sizeof(HKHubArchJITInfo), NULL, CC_DEFAULT_ERROR_CALLBACK);
    
    if (JIT)
    {
        *JIT = (HKHubArchJITInfo){
            .map = CCDictionaryCreate(Allocator, CCDictionaryHintSizeMedium | CCDictionaryHintConstantElements | CCDictionaryHintConstantLength | CCDictionaryHintHeavyFinding, sizeof(uint8_t), sizeof(HKHubArchJITBlockReferenceEntry), &(CCDictionaryCallbacks){
                .valueDestructor = (CCDictionaryElementDestructor)HKHubArchJITBlockReferenceEntryElementDestructor
            })
        };
        
        HKHubArchJITGenerate(JIT, Graph, Options);
        
        CCMemorySetDestructor(JIT, (CCMemoryDestructorCallback)HKHubArchJITDestructor);
    }
    
    else CC_LOG_ERROR("Failed to create the jit native block, due to allocation failure (%zu)", sizeof(HKHubArchJITInfo));
    
    return JIT;
#else
    return NULL;
#endif
}

void HKHubArchJITDestroy(HKHubArchJIT JIT)
{
    CCAssertLog(JIT, "JIT must not be null");
    
    CCFree(JIT);
}

void HKHubArchJITInvalidateBlocks(HKHubArchJIT JIT, uint8_t Offset, size_t Size)
{
    for (size_t Loop = 0; Loop < Size; Loop++)
    {
        CCDictionaryEntry Entry = CCDictionaryFindKey(JIT->map, &(uint8_t){ Offset + Loop });
        const HKHubArchJITBlockReferenceEntry *Ref = CCDictionaryGetEntry(JIT->map, Entry);
        
        /*
         TODO: Refactor graph and jit lookup
         */
        if ((!Loop) && (!Ref))
        {
            for (size_t Attempts = 0; Attempts < 5; Attempts++)
            {
                Entry = CCDictionaryFindKey(JIT->map, &(uint8_t){ Offset - Attempts });
                Ref = CCDictionaryGetEntry(JIT->map, Entry);
                if ((Ref) && (Offset < (Offset - Attempts) + Ref->size)) break;
                
                Ref = NULL;
            }
        }
        
        if (!Ref) continue;
        
        if (Ref->block->cached)
        {
            const HKHubArchJITBlock *RefBlock = Ref->block;
            
            const size_t Size = HK_HUB_ARCH_JIT_BLOCK_SIZE;
            void *Ptr = HKHubArchJITAllocateExecutable(Size);
            if (Ptr)
            {
                HKHubArchJITBlock *Block = CCMalloc(CC_DEFAULT_ALLOCATOR, sizeof(HKHubArchJITBlock), NULL, CC_DEFAULT_ERROR_CALLBACK);
                if (Block)
                {
                    *Block = (HKHubArchJITBlock){ .code = (uintptr_t)Ptr, .map = CCArrayCreate(CC_STD_ALLOCATOR, sizeof(HKHubArchJITBlockRelativeEntry), 4), .cached = FALSE };
                    
                    memcpy(Ptr, (const void*)RefBlock->code, Size);
                    
                    CCMemorySetDestructor(Block, (CCMemoryDestructorCallback)HKHubArchJITBlockDestructor);
                    
                    for (size_t Loop = 0, Count = CCArrayGetCount(RefBlock->map); Loop < Count; Loop++)
                    {
                        HKHubArchJITBlockRelativeEntry BlockEntry = *(const HKHubArchJITBlockRelativeEntry*)CCArrayGetElementAtIndex(RefBlock->map, Loop);
                        BlockEntry.entry = (BlockEntry.entry - RefBlock->code) + Block->code;
                        CCArrayAppendElement(Block->map, &BlockEntry);
                    }
                    
                    CC_DICTIONARY_FOREACH_VALUE_PTR(HKHubArchJITBlockReferenceEntry, Value, JIT->map)
                    {
                        if (Value->block == RefBlock)
                        {
                            CCFree(Value->block);
                            Value->block = CCRetain(Block);
                            Value->entry = (Value->entry - Ref->block->code) + Block->code;
                        }
                    }
                    
                    CCFree(Block);
                }
                
                else
                {
                    HKHubArchJITDeallocateExecutable(Ptr, Size);
                    
                    goto RemoveBlock;
                }
            }
            
            else
            {
            RemoveBlock:;
                size_t Count = 0;
                uint8_t Keys[256];
                
                CC_DICTIONARY_FOREACH_VALUE_PTR(HKHubArchJITBlockReferenceEntry, Value, JIT->map)
                {
                    if (Value->block == RefBlock)
                    {
                        Keys[Count++] = *(uint8_t*)CCDictionaryGetKey(JIT->map, CCDictionaryEnumeratorGetEntry(&CC_DICTIONARY_CURRENT_VALUE_ENUMERATOR));
                    }
                }
                
                for (size_t Loop = 0; Loop < Count; Loop++)
                {
                    CCDictionaryRemoveValue(JIT->map, &Keys[Loop]);
                }
                
                continue;
            }
        }
        
#if CC_HARDWARE_ARCH_X86_64
        HKHubArchJITRemoveEntry((void*)Ref->entry);
#endif
        
        CCDictionaryRemoveEntry(JIT->map, Entry);
    }
}

#ifndef HK_HUB_ARCH_JIT
void HKHubArchJITCall(HKHubArchJIT JIT, HKHubArchProcessor Processor)
{
    return;
}
#endif

typedef struct {
    union {
        CCArray(HKHubArchInstructionState) state;
        CCLinkedList(HKHubArchExecutionGraphInstruction) graph;
    };
    _Bool isState;
} HKHubArchJITInstructionBlock;

static void HKHubArchJITInstructionBlockDestructor(HKHubArchJITInstructionBlock *Instructions)
{
    CCAssertLog(Instructions->isState, "Should only store the state only variant");
    
    CCArrayDestroy(Instructions->state);
}

static uintmax_t HKHubArchJITInstructionBlockHasher(const HKHubArchJITInstructionBlock *Instructions)
{
#if UINTMAX_MAX < UINT64_MAX
    const uintmax_t Prime = 0x01000193;
    uintmax_t Hash = 0x811c9dc5;
#else
    const uintmax_t Prime = 0x00000100000001b3;
    uintmax_t Hash = 0xcbf29ce484222325;
#endif
    
    CCEnumerable Enumerable;
    
    if (Instructions->isState) CCArrayGetEnumerable(Instructions->state, &Enumerable);
    else CCLinkedListGetEnumerable(Instructions->graph, &Enumerable);
    
    
    size_t BitCount = 0, Loop = 0;
    uint8_t Current = 0;
    for (const void *Instruction = CCEnumerableGetCurrent(&Enumerable); Instruction; Instruction = CCEnumerableNext(&Enumerable))
    {
        const HKHubArchInstructionState *State = Instructions->isState ? Instruction : &((const HKHubArchExecutionGraphInstruction*)Instruction)->state;
        const size_t FreeBits = 8 - (BitCount % 8);
        
        if (FreeBits <= 5)
        {
            Current |= State->opcode >> (5 - FreeBits);
            
            Hash ^= Current;
            Hash *= Prime;
            
            Current = (State->opcode & CCBitSet(5 - FreeBits)) << (8 - (5 - FreeBits));
        }
        
        else Current |= (State->opcode & CCBitSet(FreeBits)) << (FreeBits - 5);
        
        BitCount += 5;
        
        if (++Loop < 8) break;
    }
    
    if (BitCount % 8)
    {
        Hash ^= Current;
        Hash *= Prime;
    }
    
    return Hash;
}

static CCComparisonResult HKHubArchJITInstructionBlockComparator(const HKHubArchJITInstructionBlock *a, const HKHubArchJITInstructionBlock *b)
{
    CCEnumerable EnumerableA, EnumerableB;
    
    if (a->isState) CCArrayGetEnumerable(a->state, &EnumerableA);
    else CCLinkedListGetEnumerable(a->graph, &EnumerableA);
    
    if (b->isState) CCArrayGetEnumerable(b->state, &EnumerableB);
    else CCLinkedListGetEnumerable(b->graph, &EnumerableB);
    
    for (const void *InstructionA = CCEnumerableGetCurrent(&EnumerableA), *InstructionB = CCEnumerableGetCurrent(&EnumerableB); InstructionA || InstructionB; InstructionA = CCEnumerableNext(&EnumerableA), InstructionB = CCEnumerableNext(&EnumerableB))
    {
        if ((!InstructionA) || (!InstructionB)) return CCComparisonResultInvalid;
        
        const HKHubArchInstructionState *StateA = a->isState ? InstructionA : &((const HKHubArchExecutionGraphInstruction*)InstructionA)->state;
        const HKHubArchInstructionState *StateB = b->isState ? InstructionB : &((const HKHubArchExecutionGraphInstruction*)InstructionB)->state;
        
        if (StateA->opcode != StateB->opcode) return CCComparisonResultInvalid;
        
        for (size_t Loop = 0; Loop < 3; Loop++)
        {
            if (StateA->operand[Loop].type != StateB->operand[Loop].type) return CCComparisonResultInvalid;
            
            switch (StateA->operand[Loop].type)
            {
                case HKHubArchInstructionOperandI:
                    if (StateA->operand[Loop].value != StateB->operand[Loop].value) return CCComparisonResultInvalid;
                    break;
                    
                case HKHubArchInstructionOperandR:
                    if (StateA->operand[Loop].reg != StateB->operand[Loop].reg) return CCComparisonResultInvalid;
                    break;
                    
                case HKHubArchInstructionOperandM:
                {
                    if (StateA->operand[Loop].memory.type != StateB->operand[Loop].memory.type) return CCComparisonResultInvalid;
                    
                    switch (StateA->operand[Loop].memory.type)
                    {
                        case HKHubArchInstructionMemoryOffset:
                            if (StateA->operand[Loop].memory.offset != StateB->operand[Loop].memory.offset) return CCComparisonResultInvalid;
                            break;
                            
                        case HKHubArchInstructionMemoryRegister:
                            if (StateA->operand[Loop].memory.reg != StateB->operand[Loop].memory.reg) return CCComparisonResultInvalid;
                            break;
                            
                        case HKHubArchInstructionMemoryRelativeOffset:
                            if (StateA->operand[Loop].memory.relativeOffset.offset != StateB->operand[Loop].memory.relativeOffset.offset) return CCComparisonResultInvalid;
                            if (StateA->operand[Loop].memory.relativeOffset.reg != StateB->operand[Loop].memory.relativeOffset.reg) return CCComparisonResultInvalid;
                            break;
                            
                        case HKHubArchInstructionMemoryRelativeRegister:
                            if (StateA->operand[Loop].memory.relativeReg[0] != StateB->operand[Loop].memory.relativeReg[0]) return CCComparisonResultInvalid;
                            if (StateA->operand[Loop].memory.relativeReg[1] != StateB->operand[Loop].memory.relativeReg[1]) return CCComparisonResultInvalid;
                            break;
                    }
                    
                    break;
                }
                    
                default:
                    break;
            }
        }
    }
    
    return CCComparisonResultEqual;
}

const CCDictionaryElementDestructor HKHubArchJITInstructionBlockDestructorForDictionary = (CCDictionaryElementDestructor)HKHubArchJITInstructionBlockDestructor;
const CCDictionaryKeyHasher HKHubArchJITInstructionBlockHasherForDictionary = (CCDictionaryKeyHasher)HKHubArchJITInstructionBlockHasher;
const CCComparator HKHubArchJITInstructionBlockComparatorForDictionary = (CCComparator)HKHubArchJITInstructionBlockComparator;

const CCAssetManagerInterface HKHubArchJITBlockAssetInterface = {
    .identifier = {
        .destructor = &HKHubArchJITInstructionBlockDestructorForDictionary,
        .hasher = &HKHubArchJITInstructionBlockHasherForDictionary,
        .comparator = &HKHubArchJITInstructionBlockComparatorForDictionary,
        .size = sizeof(HKHubArchJITInstructionBlock)
    }
};

static CCAssetManager HKHubArchJITBlockManager = CC_ASSET_MANAGER_INIT(&HKHubArchJITBlockAssetInterface);

static void HKHubArchJITBlockAssetRegister(CCArray(HKHubArchInstructionState) Instructions, HKHubArchJITBlock *Block)
{
    CCAssetManagerRegister(&HKHubArchJITBlockManager, &(HKHubArchJITInstructionBlock){
        .state = Instructions,
        .isState = TRUE
    }, Block);
}

static HKHubArchJITBlock *HKHubArchJITBlockAssetCreate(CCLinkedList(HKHubArchExecutionGraphInstruction) Instructions)
{
    void *Asset = CCAssetManagerCreate(&HKHubArchJITBlockManager, &(HKHubArchJITInstructionBlock){
        .graph = Instructions,
        .isState = FALSE
    });
    
    return Asset;
}
