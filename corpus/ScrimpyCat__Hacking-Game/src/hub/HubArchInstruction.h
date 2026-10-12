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

#ifndef HackingGame_HubArchInstruction_h
#define HackingGame_HubArchInstruction_h

#include "Base.h"
#include "HubArchAssembly.h"
#include "HubArchProcessor.h"
#include "HubArchInstructionType.h"

/*!
 * @brief An instruction operation executed on a given processor with the given state.
 * @description Updates the processor's cycle count and any other state. Cycles are calculated for the operation
 *              alone.
 *
 * @param Processor The processor to execute the operation in.
 * @param State The operand state for the instruction.
 * @return The result of the operation.
 */
typedef HKHubArchInstructionOperationResult (*HKHubArchInstructionOperation)(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);


/*!
 * @brief Encode an instruction AST.
 * @param Offset The offset the instruction should be located at.
 * @param Data The data to output the encoding to.
 * @param Command The instruction command.
 * @param Errors The collection of errors.
 * @param Labels The labels.
 * @param Defines The defined symbols.
 * @param Expansion The symbol expansion behaviour.
 * @return The offset after the instruction.
 */
size_t HKHubArchInstructionEncode(size_t Offset, uint8_t Data[256], HKHubArchAssemblyASTNode *Command, CCOrderedCollection(HKHubArchAssemblyASTError) Errors, CCDictionary(CCString, uint8_t) Labels, CCDictionary(CCString, uint8_t) Defines, const HKHubArchAssemblySymbolExpansion *Expansion);

/*!
 * @brief Decode an instruction from binary.
 * @param Offset The offset the instruction is located at.
 * @param Data The data that contains the instruction.
 * @param Decoded The pointer to store the decoded state. May be null.
 * @return The offset after the instruction.
 */
uint8_t HKHubArchInstructionDecode(uint8_t Offset, uint8_t Data[256], HKHubArchInstructionState *Decoded);

/*!
 * @brief Get the size of the encoded instruction state.
 * @param State The state for the instruction.
 * @return The size of the encoding.
 */
size_t HKHubArchInstructionSizeOfEncoding(const HKHubArchInstructionState *State);

/*!
 * @brief Check whether a given instruction has predictable flow.
 * @description A predictable flow refers to an instruction that when executed will move immediately to the
 *              instruction below it. Instructions that may stall (temporarily or persistently), branch,
 *              or modify the PC register are all examples of unpredictable flow.
 *
 * @note This should only be used as a hint. A true result means the the flow is guaranteed to be predictable,
 *       while a false result means it cannot be sure.
 *
 * @param State The state for the instruction.
 * @return Whether the instruction has predictable flow.
 */
_Bool HKHubArchInstructionPredictableFlow(const HKHubArchInstructionState *State);

/*!
 * @brief Check what flags an instruction will read/depend on.
 * @param State The state for the instruction.
 * @return What flags the instruction reads.
 */
HKHubArchProcessorFlags HKHubArchInstructionReadFlags(const HKHubArchInstructionState *State);

/*!
 * @brief Check what flags an instruction writes.
 * @description This is the same as @b HKHubArchInstructionGetModifiedFlags but also includes if the flags
 *              register is a destination.
 *
 * @param State The state for the instruction.
 * @return What flags the instruction writes.
 */
HKHubArchProcessorFlags HKHubArchInstructionWriteFlags(const HKHubArchInstructionState *State);

/*!
 * @brief Get the control flow of the instruction.
 * @param State The state for the instruction.
 * @return The control flow.
 */
HKHubArchInstructionControlFlow HKHubArchInstructionGetControlFlow(const HKHubArchInstructionState *State);

/*!
 * @brief Get the flags this instruction modifies.
 * @note This does not include if the flags register is modified due to being the destination.
 * @param State The state for the instruction.
 * @return The modified flags.
 */
HKHubArchProcessorFlags HKHubArchInstructionGetModifiedFlags(const HKHubArchInstructionState *State);

/*!
 * @brief Get the memory operation of the instruction.
 * @param State The state for the instruction.
 * @return The memory operation.
 */
HKHubArchInstructionMemoryOperation HKHubArchInstructionGetMemoryOperation(const HKHubArchInstructionState *State);

/*!
 * @brief Disassemble an instruction from state.
 * @param State The pointer to decoded instruction state.
 * @return The disassembly or 0 on failure. Must be destroyed to free memory.
 */
CC_NEW CCString HKHubArchInstructionDisassemble(const HKHubArchInstructionState *State);

/*!
 * @brief Execute an instruction on a given processor with the given state.
 * @description Updates the processor's cycle count and any other state. Cycles are calculated for the operation
 *              alone.
 *
 * @param Processor The processor to execute the operation in.
 * @param State The state for the instruction to be executed.
 * @return The result type of the executed operation.
 */
HKHubArchInstructionOperationResult HKHubArchInstructionExecute(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);

#endif
