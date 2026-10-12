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

#include "HubArchInstruction.h"


#pragma mark Instructions

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationMOV(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationADD(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationSUB(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationMUL(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationSDIV(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationUDIV(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationSMOD(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationUMOD(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationCMP(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationSHL(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationSHR(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationXOR(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationOR(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationAND(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationNOT(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationNEG(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationHLT(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationSEND(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationRECV(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJMP(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJZ(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJNZ(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJS(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJNS(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJO(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJNO(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJSL(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJSGE(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJSLE(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJSG(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJUL(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJUGE(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJULE(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);
static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJUG(HKHubArchProcessor Processor, const HKHubArchInstructionState *State);


static const struct {
    CCString mnemonic;
    HKHubArchInstructionOperation operation;
    HKHubArchInstructionOperand operands[3];
    HKHubArchInstructionMemoryOperation memory;
    HKHubArchInstructionControlFlow control;
    HKHubArchProcessorFlags flags;
} Instructions[64] = {
    { CC_STRING("add")     , HKHubArchInstructionOperationADD,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("add")     , HKHubArchInstructionOperationADD,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandI,   HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("mov")     , HKHubArchInstructionOperationMOV,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationDS },
    { CC_STRING("jz")      , HKHubArchInstructionOperationJZ,   { HKHubArchInstructionOperandRel, HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationS, HKHubArchInstructionControlFlowEffectBranch | HKHubArchInstructionControlFlowEvaluationConditional },
    { CC_STRING("sub")     , HKHubArchInstructionOperationSUB,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("sub")     , HKHubArchInstructionOperationSUB,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandI,   HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("mov")     , HKHubArchInstructionOperationMOV,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandI,   HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationDS },
    { CC_STRING("jnz")     , HKHubArchInstructionOperationJNZ,  { HKHubArchInstructionOperandRel, HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationS, HKHubArchInstructionControlFlowEffectBranch | HKHubArchInstructionControlFlowEvaluationConditional },
    { CC_STRING("mul")     , HKHubArchInstructionOperationMUL,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("mul")     , HKHubArchInstructionOperationMUL,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandI,   HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { 0                    , NULL,                              { HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA } },
    { CC_STRING("js")      , HKHubArchInstructionOperationJS,   { HKHubArchInstructionOperandRel, HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationS, HKHubArchInstructionControlFlowEffectBranch | HKHubArchInstructionControlFlowEvaluationConditional },
    { CC_STRING("sdiv")    , HKHubArchInstructionOperationSDIV, { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("sdiv")    , HKHubArchInstructionOperationSDIV, { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandI,   HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { 0                    , NULL,                              { HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA } },
    { CC_STRING("jns")     , HKHubArchInstructionOperationJNS,  { HKHubArchInstructionOperandRel, HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationS, HKHubArchInstructionControlFlowEffectBranch | HKHubArchInstructionControlFlowEvaluationConditional },
    { CC_STRING("udiv")    , HKHubArchInstructionOperationUDIV, { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("udiv")    , HKHubArchInstructionOperationUDIV, { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandI,   HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { 0                    , NULL,                              { HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA } },
    { CC_STRING("jo")      , HKHubArchInstructionOperationJO,   { HKHubArchInstructionOperandRel, HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationS, HKHubArchInstructionControlFlowEffectBranch | HKHubArchInstructionControlFlowEvaluationConditional },
    { CC_STRING("smod")    , HKHubArchInstructionOperationSMOD, { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("smod")    , HKHubArchInstructionOperationSMOD, { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandI,   HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { 0                    , NULL,                              { HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA } },
    { CC_STRING("jno")     , HKHubArchInstructionOperationJNO,  { HKHubArchInstructionOperandRel, HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationS, HKHubArchInstructionControlFlowEffectBranch | HKHubArchInstructionControlFlowEvaluationConditional },
    { CC_STRING("umod")    , HKHubArchInstructionOperationUMOD, { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("umod")    , HKHubArchInstructionOperationUMOD, { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandI,   HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { 0                    , NULL,                              { HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA } },
    { CC_STRING("send")    , HKHubArchInstructionOperationSEND, { HKHubArchInstructionOperandR,   HKHubArchInstructionOperandR,   HKHubArchInstructionOperandM  }, HKHubArchInstructionMemoryOperationSSS, HKHubArchInstructionControlFlowEffectIO, HKHubArchProcessorFlagsZero },
    { CC_STRING("cmp")     , HKHubArchInstructionOperationCMP,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationSS, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("cmp")     , HKHubArchInstructionOperationCMP,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandI,   HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationSS, .flags = HKHubArchProcessorFlagsMask },
    { 0                    , NULL,                              { HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA } },
    { CC_STRING("send")    , HKHubArchInstructionOperationSEND, { HKHubArchInstructionOperandR,   HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationS, HKHubArchInstructionControlFlowEffectIO, HKHubArchProcessorFlagsZero },
    { CC_STRING("shl")     , HKHubArchInstructionOperationSHL,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("shl")     , HKHubArchInstructionOperationSHL,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandI,   HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { 0                    , NULL,                              { HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA } },
    { CC_STRING("send")    , HKHubArchInstructionOperationSEND, { HKHubArchInstructionOperandI,   HKHubArchInstructionOperandR,   HKHubArchInstructionOperandM  }, HKHubArchInstructionMemoryOperationSSS, HKHubArchInstructionControlFlowEffectIO, HKHubArchProcessorFlagsZero },
    { CC_STRING("shr")     , HKHubArchInstructionOperationSHR,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("shr")     , HKHubArchInstructionOperationSHR,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandI,   HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { 0                    , NULL,                              { HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA } },
    { CC_STRING("recv")    , HKHubArchInstructionOperationRECV, { HKHubArchInstructionOperandR,   HKHubArchInstructionOperandM,   HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationSD, HKHubArchInstructionControlFlowEffectIO, HKHubArchProcessorFlagsZero },
    { CC_STRING("xor")     , HKHubArchInstructionOperationXOR,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("xor")     , HKHubArchInstructionOperationXOR,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandI,   HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { 0                    , NULL,                              { HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA } },
    { CC_STRING("send")    , HKHubArchInstructionOperationSEND, { HKHubArchInstructionOperandR,   HKHubArchInstructionOperandI,   HKHubArchInstructionOperandM  }, HKHubArchInstructionMemoryOperationSSS, HKHubArchInstructionControlFlowEffectIO, HKHubArchProcessorFlagsZero },
    { CC_STRING("or")      , HKHubArchInstructionOperationOR,   { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("or")      , HKHubArchInstructionOperationOR,   { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandI,   HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("neg")     , HKHubArchInstructionOperationNEG,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationB, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("send")    , HKHubArchInstructionOperationSEND, { HKHubArchInstructionOperandI,   HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationS, HKHubArchInstructionControlFlowEffectIO, HKHubArchProcessorFlagsZero },
    { CC_STRING("and")     , HKHubArchInstructionOperationAND,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("and")     , HKHubArchInstructionOperationAND,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandI,   HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationBS, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("not")     , HKHubArchInstructionOperationNOT,  { HKHubArchInstructionOperandRM,  HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationB, .flags = HKHubArchProcessorFlagsMask },
    { CC_STRING("hlt")     , HKHubArchInstructionOperationHLT,  { HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, .control = HKHubArchInstructionControlFlowEffectPause },
    { CC_STRING("jsl")     , HKHubArchInstructionOperationJSL,  { HKHubArchInstructionOperandRel, HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationS, HKHubArchInstructionControlFlowEffectBranch | HKHubArchInstructionControlFlowEvaluationConditional },
    { CC_STRING("jsge")    , HKHubArchInstructionOperationJSGE, { HKHubArchInstructionOperandRel, HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationS, HKHubArchInstructionControlFlowEffectBranch | HKHubArchInstructionControlFlowEvaluationConditional },
    { CC_STRING("jsle")    , HKHubArchInstructionOperationJSLE, { HKHubArchInstructionOperandRel, HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationS, HKHubArchInstructionControlFlowEffectBranch | HKHubArchInstructionControlFlowEvaluationConditional },
    { CC_STRING("jsg")     , HKHubArchInstructionOperationJSG,  { HKHubArchInstructionOperandRel, HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationS, HKHubArchInstructionControlFlowEffectBranch | HKHubArchInstructionControlFlowEvaluationConditional },
    { CC_STRING("jul")     , HKHubArchInstructionOperationJUL,  { HKHubArchInstructionOperandRel, HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationS, HKHubArchInstructionControlFlowEffectBranch | HKHubArchInstructionControlFlowEvaluationConditional },
    { CC_STRING("juge")    , HKHubArchInstructionOperationJUGE, { HKHubArchInstructionOperandRel, HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationS, HKHubArchInstructionControlFlowEffectBranch | HKHubArchInstructionControlFlowEvaluationConditional },
    { CC_STRING("jule")    , HKHubArchInstructionOperationJULE, { HKHubArchInstructionOperandRel, HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationS, HKHubArchInstructionControlFlowEffectBranch | HKHubArchInstructionControlFlowEvaluationConditional },
    { CC_STRING("jug")     , HKHubArchInstructionOperationJUG,  { HKHubArchInstructionOperandRel, HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationS, HKHubArchInstructionControlFlowEffectBranch | HKHubArchInstructionControlFlowEvaluationConditional },
    { CC_STRING("send")    , HKHubArchInstructionOperationSEND, { HKHubArchInstructionOperandI,   HKHubArchInstructionOperandI,   HKHubArchInstructionOperandM  }, HKHubArchInstructionMemoryOperationSSS, HKHubArchInstructionControlFlowEffectIO, HKHubArchProcessorFlagsZero },
    { CC_STRING("recv")    , HKHubArchInstructionOperationRECV, { HKHubArchInstructionOperandI,   HKHubArchInstructionOperandM,   HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationSD, HKHubArchInstructionControlFlowEffectIO, HKHubArchProcessorFlagsZero },
    { CC_STRING("nop")     , NULL,                              { HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA } },
    { CC_STRING("jmp")     , HKHubArchInstructionOperationJMP,  { HKHubArchInstructionOperandRel, HKHubArchInstructionOperandNA,  HKHubArchInstructionOperandNA }, HKHubArchInstructionMemoryOperationS, HKHubArchInstructionControlFlowEffectBranch }
};

static const struct {
    CCString mnemonic;
    uint8_t encoding;
} Registers[6] = {
    { CC_STRING("r0"),      HKHubArchInstructionRegisterR0 },
    { CC_STRING("r1"),      HKHubArchInstructionRegisterR1 },
    { CC_STRING("r2"),      HKHubArchInstructionRegisterR2 },
    { CC_STRING("r3"),      HKHubArchInstructionRegisterR3 },
    { CC_STRING("flags"),   HKHubArchInstructionRegisterFlags },
    { CC_STRING("pc"),      HKHubArchInstructionRegisterPC },
};

#pragma mark - Error Messages

static const CCString HKHubArchInstructionErrorMessageUnknownMnemonic = CC_STRING("no instruction with name available");
static const CCString HKHubArchInstructionErrorMessageUnknownOperands = CC_STRING("incorrect operands");
static const CCString HKHubArchInstructionErrorMessageMin0Max3Operands = CC_STRING("expects 0 to 3 operands");
static const CCString HKHubArchInstructionErrorMessageResolveOperand = CC_STRING("unknown operand");
static const CCString HKHubArchInstructionErrorMessageMemoryRegister = CC_STRING("only general purpose registers r0, r1, r2, r3 may be used as memory references");
static const CCString HKHubArchInstructionErrorMessageMin0Max2MemoryRegister = CC_STRING("expects 0 to 2 registers");
static const CCString HKHubArchInstructionErrorMessageMemoryAdditionOnly = CC_STRING("addition is the only arithmetic operation available for 2 register memory references");

#pragma mark -

CC_DICTIONARY_DECLARE(HKHubArchInstructionKey, size_t);

static CCDictionary(CCString, uint8_t) RegularRegisters = NULL, MemoryRegisters = NULL;
static CCDictionary(HKHubArchInstructionKey, size_t) InstructionTable = NULL;

static HKHubArchInstructionOperand HKHubArchInstructionResolveOperand(HKHubArchAssemblyASTNode *Operand, CCOrderedCollection(HKHubArchAssemblyASTError) Errors, CCDictionary(CCString, uint8_t) Labels, CCDictionary(CCString, uint8_t) Defines)
{
    if (Operand->type == HKHubArchAssemblyASTTypeMemory) return HKHubArchInstructionOperandM;
    
    if (Operand->childNodes)
    {
        const size_t Count = CCCollectionGetCount(Operand->childNodes);
        if (Count == 1)
        {
            HKHubArchAssemblyASTNode *Value = CCOrderedCollectionGetElementAtIndex(Operand->childNodes, 0);
            switch (Value->type)
            {
                case HKHubArchAssemblyASTTypeInteger:
                case HKHubArchAssemblyASTTypeOffset:
                case HKHubArchAssemblyASTTypeRandom:
                case HKHubArchAssemblyASTTypeExpression:
                    return HKHubArchInstructionOperandI;
                    
                case HKHubArchAssemblyASTTypeSymbol:
                    if (CCDictionaryFindKey(RegularRegisters, &Value->string)) return HKHubArchInstructionOperandR;
                    return HKHubArchInstructionOperandI;
                    
                default:
                    break;
            }
        }
        
        else if (Count > 1) return HKHubArchInstructionOperandI;
    }
    
    return HKHubArchInstructionOperandNA;
}

typedef struct {
    CCString mnemonic;
    HKHubArchInstructionOperand operands[3];
} HKHubArchInstructionKey;

static uintmax_t HKHubArchInstructionKeyHasher(const HKHubArchInstructionKey *Key)
{
    return CCStringGetHash(Key->mnemonic);
}

static _Thread_local _Bool MatchedMnemonic = FALSE;
static CCComparisonResult HKHubArchInstructionKeyComparator(const HKHubArchInstructionKey *left, const HKHubArchInstructionKey *right)
{
    const _Bool Match = CCStringEqual(left->mnemonic, right->mnemonic);
    if (!MatchedMnemonic) MatchedMnemonic = Match;
    
    return (Match && (left->operands[0] & right->operands[0]) && (left->operands[1] & right->operands[1]) && (left->operands[2] & right->operands[2])) ? CCComparisonResultEqual : CCComparisonResultInvalid;
}

static _Atomic(int) InitStatus = ATOMIC_VAR_INIT(0);
size_t HKHubArchInstructionEncode(size_t Offset, uint8_t Data[256], HKHubArchAssemblyASTNode *Command, CCOrderedCollection(HKHubArchAssemblyASTError) Errors, CCDictionary(CCString, uint8_t) Labels, CCDictionary(CCString, uint8_t) Defines, const HKHubArchAssemblySymbolExpansion *Expansion)
{
    CCAssertLog(Command, "Command must not be null");
    
    switch (atomic_load_explicit(&InitStatus, memory_order_relaxed))
    {
        case 0:
            if (atomic_compare_exchange_strong_explicit(&InitStatus, &(int){ 0 }, 1, memory_order_relaxed, memory_order_relaxed))
            {
                const CCDictionaryCallbacks Callbacks = {
                    .getHash = CCStringHasherForDictionary,
                    .compareKeys = CCStringComparatorForDictionary
                };
                const CCDictionaryHint ConstantHint = CCDictionaryHintConstantElements | CCDictionaryHintConstantLength;
                RegularRegisters = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeSmall | ConstantHint, sizeof(CCString), sizeof(uint8_t), &Callbacks);
                MemoryRegisters = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeSmall | ConstantHint, sizeof(CCString), sizeof(uint8_t), &Callbacks);
                
                for (size_t Loop = 0; Loop < 4; Loop++)
                {
                    CCDictionarySetValue(RegularRegisters, (void*)&Registers[Loop].mnemonic, &Registers[Loop].encoding);
                    CCDictionarySetValue(MemoryRegisters, (void*)&Registers[Loop].mnemonic, &Registers[Loop].encoding);
                }
                
                CCDictionarySetValue(RegularRegisters, (void*)&Registers[4].mnemonic, &Registers[4].encoding);
                CCDictionarySetValue(RegularRegisters, (void*)&Registers[5].mnemonic, &Registers[5].encoding);
                
                
                InstructionTable = CCDictionaryCreate(CC_STD_ALLOCATOR, CCCollectionHintSizeMedium | ConstantHint, sizeof(HKHubArchInstructionKey), sizeof(size_t), &(CCDictionaryCallbacks){
                    .getHash = (CCDictionaryKeyHasher)HKHubArchInstructionKeyHasher,
                    .compareKeys = (CCComparator)HKHubArchInstructionKeyComparator
                });
                
                for (size_t Loop = 0; Loop < sizeof(Instructions) / sizeof(typeof(*Instructions)); Loop++)
                {
                    if (Instructions[Loop].mnemonic)
                    {
                        CCDictionarySetValue(InstructionTable, &(HKHubArchInstructionKey){
                            .mnemonic = Instructions[Loop].mnemonic,
                            .operands = { Instructions[Loop].operands[0], Instructions[Loop].operands[1], Instructions[Loop].operands[2] }
                        }, &Loop);
                    }
                }
                
                atomic_store_explicit(&InitStatus, 2, memory_order_release);
                break;
            }
        case 1:
            while (atomic_load_explicit(&InitStatus, memory_order_acquire) != 2) CC_SPIN_WAIT();
            break;
            
        default:
            break;
    }
    
    HKHubArchInstructionOperand Operands[3] = { HKHubArchInstructionOperandNA, HKHubArchInstructionOperandNA, HKHubArchInstructionOperandNA };
    if (Command->childNodes)
    {
        if (CCCollectionGetCount(Command->childNodes) <= 3)
        {
            size_t Index = 0;
            CC_COLLECTION_FOREACH_PTR(HKHubArchAssemblyASTNode, Operand, Command->childNodes)
            {
                Operands[Index] = HKHubArchInstructionResolveOperand(Operand, Errors, Labels, Defines);
                Index++;
            }
        }
        
        else
        {
            HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchInstructionErrorMessageMin0Max3Operands, Command, NULL, NULL);
            
            return Offset;
        }
    }
    
    MatchedMnemonic = FALSE;
    size_t *InstructionIndex = CCDictionaryGetValue(InstructionTable, &(HKHubArchInstructionKey){
        .mnemonic = Command->string,
        .operands = { Operands[0], Operands[1], Operands[2] }
    });
    
    if (InstructionIndex)
    {
        size_t Count = 0, BitCount = 6;
        uint8_t Bytes[5] = { *InstructionIndex << 2, 0, 0, 0, 0 };
        
        for (size_t Index = 0; Index < 3; Index++)
        {
            size_t FreeBits = 8 - (BitCount % 8);
            if (Operands[Index] & HKHubArchInstructionOperandI)
            {
                HKHubArchAssemblyASTNode *Op = CCOrderedCollectionGetElementAtIndex(Command->childNodes, Index);
                if (Op->childNodes)
                {
                    uint8_t Result;
                    if (HKHubArchAssemblyResolveInteger(Offset, &Result, Command, Op, Errors, Labels, Defines, NULL, Expansion))
                    {
                        if (Instructions[*InstructionIndex].operands[Index] == HKHubArchInstructionOperandRel) Result -= Offset;
                        
                        Bytes[Count++] |= Result >> (8 - FreeBits);
                        Bytes[Count] = (Result & CCBitSet(8 - FreeBits)) << FreeBits;
                    }
                    
                    else HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchInstructionErrorMessageResolveOperand, Command, Op, NULL);
                }
                
                else HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchInstructionErrorMessageResolveOperand, Command, Op, NULL);
                
                BitCount += 8;
            }
            
            else if (Operands[Index] & HKHubArchInstructionOperandR)
            {
                HKHubArchAssemblyASTNode *Op = CCOrderedCollectionGetElementAtIndex(Command->childNodes, Index);
                if ((Op->childNodes) && (CCCollectionGetCount(Op->childNodes) == 1))
                {
                    HKHubArchAssemblyASTNode *Value = CCOrderedCollectionGetElementAtIndex(Op->childNodes, 0);
                    if (Value->type == HKHubArchAssemblyASTTypeSymbol)
                    {
                        const uint8_t *Encoding = CCDictionaryGetValue(RegularRegisters, &Value->string);
                        if (Encoding)
                        {
                            if (FreeBits <= 3)
                            {
                                Bytes[Count++] |= *Encoding >> (3 - FreeBits);
                                Bytes[Count] = (*Encoding & CCBitSet(3 - FreeBits)) << (8 - (3 - FreeBits));
                            }
                            
                            else Bytes[Count] |= (*Encoding & CCBitSet(FreeBits)) << (FreeBits - 3);
                        }
                    }
                }
                
                else HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchInstructionErrorMessageResolveOperand, Command, Op, NULL);
                
                BitCount += 3;
            }
            
            else if (Operands[Index] & HKHubArchInstructionOperandM)
            {
                HKHubArchAssemblyASTNode *Memory = CCOrderedCollectionGetElementAtIndex(Command->childNodes, Index);
                if ((Memory->childNodes) && (CCCollectionGetCount(Memory->childNodes) == 1))
                {
                    HKHubArchAssemblyASTNode *Op = CCOrderedCollectionGetElementAtIndex(Memory->childNodes, 0);
                    
                    if (Op->childNodes)
                    {
                        size_t RegIndex = 0;
                        uint8_t Regs[2] = { HKHubArchInstructionRegisterGeneralPurpose, HKHubArchInstructionRegisterGeneralPurpose };
                        
                        CC_COLLECTION_FOREACH_PTR(HKHubArchAssemblyASTNode, Value, Op->childNodes)
                        {
                            if (Value->type == HKHubArchAssemblyASTTypeSymbol)
                            {
                                const uint8_t *Encoding = CCDictionaryGetValue(RegularRegisters, &Value->string);
                                if (Encoding)
                                {
                                    if (RegIndex < 2)
                                    {
                                        Regs[RegIndex] = *Encoding;
                                    }
                                    
                                    RegIndex++;
                                }
                            }
                        }
                        
                        if ((Regs[0] & HKHubArchInstructionRegisterGeneralPurpose) && (Regs[1] & HKHubArchInstructionRegisterGeneralPurpose))
                        {
                            /*
                             0000 iiiiiiii - Immediate address
                             0001 rr - Register address (r0 - r3)
                             0010 iiiiiiii rr - Immediate + Register address (r0 - r3)
                             0011 rr rr - Register + Register address (r0 - r3)
                             */
                            switch (RegIndex)
                            {
                                case 0: //integer
                                {
                                    uint8_t MemoryType = HKHubArchInstructionMemoryOffset;
                                    if (FreeBits <= 4)
                                    {
                                        Bytes[Count++] |= MemoryType >> (4 - FreeBits);
                                        Bytes[Count] = (MemoryType & CCBitSet(4 - FreeBits)) << (8 - (4 - FreeBits));
                                    }
                                    
                                    else Bytes[Count] |= (MemoryType & CCBitSet(FreeBits)) << (FreeBits - 4);
                                    
                                    BitCount += 4;
                                    FreeBits = 8 - (BitCount % 8);
                                    
                                    uint8_t Result;
                                    if (HKHubArchAssemblyResolveInteger(Offset, &Result, Command, Op, Errors, Labels, Defines, NULL, Expansion))
                                    {
                                        Bytes[Count++] |= Result >> (8 - FreeBits);
                                        Bytes[Count] = (Result & CCBitSet(8 - FreeBits)) << FreeBits;
                                    }
                                    
                                    else HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchInstructionErrorMessageResolveOperand, Command, Op, NULL);
                                    
                                    BitCount += 8;
                                    break;
                                }
                                    
                                case 1: //reg or reg+integer/reg-integer
                                {
                                    const size_t OpCount = CCCollectionGetCount(Op->childNodes);
                                    if (OpCount == 1) //reg
                                    {
                                        uint8_t Memory = (HKHubArchInstructionMemoryRegister << 2) | (Regs[0] & HKHubArchInstructionRegisterGeneralPurposeIndexMask);
                                        if (FreeBits <= 6)
                                        {
                                            Bytes[Count++] |= Memory >> (6 - FreeBits);
                                            Bytes[Count] = (Memory & CCBitSet(6 - FreeBits)) << (8 - (6 - FreeBits));
                                        }
                                        
                                        else Bytes[Count] |= (Memory & CCBitSet(FreeBits)) << (FreeBits - 6);
                                        
                                        BitCount += 6;
                                    }
                                    
                                    else if (OpCount >= 3) //reg+integer/reg-integer
                                    {
                                        uint8_t MemoryType = HKHubArchInstructionMemoryRelativeOffset;
                                        if (FreeBits <= 4)
                                        {
                                            Bytes[Count++] |= MemoryType >> (4 - FreeBits);
                                            Bytes[Count] = (MemoryType & CCBitSet(4 - FreeBits)) << (8 - (4 - FreeBits));
                                        }
                                        
                                        else Bytes[Count] |= (MemoryType & CCBitSet(FreeBits)) << (FreeBits - 4);
                                        
                                        BitCount += 4;
                                        FreeBits = 8 - (BitCount % 8);
                                        
                                        uint8_t Result;
                                        if (HKHubArchAssemblyResolveInteger(Offset, &Result, Command, Op, Errors, Labels, Defines, MemoryRegisters, Expansion))
                                        {
                                            Bytes[Count++] |= Result >> (8 - FreeBits);
                                            Bytes[Count] = (Result & CCBitSet(8 - FreeBits)) << FreeBits;
                                        }
                                        
                                        else HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchInstructionErrorMessageResolveOperand, Command, Op, NULL);
                                        
                                        BitCount += 8;
                                        
                                        uint8_t Memory = Regs[0] & HKHubArchInstructionRegisterGeneralPurposeIndexMask;
                                        if (FreeBits <= 2)
                                        {
                                            Bytes[Count++] |= Memory >> (2 - FreeBits);
                                            Bytes[Count] = (Memory & CCBitSet(2 - FreeBits)) << (8 - (2 - FreeBits));
                                        }
                                        
                                        else Bytes[Count] |= (Memory & CCBitSet(FreeBits)) << (FreeBits - 2);
                                        
                                        BitCount += 2;
                                    }
                                    
                                    else HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchInstructionErrorMessageResolveOperand, Command, Memory, NULL);
                                    
                                    break;
                                }
                                    
                                case 2: //reg+reg
                                {
                                    if (CCCollectionGetCount(Op->childNodes) == 3)
                                    {
                                        HKHubArchAssemblyASTNode *Operation = CCOrderedCollectionGetElementAtIndex(Op->childNodes, 1);
                                        if (Operation->type == HKHubArchAssemblyASTTypePlus)
                                        {
                                            uint8_t Memory = (HKHubArchInstructionMemoryRelativeRegister << 4) | ((Regs[0] & HKHubArchInstructionRegisterGeneralPurposeIndexMask) << 2) | (Regs[1] & HKHubArchInstructionRegisterGeneralPurposeIndexMask); //type|reg1|reg2
                                            Bytes[Count++] |= Memory >> (8 - FreeBits);
                                            Bytes[Count] = (Memory & CCBitSet(8 - FreeBits)) << FreeBits;
                                            
                                            BitCount += 8;
                                        }
                                        
                                        else HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchInstructionErrorMessageMemoryAdditionOnly, Command, Op, Operation);
                                    }
                                    
                                    else HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchInstructionErrorMessageResolveOperand, Command, Memory, NULL);
                                    
                                    break;
                                }
                                    
                                default:
                                    HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchInstructionErrorMessageMin0Max2MemoryRegister, Command, Memory, NULL);
                                    break;
                            }
                        }
                        
                        else HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchInstructionErrorMessageMemoryRegister, Command, Memory, NULL);
                    }
                    
                    else HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchInstructionErrorMessageResolveOperand, Command, Memory, NULL);
                }
                
                else HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchInstructionErrorMessageResolveOperand, Command, Memory, NULL);
            }
        }
        
        const size_t ByteCount = (BitCount / 8) + (_Bool)(BitCount % 8);
        if (Data) memcpy(&Data[Offset], Bytes, ByteCount);
        
        return Offset + ByteCount;
    }
    
    HKHubArchAssemblyErrorAddMessage(Errors, (MatchedMnemonic ? HKHubArchInstructionErrorMessageUnknownOperands : HKHubArchInstructionErrorMessageUnknownMnemonic), Command, NULL, NULL);
    
    return Offset;
}

uint8_t HKHubArchInstructionDecode(uint8_t Offset, uint8_t Data[256], HKHubArchInstructionState *Decoded)
{
    CCAssertLog(Data, "Data must not be null");
    
    HKHubArchInstructionState State = { .opcode = -1, .operand = { { .type = HKHubArchInstructionOperandNA }, { .type = HKHubArchInstructionOperandNA }, { .type = HKHubArchInstructionOperandNA } } };
    uint8_t Byte = Data[Offset++];
    
    uint8_t FreeBits = 2;
    const uint8_t Opcode = Byte >> 2;
    if (Instructions[Opcode].mnemonic)
    {
        State.opcode = Opcode;
        
        for (int Loop = 0; (Loop < 3) && (Instructions[Opcode].operands[Loop] != HKHubArchInstructionOperandNA); Loop++)
        {
            if (FreeBits == 0)
            {
                FreeBits = 8;
                Byte = Data[Offset++];
            }
            
            if (Instructions[Opcode].operands[Loop] & HKHubArchInstructionOperandI)
            {
                uint8_t Value = (Byte & CCBitSet(FreeBits)) << (8 - FreeBits);
                if (FreeBits != 8)
                {
                    Byte = Data[Offset++];
                    Value |= Byte >> FreeBits;
                }
                
                else FreeBits = 0;
                
                State.operand[Loop] = (HKHubArchInstructionOperandValue){ .type = HKHubArchInstructionOperandI, .value = Value };
            }
            
            else if (Instructions[Opcode].operands[Loop] & HKHubArchInstructionOperandRM)
            {
                uint8_t Reg = Byte & CCBitSet(FreeBits);
                if (FreeBits < 3)
                {
                    Byte = Data[Offset++];
                    Reg = (Reg << (3 - FreeBits)) | (Byte >> (8 - (3 - FreeBits)));
                    FreeBits = 8 - (3 - FreeBits);
                }
                
                else
                {
                    if (FreeBits > 3) Reg >>= (FreeBits - 3);
                    FreeBits -= 3;
                }
                
                if (Reg & (HKHubArchInstructionRegisterGeneralPurpose | HKHubArchInstructionRegisterSpecialPurpose))
                {
                    if (Instructions[Opcode].operands[Loop] & HKHubArchInstructionOperandR) State.operand[Loop] = (HKHubArchInstructionOperandValue){ .type = HKHubArchInstructionOperandR, .reg = Reg };
                    else State.opcode = -1;
                }
                
                else if (Instructions[Opcode].operands[Loop] & HKHubArchInstructionOperandM)
                {
                    uint8_t Memory = Byte & CCBitSet(FreeBits);
                    if (FreeBits < 1)
                    {
                        Byte = Data[Offset++];
                        Memory = (Memory << (1 - FreeBits)) | (Byte >> (8 - (1 - FreeBits)));
                        FreeBits = 8 - (1 - FreeBits);
                    }
                    
                    else
                    {
                        if (FreeBits > 1) Memory >>= (FreeBits - 1);
                        FreeBits -= 1;
                    }
                    
                    Memory |= Reg << 1;
                    
                    switch (Memory)
                    {
                        case HKHubArchInstructionMemoryOffset:
                        {
                            uint8_t Value = (Byte & CCBitSet(FreeBits)) << (8 - FreeBits);
                            if (FreeBits != 8)
                            {
                                Byte = Data[Offset++];
                                Value |= Byte >> FreeBits;
                            }
                            
                            else FreeBits = 0;
                            
                            State.operand[Loop] = (HKHubArchInstructionOperandValue){ .type = HKHubArchInstructionOperandM, .memory = { .type = Memory, .offset = Value } };
                            break;
                        }
                            
                        case HKHubArchInstructionMemoryRegister:
                            Reg = Byte & CCBitSet(FreeBits);
                            if (FreeBits < 2)
                            {
                                Byte = Data[Offset++];
                                Reg = (Reg << (2 - FreeBits)) | (Byte >> (8 - (2 - FreeBits)));
                                FreeBits = 8 - (2 - FreeBits);
                            }
                            
                            else
                            {
                                if (FreeBits > 2) Reg >>= (FreeBits - 2);
                                FreeBits -= 2;
                            }
                            
                            State.operand[Loop] = (HKHubArchInstructionOperandValue){ .type = HKHubArchInstructionOperandM, .memory = { .type = Memory, .reg = Reg | HKHubArchInstructionRegisterGeneralPurpose } };
                            break;
                            
                        case HKHubArchInstructionMemoryRelativeOffset:
                        {
                            uint8_t Value = (Byte & CCBitSet(FreeBits)) << (8 - FreeBits);
                            if (FreeBits != 8)
                            {
                                Byte = Data[Offset++];
                                Value |= Byte >> FreeBits;
                            }
                            
                            else FreeBits = 0;
                            
                            Reg = Byte & CCBitSet(FreeBits);
                            if (FreeBits < 2)
                            {
                                Byte = Data[Offset++];
                                Reg = (Reg << (2 - FreeBits)) | (Byte >> (8 - (2 - FreeBits)));
                                FreeBits = 8 - (2 - FreeBits);
                            }
                            
                            else
                            {
                                if (FreeBits > 2) Reg >>= (FreeBits - 2);
                                FreeBits -= 2;
                            }
                            
                            State.operand[Loop] = (HKHubArchInstructionOperandValue){ .type = HKHubArchInstructionOperandM, .memory = { .type = Memory, .relativeOffset = { .offset = Value, .reg = Reg | HKHubArchInstructionRegisterGeneralPurpose } } };
                            break;
                        }
                            
                        case HKHubArchInstructionMemoryRelativeRegister:
                            Reg = Byte & CCBitSet(FreeBits);
                            if (FreeBits < 4)
                            {
                                Byte = Data[Offset++];
                                Reg = (Reg << (4 - FreeBits)) | (Byte >> (8 - (4 - FreeBits)));
                                FreeBits = 8 - (4 - FreeBits);
                            }
                            
                            else
                            {
                                if (FreeBits > 4) Reg >>= (FreeBits - 4);
                                FreeBits -= 4;
                            }
                            
                            State.operand[Loop] = (HKHubArchInstructionOperandValue){ .type = HKHubArchInstructionOperandM, .memory = { .type = Memory, .relativeReg = { (Reg >> 2) | HKHubArchInstructionRegisterGeneralPurpose, (Reg & 3) | HKHubArchInstructionRegisterGeneralPurpose } } };
                            break;
                    }
                }
                
                else State.opcode = -1;
            }
        }
    }
    
    if (Decoded) *Decoded = State;
    
    return Offset;
}

size_t HKHubArchInstructionSizeOfEncoding(const HKHubArchInstructionState *State)
{
    CCAssertLog(State, "State must not be null");
    
    size_t InstructionBits = 6;
    for (size_t Loop = 0; (Loop < 3) && (State->operand[Loop].type != HKHubArchInstructionOperandNA); Loop++)
    {
        switch (State->operand[Loop].type)
        {
            case HKHubArchInstructionOperandI:
                InstructionBits += 8;
                break;
                
            case HKHubArchInstructionOperandR:
                InstructionBits += 3;
                break;
                
            case HKHubArchInstructionOperandM:
            {
                InstructionBits += 4;
                
                switch (State->operand[Loop].memory.type)
                {
                    case HKHubArchInstructionMemoryOffset:
                        InstructionBits += 8;
                        break;
                        
                    case HKHubArchInstructionMemoryRegister:
                        InstructionBits += 2;
                        break;
                        
                    case HKHubArchInstructionMemoryRelativeOffset:
                        InstructionBits += 8 + 2;
                        break;
                        
                    case HKHubArchInstructionMemoryRelativeRegister:
                        InstructionBits += 2 + 2;
                        break;
                }
                break;
            }
                
            default:
                CCAssertLog(0, "Should not contain another operand type");
                break;
        }
    }
    
    return (InstructionBits / 8) + (_Bool)(InstructionBits % 8);
}

_Bool HKHubArchInstructionPredictableFlow(const HKHubArchInstructionState *State)
{
    CCAssertLog(State, "State must not be null");
    
    if ((State->opcode != -1) && (Instructions[State->opcode].mnemonic))
    {
        if (Instructions[State->opcode].control & HKHubArchInstructionControlFlowEffectMask) return FALSE;
        
        _Static_assert(HKHubArchInstructionMemoryOperationOp1 == 0 &&
                       HKHubArchInstructionMemoryOperationOp2 == 2 &&
                       HKHubArchInstructionMemoryOperationOp3 == 4, "Expects the following operand mask layout");
        
        const HKHubArchInstructionMemoryOperation Memory = Instructions[State->opcode].memory;
        for (size_t Loop = 0; Loop < 3; Loop++)
        {
            if ((Memory >> (Loop * 2)) & HKHubArchInstructionMemoryOperationDst)
            {
                if (State->operand[Loop].type & HKHubArchInstructionOperandR)
                {
                    if (State->operand[Loop].reg == HKHubArchInstructionRegisterPC) return FALSE;
                }
            }
        }
        
        return TRUE;
    }
            
    return FALSE;
}

HKHubArchProcessorFlags HKHubArchInstructionReadFlags(const HKHubArchInstructionState *State)
{
    const HKHubArchInstructionMemoryOperation MemoryOp = HKHubArchInstructionGetMemoryOperation(State);
    for (size_t Loop = 0; Loop < 3; Loop++)
    {
        _Static_assert(HKHubArchInstructionMemoryOperationOp1 == 0 &&
                       HKHubArchInstructionMemoryOperationOp2 == 2 &&
                       HKHubArchInstructionMemoryOperationOp3 == 4, "Expects the following operand mask layout");
        
        switch (State->operand[Loop].type)
        {
            case HKHubArchInstructionOperandR:
                if (State->operand[Loop].reg == HKHubArchInstructionRegisterFlags)
                {
                    if ((MemoryOp >> (Loop * 2)) & HKHubArchInstructionMemoryOperationSrc) return HKHubArchProcessorFlagsMask;
                }
                break;
                
            case HKHubArchInstructionOperandM:
            {
                switch (State->operand[Loop].memory.type)
                {
                    case HKHubArchInstructionMemoryRegister:
                        if (State->operand[Loop].memory.reg == HKHubArchInstructionRegisterFlags) return HKHubArchProcessorFlagsMask;
                        break;
                        
                    case HKHubArchInstructionMemoryRelativeOffset:
                        if (State->operand[Loop].memory.relativeOffset.reg == HKHubArchInstructionRegisterFlags) return HKHubArchProcessorFlagsMask;
                        break;
                        
                    case HKHubArchInstructionMemoryRelativeRegister:
                        if ((State->operand[Loop].memory.relativeReg[0] == HKHubArchInstructionRegisterFlags) || (State->operand[Loop].memory.relativeReg[1] == HKHubArchInstructionRegisterFlags)) return HKHubArchProcessorFlagsMask;
                        break;
                        
                    default:
                        break;
                }
                
                break;
            }
                
            default:
                break;
        }
    }
    
    static const HKHubArchProcessorFlags FlagDependentInstructions[sizeof(Instructions) / sizeof(typeof(*Instructions))] = {
        0,
        0,
        0,
        HKHubArchProcessorFlagsZero, //jz
        0,
        0,
        0,
        HKHubArchProcessorFlagsZero, //jnz
        0,
        0,
        0,
        HKHubArchProcessorFlagsSign, //js
        0,
        0,
        0,
        HKHubArchProcessorFlagsSign, //jns
        0,
        0,
        0,
        HKHubArchProcessorFlagsOverflow, //jo
        0,
        0,
        0,
        HKHubArchProcessorFlagsOverflow, //jno
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsOverflow, //jsl
        HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsOverflow, //jsge
        HKHubArchProcessorFlagsZero | HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsOverflow, //jsle
        HKHubArchProcessorFlagsZero | HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsOverflow, //jsg
        HKHubArchProcessorFlagsCarry, //jul
        HKHubArchProcessorFlagsCarry, //juge
        HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero, //jule
        HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero, //jug
        0,
        0,
        0,
        0
    };
    
    return FlagDependentInstructions[State->opcode];
}

HKHubArchProcessorFlags HKHubArchInstructionWriteFlags(const HKHubArchInstructionState *State)
{
    HKHubArchProcessorFlags Flags = HKHubArchInstructionGetModifiedFlags(State);
    if (Flags != HKHubArchProcessorFlagsMask)
    {
        const HKHubArchInstructionMemoryOperation MemoryOp = HKHubArchInstructionGetMemoryOperation(State);
        for (size_t Loop = 0; Loop < 3; Loop++)
        {
            _Static_assert(HKHubArchInstructionMemoryOperationOp1 == 0 &&
                           HKHubArchInstructionMemoryOperationOp2 == 2 &&
                           HKHubArchInstructionMemoryOperationOp3 == 4, "Expects the following operand mask layout");
            
            if ((State->operand[Loop].type == HKHubArchInstructionOperandR) && (State->operand[Loop].reg == HKHubArchInstructionRegisterFlags) && ((MemoryOp >> (Loop * 2)) & HKHubArchInstructionMemoryOperationDst)) return HKHubArchProcessorFlagsMask;
        }
    }
    
    return Flags;
}

HKHubArchInstructionControlFlow HKHubArchInstructionGetControlFlow(const HKHubArchInstructionState *State)
{
    CCAssertLog(State, "State must not be null");
    
    HKHubArchInstructionControlFlow Flow = HKHubArchInstructionControlFlowEffectPause;
    if ((State->opcode != -1) && (Instructions[State->opcode].mnemonic))
    {
        Flow = Instructions[State->opcode].control;
    }
    
    return Flow;
}

HKHubArchProcessorFlags HKHubArchInstructionGetModifiedFlags(const HKHubArchInstructionState *State)
{
    CCAssertLog(State, "State must not be null");
    
    HKHubArchProcessorFlags Flags = 0;
    if ((State->opcode != -1) && (Instructions[State->opcode].mnemonic))
    {
        Flags = Instructions[State->opcode].flags;
    }
    
    return Flags;
}

HKHubArchInstructionMemoryOperation HKHubArchInstructionGetMemoryOperation(const HKHubArchInstructionState *State)
{
    CCAssertLog(State, "State must not be null");
    
    HKHubArchInstructionMemoryOperation Operation = 0;
    if ((State->opcode != -1) && (Instructions[State->opcode].mnemonic))
    {
        Operation = Instructions[State->opcode].memory;
    }
    
    return Operation;
}

CCString HKHubArchInstructionDisassemble(const HKHubArchInstructionState *State)
{
    CCAssertLog(State, "State must not be null");
    
    //TODO: Pass in formatting options?
    CCString Disassembly = 0;
    if ((State->opcode != -1) && (Instructions[State->opcode].mnemonic))
    {
        Disassembly = CCStringCopy(Instructions[State->opcode].mnemonic);
        
        for (int Loop = 0; (Loop < 3) && (State->operand[Loop].type != HKHubArchInstructionOperandNA); Loop++)
        {
            switch (State->operand[Loop].type)
            {
                case HKHubArchInstructionOperandI:
                {
                    char Hex[5];
                    snprintf(Hex, sizeof(Hex), State->operand[Loop].value ? "%#.2x" : "0x%#.2x", State->operand[Loop].value);
                    
                    CCString Value = CCStringCreate(CC_STD_ALLOCATOR, (CCStringHint)CCStringEncodingASCII, Hex);
                    CCString Temp = CCStringCreateByJoiningStrings((CCString[2]){ Disassembly, Value }, 2, Loop == 0 ? CC_STRING(" ") : CC_STRING(","));
                    CCStringDestroy(Disassembly);
                    Disassembly = Temp;
                    CCStringDestroy(Value);
                    
                    break;
                }
                    
                case HKHubArchInstructionOperandR:
                    if (State->operand[Loop].reg & HKHubArchInstructionRegisterGeneralPurpose)
                    {
                        CCString Temp = CCStringCreateByJoiningStrings((CCString[2]){ Disassembly, Registers[State->operand[Loop].reg & HKHubArchInstructionRegisterGeneralPurposeIndexMask].mnemonic }, 2, Loop == 0 ? CC_STRING(" ") : CC_STRING(","));
                        CCStringDestroy(Disassembly);
                        Disassembly = Temp;
                    }
                    
                    else if (State->operand[Loop].reg & HKHubArchInstructionRegisterSpecialPurpose)
                    {
                        CCString Temp = CCStringCreateByJoiningStrings((CCString[2]){ Disassembly, Registers[(State->operand[Loop].reg & HKHubArchInstructionRegisterSpecialPurposeIndexMask) + 4].mnemonic }, 2, Loop == 0 ? CC_STRING(" ") : CC_STRING(","));
                        CCStringDestroy(Disassembly);
                        Disassembly = Temp;
                    }
                    break;
                    
                case HKHubArchInstructionOperandM:
                {
                    CCString Memory = 0;
                    switch (State->operand[Loop].memory.type)
                    {
                        case HKHubArchInstructionMemoryOffset:
                        {
                            char Hex[5];
                            snprintf(Hex, sizeof(Hex), State->operand[Loop].memory.offset ? "%#.2x" : "0x%#.2x", State->operand[Loop].memory.offset);
                            
                            CCString Value = CCStringCreate(CC_STD_ALLOCATOR, (CCStringHint)CCStringEncodingASCII, Hex);
                            Memory = CCStringCreateByJoiningStrings((CCString[3]){ CC_STRING("["), Value, CC_STRING("]") }, 3, 0);
                            CCStringDestroy(Value);
                            break;
                        }
                            
                        case HKHubArchInstructionMemoryRegister:
                            Memory = CCStringCreateByJoiningStrings((CCString[3]){ CC_STRING("["), Registers[State->operand[Loop].memory.reg & HKHubArchInstructionRegisterGeneralPurposeIndexMask].mnemonic, CC_STRING("]") }, 3, 0);
                            break;
                            
                        case HKHubArchInstructionMemoryRelativeOffset:
                        {
                            char Hex[5];
                            snprintf(Hex, sizeof(Hex), State->operand[Loop].memory.relativeOffset.offset ? "%#.2x" : "0x%#.2x", State->operand[Loop].memory.relativeOffset.offset);
                            
                            CCString Value = CCStringCreate(CC_STD_ALLOCATOR, (CCStringHint)CCStringEncodingASCII, Hex);
                            Memory = CCStringCreateByJoiningStrings((CCString[5]){
                                CC_STRING("["),
                                Value,
                                CC_STRING("+"),
                                Registers[State->operand[Loop].memory.relativeOffset.reg & HKHubArchInstructionRegisterGeneralPurposeIndexMask].mnemonic,
                                CC_STRING("]")
                            }, 5, 0);
                            CCStringDestroy(Value);
                            break;
                        }
                            
                        case HKHubArchInstructionMemoryRelativeRegister:
                            Memory = CCStringCreateByJoiningStrings((CCString[5]){
                                CC_STRING("["),
                                Registers[State->operand[Loop].memory.relativeReg[0] & HKHubArchInstructionRegisterGeneralPurposeIndexMask].mnemonic,
                                CC_STRING("+"),
                                Registers[State->operand[Loop].memory.relativeReg[1] & HKHubArchInstructionRegisterGeneralPurposeIndexMask].mnemonic,
                                CC_STRING("]")
                            }, 5, 0);
                            break;
                    }
                    
                    CCString Temp = CCStringCreateByJoiningStrings((CCString[2]){ Disassembly, Memory }, 2, Loop == 0 ? CC_STRING(" ") : CC_STRING(","));
                    CCStringDestroy(Disassembly);
                    Disassembly = Temp;
                    CCStringDestroy(Memory);
                    break;
                }
                    
                default:
                    break;
            }
        }
    }
    
    return Disassembly;
}

HKHubArchInstructionOperationResult HKHubArchInstructionExecute(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    CCAssertLog(Processor, "Processor must not be null");
    CCAssertLog(State, "State must not be null");
    
    if (State->opcode == -1) return HKHubArchInstructionOperationResultFailure | HKHubArchInstructionOperationResultFlagInvalidOp;
    
    if (!Instructions[State->opcode].operation) return HKHubArchInstructionOperationResultSuccess;
    
    return Instructions[State->opcode].operation(Processor, State);
}

#pragma mark - Instruction Operations

static inline uint8_t *HKHubArchInstructionOperandStateValue(HKHubArchProcessor Processor, const HKHubArchInstructionOperandValue *Operand, _Bool ModifyDebug)
{
    switch (Operand->type)
    {
        case HKHubArchInstructionOperandR:
            if (ModifyDebug) Processor->state.debug.modified.reg = Operand->reg;
            
            if (Operand->reg & HKHubArchInstructionRegisterGeneralPurpose) return Processor->state.r + (Operand->reg & HKHubArchInstructionRegisterGeneralPurposeIndexMask);
            else if (Operand->reg == HKHubArchInstructionRegisterFlags) return &Processor->state.flags;
            else if (Operand->reg == HKHubArchInstructionRegisterPC) return &Processor->state.pc;
            break;
            
        case HKHubArchInstructionOperandM:
        {
            uint8_t Offset;
            switch (Operand->memory.type)
            {
                case HKHubArchInstructionMemoryOffset:
                    Offset = Operand->memory.offset;
                    break;
                    
                case HKHubArchInstructionMemoryRegister:
                    Offset = Processor->state.r[Operand->memory.reg & HKHubArchInstructionRegisterGeneralPurposeIndexMask];
                    break;
                    
                case HKHubArchInstructionMemoryRelativeOffset:
                    Offset = Processor->state.r[Operand->memory.relativeOffset.reg & HKHubArchInstructionRegisterGeneralPurposeIndexMask] + Operand->memory.relativeOffset.offset;
                    break;
                    
                case HKHubArchInstructionMemoryRelativeRegister:
                    Offset = Processor->state.r[Operand->memory.relativeReg[0] & HKHubArchInstructionRegisterGeneralPurposeIndexMask] + Processor->state.r[Operand->memory.relativeReg[1] & HKHubArchInstructionRegisterGeneralPurposeIndexMask];
                    break;
            }
            
            if (ModifyDebug)
            {
                Processor->state.debug.modified.offset = Offset;
                Processor->state.debug.modified.size = 1;
            }
            
            return &Processor->memory[Offset];
        }
            
        default:
            break;
    }
    
    CCAssertLog(0, "Should be a correctly formatted operand");
    
    return NULL;
}

static inline uint8_t *HKHubArchInstructionOperandDestinationValue(HKHubArchProcessor Processor, const HKHubArchInstructionOperandValue *Operand)
{
    return HKHubArchInstructionOperandStateValue(Processor, Operand, TRUE);
}

static inline const uint8_t *HKHubArchInstructionOperandSourceValue(HKHubArchProcessor Processor, const HKHubArchInstructionOperandValue *Operand)
{
    switch (Operand->type)
    {
        case HKHubArchInstructionOperandI:
            return &Operand->value;
            
        case HKHubArchInstructionOperandR:
        case HKHubArchInstructionOperandM:
            return HKHubArchInstructionOperandStateValue(Processor, Operand, FALSE);
            
        default:
            break;
    }
    
    CCAssertLog(0, "Should be a correctly formatted operand");
    
    return NULL;
}

#pragma mark Arithmetic

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationMOV(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    const size_t Cycles = 1 + ((State->operand[0].type == HKHubArchInstructionOperandM) * HKHubArchProcessorSpeedMemoryWrite) + ((State->operand[1].type == HKHubArchInstructionOperandM) * HKHubArchProcessorSpeedMemoryRead);
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= Cycles;
    uint8_t *Dest = HKHubArchInstructionOperandDestinationValue(Processor, &State->operand[0]);
    *Dest = *HKHubArchInstructionOperandSourceValue(Processor, &State->operand[1]);
    
    return HKHubArchInstructionOperationResultSuccess | (Dest == &Processor->state.pc ? HKHubArchInstructionOperationResultFlagSkipPC : 0);
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationADD(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    const size_t Cycles = 2 + ((State->operand[0].type == HKHubArchInstructionOperandM) * (HKHubArchProcessorSpeedMemoryRead + HKHubArchProcessorSpeedMemoryWrite)) + ((State->operand[1].type == HKHubArchInstructionOperandM) * HKHubArchProcessorSpeedMemoryRead);
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= Cycles;
    uint8_t *Dest = HKHubArchInstructionOperandDestinationValue(Processor, &State->operand[0]);
    const uint8_t *Src = HKHubArchInstructionOperandSourceValue(Processor, &State->operand[1]);
    
    const uint8_t Result = *Dest + *Src;
    const HKHubArchProcessorFlags Zero = (Result == 0 ? HKHubArchProcessorFlagsZero : 0);
    const HKHubArchProcessorFlags Carry = (Result < *Dest ? HKHubArchProcessorFlagsCarry : 0);
    const HKHubArchProcessorFlags Sign = (Result & 0x80 ? HKHubArchProcessorFlagsSign : 0);
    const HKHubArchProcessorFlags Overflow = ((*Dest ^ *Src) & 0x80) ? 0 : (((*Dest ^ Result) & 0x80) ? HKHubArchProcessorFlagsOverflow : 0);
    
    *Dest = Result;
    Processor->state.flags = (Processor->state.flags & ~HKHubArchProcessorFlagsMask) | Zero | Carry | Sign | Overflow;
    
    return HKHubArchInstructionOperationResultSuccess | (Dest == &Processor->state.pc ? HKHubArchInstructionOperationResultFlagSkipPC : 0);
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationSUB(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    const size_t Cycles = 2 + ((State->operand[0].type == HKHubArchInstructionOperandM) * (HKHubArchProcessorSpeedMemoryRead + HKHubArchProcessorSpeedMemoryWrite)) + ((State->operand[1].type == HKHubArchInstructionOperandM) * HKHubArchProcessorSpeedMemoryRead);
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= Cycles;
    uint8_t *Dest = HKHubArchInstructionOperandDestinationValue(Processor, &State->operand[0]);
    const uint8_t *Src = HKHubArchInstructionOperandSourceValue(Processor, &State->operand[1]);
    
    const uint8_t Result = *Dest - *Src;
    const HKHubArchProcessorFlags Zero = (Result == 0 ? HKHubArchProcessorFlagsZero : 0);
    const HKHubArchProcessorFlags Carry = (Result > *Dest ? HKHubArchProcessorFlagsCarry : 0);
    const HKHubArchProcessorFlags Sign = (Result & 0x80 ? HKHubArchProcessorFlagsSign : 0);
    const HKHubArchProcessorFlags Overflow = ((*Dest ^ *Src) & 0x80) ? (((*Dest ^ Result) & 0x80) ? HKHubArchProcessorFlagsOverflow : 0) : 0;
    
    *Dest = Result;
    Processor->state.flags = (Processor->state.flags & ~HKHubArchProcessorFlagsMask) | Zero | Carry | Sign | Overflow;
    
    return HKHubArchInstructionOperationResultSuccess | (Dest == &Processor->state.pc ? HKHubArchInstructionOperationResultFlagSkipPC : 0);
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationMUL(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    const size_t Cycles = 2 + ((State->operand[0].type == HKHubArchInstructionOperandM) * (HKHubArchProcessorSpeedMemoryRead + HKHubArchProcessorSpeedMemoryWrite)) + ((State->operand[1].type == HKHubArchInstructionOperandM) * HKHubArchProcessorSpeedMemoryRead);
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= Cycles;
    uint8_t *Dest = HKHubArchInstructionOperandDestinationValue(Processor, &State->operand[0]);
    const uint8_t *Src = HKHubArchInstructionOperandSourceValue(Processor, &State->operand[1]);
    
    const uint8_t Result = *Dest * *Src;
    const int32_t Temp = (int32_t)*(int8_t*)Dest * (int32_t)*(int8_t*)Src;
    const HKHubArchProcessorFlags Zero = (Result == 0 ? HKHubArchProcessorFlagsZero : 0);
    const HKHubArchProcessorFlags Carry = (((uint16_t)*Dest * (uint16_t)*Src) & 0xff00 ? HKHubArchProcessorFlagsCarry : 0);
    const HKHubArchProcessorFlags Sign = (Result & 0x80 ? HKHubArchProcessorFlagsSign : 0);
    const HKHubArchProcessorFlags Overflow = ((*Dest == 0) || (*Src == 0) ? 0 : ((*Dest ^ *Src) & 0x80 ? (((Result & 0x80) && (Temp == *(int8_t*)&Result)) ? 0 : HKHubArchProcessorFlagsOverflow) : ((!(Result & 0x80) && !(Temp & 0xffffff00)) ? 0 : HKHubArchProcessorFlagsOverflow)));
    
    *Dest = Result;
    Processor->state.flags = (Processor->state.flags & ~HKHubArchProcessorFlagsMask) | Zero | Carry | Sign | Overflow;
    
    return HKHubArchInstructionOperationResultSuccess | (Dest == &Processor->state.pc ? HKHubArchInstructionOperationResultFlagSkipPC : 0);
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationSDIV(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    const size_t Cycles = 3 + ((State->operand[0].type == HKHubArchInstructionOperandM) * (HKHubArchProcessorSpeedMemoryRead + HKHubArchProcessorSpeedMemoryWrite)) + ((State->operand[1].type == HKHubArchInstructionOperandM) * HKHubArchProcessorSpeedMemoryRead);
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= Cycles;
    int8_t *Dest = (int8_t*)HKHubArchInstructionOperandDestinationValue(Processor, &State->operand[0]);
    const int8_t *Src = (const int8_t*)HKHubArchInstructionOperandSourceValue(Processor, &State->operand[1]);
    
    const int8_t Result = *Src == 0 ? 0 : *Dest / *Src;
    const HKHubArchProcessorFlags Zero = (Result == 0 ? HKHubArchProcessorFlagsZero : 0);
    const HKHubArchProcessorFlags Sign = (Result & 0x80 ? HKHubArchProcessorFlagsSign : 0);
    const HKHubArchProcessorFlags Overflow = ((*Dest & *Src) & 0x80) && (Result & 0x80) ? HKHubArchProcessorFlagsOverflow : 0;
    const HKHubArchProcessorFlags DivideByZero = *Src == 0 ? (HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry) : 0;
    
    *Dest = Result;
    Processor->state.flags = (Processor->state.flags & ~HKHubArchProcessorFlagsMask) | Zero | Sign | Overflow | DivideByZero;
    
    return HKHubArchInstructionOperationResultSuccess | ((uint8_t*)Dest == &Processor->state.pc ? HKHubArchInstructionOperationResultFlagSkipPC : 0);
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationUDIV(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    const size_t Cycles = 3 + ((State->operand[0].type == HKHubArchInstructionOperandM) * (HKHubArchProcessorSpeedMemoryRead + HKHubArchProcessorSpeedMemoryWrite)) + ((State->operand[1].type == HKHubArchInstructionOperandM) * HKHubArchProcessorSpeedMemoryRead);
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= Cycles;
    uint8_t *Dest = HKHubArchInstructionOperandDestinationValue(Processor, &State->operand[0]);
    const uint8_t *Src = HKHubArchInstructionOperandSourceValue(Processor, &State->operand[1]);
    
    const uint8_t Result = *Src == 0 ? 0 : *Dest / *Src;
    const HKHubArchProcessorFlags Zero = (Result == 0 ? HKHubArchProcessorFlagsZero : 0);
    const HKHubArchProcessorFlags DivideByZero = *Src == 0 ? (HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry) : 0;
    
    *Dest = Result;
    Processor->state.flags = (Processor->state.flags & ~HKHubArchProcessorFlagsMask) | Zero | DivideByZero;
    
    return HKHubArchInstructionOperationResultSuccess | (Dest == &Processor->state.pc ? HKHubArchInstructionOperationResultFlagSkipPC : 0);
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationSMOD(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    const size_t Cycles = 3 + ((State->operand[0].type == HKHubArchInstructionOperandM) * (HKHubArchProcessorSpeedMemoryRead + HKHubArchProcessorSpeedMemoryWrite)) + ((State->operand[1].type == HKHubArchInstructionOperandM) * HKHubArchProcessorSpeedMemoryRead);
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= Cycles;
    int8_t *Dest = (int8_t*)HKHubArchInstructionOperandDestinationValue(Processor, &State->operand[0]);
    const int8_t *Src = (const int8_t*)HKHubArchInstructionOperandSourceValue(Processor, &State->operand[1]);
    
    const int8_t Result = *Src == 0 ? 0 : *Dest % *Src;
    const HKHubArchProcessorFlags Zero = (Result == 0 ? HKHubArchProcessorFlagsZero : 0);
    const HKHubArchProcessorFlags Sign = (Result & 0x80 ? HKHubArchProcessorFlagsSign : 0);
    const HKHubArchProcessorFlags Overflow = ((*Dest & *Src) & 0x80) && ((*Dest / *Src) & 0x80) ? HKHubArchProcessorFlagsOverflow : 0;
    const HKHubArchProcessorFlags DivideByZero = *Src == 0 ? (HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry) : 0;
    
    *Dest = Result;
    Processor->state.flags = (Processor->state.flags & ~HKHubArchProcessorFlagsMask) | Zero | Sign | Overflow | DivideByZero;
    
    return HKHubArchInstructionOperationResultSuccess | ((uint8_t*)Dest == &Processor->state.pc ? HKHubArchInstructionOperationResultFlagSkipPC : 0);
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationUMOD(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    const size_t Cycles = 3 + ((State->operand[0].type == HKHubArchInstructionOperandM) * (HKHubArchProcessorSpeedMemoryRead + HKHubArchProcessorSpeedMemoryWrite)) + ((State->operand[1].type == HKHubArchInstructionOperandM) * HKHubArchProcessorSpeedMemoryRead);
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= Cycles;
    uint8_t *Dest = HKHubArchInstructionOperandDestinationValue(Processor, &State->operand[0]);
    const uint8_t *Src = HKHubArchInstructionOperandSourceValue(Processor, &State->operand[1]);
    
    const uint8_t Result = *Src == 0 ? 0 : *Dest % *Src;
    const HKHubArchProcessorFlags Zero = (Result == 0 ? HKHubArchProcessorFlagsZero : 0);
    const HKHubArchProcessorFlags DivideByZero = *Src == 0 ? (HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry) : 0;
    
    *Dest = Result;
    Processor->state.flags = (Processor->state.flags & ~HKHubArchProcessorFlagsMask) | Zero | DivideByZero;
    
    return HKHubArchInstructionOperationResultSuccess | (Dest == &Processor->state.pc ? HKHubArchInstructionOperationResultFlagSkipPC : 0);
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationCMP(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    const size_t Cycles = 2 + ((State->operand[0].type == HKHubArchInstructionOperandM) * HKHubArchProcessorSpeedMemoryRead) + ((State->operand[1].type == HKHubArchInstructionOperandM) * HKHubArchProcessorSpeedMemoryRead);
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= Cycles;
    uint8_t *Dest = HKHubArchInstructionOperandStateValue(Processor, &State->operand[0], FALSE);
    const uint8_t *Src = HKHubArchInstructionOperandSourceValue(Processor, &State->operand[1]);
    
    const uint8_t Result = *Dest - *Src;
    const HKHubArchProcessorFlags Zero = (Result == 0 ? HKHubArchProcessorFlagsZero : 0);
    const HKHubArchProcessorFlags Carry = (Result > *Dest ? HKHubArchProcessorFlagsCarry : 0);
    const HKHubArchProcessorFlags Sign = (Result & 0x80 ? HKHubArchProcessorFlagsSign : 0);
    const HKHubArchProcessorFlags Overflow = ((*Dest ^ *Src) & 0x80) ? (((*Dest ^ Result) & 0x80) ? HKHubArchProcessorFlagsOverflow : 0) : 0;
    
    Processor->state.flags = (Processor->state.flags & ~HKHubArchProcessorFlagsMask) | Zero | Carry | Sign | Overflow;
        
    return HKHubArchInstructionOperationResultSuccess;
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationSHL(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    const size_t Cycles = 1 + ((State->operand[0].type == HKHubArchInstructionOperandM) * (HKHubArchProcessorSpeedMemoryRead + HKHubArchProcessorSpeedMemoryWrite)) + ((State->operand[1].type == HKHubArchInstructionOperandM) * HKHubArchProcessorSpeedMemoryRead);
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= Cycles;
    uint8_t *Dest = HKHubArchInstructionOperandDestinationValue(Processor, &State->operand[0]);
    const uint8_t *Src = HKHubArchInstructionOperandSourceValue(Processor, &State->operand[1]);
    
    const uint8_t Result = *Dest << *Src;
    const HKHubArchProcessorFlags Zero = (Result == 0 ? HKHubArchProcessorFlagsZero : 0);
    const HKHubArchProcessorFlags Carry = ((*Src <= 8) && (*Src > 0) && (*Dest & (0x80 >> (*Src - 1))) ? HKHubArchProcessorFlagsCarry : 0);
    const HKHubArchProcessorFlags Sign = (Result & 0x80 ? HKHubArchProcessorFlagsSign : 0);
    const HKHubArchProcessorFlags Overflow = ((*Dest >> (8 - *Src)) || ((*Src >= 8) && (*Dest)) ? HKHubArchProcessorFlagsOverflow : 0);
    
    *Dest = Result;
    Processor->state.flags = (Processor->state.flags & ~HKHubArchProcessorFlagsMask) | Zero | Carry | Sign | Overflow;
    
    return HKHubArchInstructionOperationResultSuccess | (Dest == &Processor->state.pc ? HKHubArchInstructionOperationResultFlagSkipPC : 0);
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationSHR(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    const size_t Cycles = 1 + ((State->operand[0].type == HKHubArchInstructionOperandM) * (HKHubArchProcessorSpeedMemoryRead + HKHubArchProcessorSpeedMemoryWrite)) + ((State->operand[1].type == HKHubArchInstructionOperandM) * HKHubArchProcessorSpeedMemoryRead);
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= Cycles;
    uint8_t *Dest = HKHubArchInstructionOperandDestinationValue(Processor, &State->operand[0]);
    const uint8_t *Src = HKHubArchInstructionOperandSourceValue(Processor, &State->operand[1]);
    
    const uint8_t Result = *Dest >> *Src;
    const HKHubArchProcessorFlags Zero = (Result == 0 ? HKHubArchProcessorFlagsZero : 0);
    const HKHubArchProcessorFlags Carry = ((*Src <= 8) && (*Src > 0) && (*Dest & (1 << (*Src - 1))) ? HKHubArchProcessorFlagsCarry : 0);
    const HKHubArchProcessorFlags Sign = (Result & 0x80 ? HKHubArchProcessorFlagsSign : 0);
    const HKHubArchProcessorFlags Overflow = ((uint8_t)(*Dest << (8 - *Src)) || ((*Src >= 8) && (*Dest)) ? HKHubArchProcessorFlagsOverflow : 0);
    
    *Dest = Result;
    Processor->state.flags = (Processor->state.flags & ~HKHubArchProcessorFlagsMask) | Zero | Carry | Sign | Overflow;
    
    return HKHubArchInstructionOperationResultSuccess | (Dest == &Processor->state.pc ? HKHubArchInstructionOperationResultFlagSkipPC : 0);
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationXOR(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    const size_t Cycles = 1 + ((State->operand[0].type == HKHubArchInstructionOperandM) * (HKHubArchProcessorSpeedMemoryRead + HKHubArchProcessorSpeedMemoryWrite)) + ((State->operand[1].type == HKHubArchInstructionOperandM) * HKHubArchProcessorSpeedMemoryRead);
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= Cycles;
    uint8_t *Dest = HKHubArchInstructionOperandDestinationValue(Processor, &State->operand[0]);
    const uint8_t *Src = HKHubArchInstructionOperandSourceValue(Processor, &State->operand[1]);
    
    const uint8_t Result = *Dest ^ *Src;
    const HKHubArchProcessorFlags Zero = (Result == 0 ? HKHubArchProcessorFlagsZero : 0);
    const HKHubArchProcessorFlags Sign = (Result & 0x80 ? HKHubArchProcessorFlagsSign : 0);
    
    *Dest = Result;
    Processor->state.flags = (Processor->state.flags & ~HKHubArchProcessorFlagsMask) | Zero | Sign;
    
    return HKHubArchInstructionOperationResultSuccess | (Dest == &Processor->state.pc ? HKHubArchInstructionOperationResultFlagSkipPC : 0);
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationOR(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    const size_t Cycles = 1 + ((State->operand[0].type == HKHubArchInstructionOperandM) * (HKHubArchProcessorSpeedMemoryRead + HKHubArchProcessorSpeedMemoryWrite)) + ((State->operand[1].type == HKHubArchInstructionOperandM) * HKHubArchProcessorSpeedMemoryRead);
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= Cycles;
    uint8_t *Dest = HKHubArchInstructionOperandDestinationValue(Processor, &State->operand[0]);
    const uint8_t *Src = HKHubArchInstructionOperandSourceValue(Processor, &State->operand[1]);
    
    const uint8_t Result = *Dest | *Src;
    const HKHubArchProcessorFlags Zero = (Result == 0 ? HKHubArchProcessorFlagsZero : 0);
    const HKHubArchProcessorFlags Sign = (Result & 0x80 ? HKHubArchProcessorFlagsSign : 0);
    
    *Dest = Result;
    Processor->state.flags = (Processor->state.flags & ~HKHubArchProcessorFlagsMask) | Zero | Sign;
    
    return HKHubArchInstructionOperationResultSuccess | (Dest == &Processor->state.pc ? HKHubArchInstructionOperationResultFlagSkipPC : 0);
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationAND(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    const size_t Cycles = 1 + ((State->operand[0].type == HKHubArchInstructionOperandM) * (HKHubArchProcessorSpeedMemoryRead + HKHubArchProcessorSpeedMemoryWrite)) + ((State->operand[1].type == HKHubArchInstructionOperandM) * HKHubArchProcessorSpeedMemoryRead);
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= Cycles;
    uint8_t *Dest = HKHubArchInstructionOperandDestinationValue(Processor, &State->operand[0]);
    const uint8_t *Src = HKHubArchInstructionOperandSourceValue(Processor, &State->operand[1]);
    
    const uint8_t Result = *Dest & *Src;
    const HKHubArchProcessorFlags Zero = (Result == 0 ? HKHubArchProcessorFlagsZero : 0);
    const HKHubArchProcessorFlags Sign = (Result & 0x80 ? HKHubArchProcessorFlagsSign : 0);
    
    *Dest = Result;
    Processor->state.flags = (Processor->state.flags & ~HKHubArchProcessorFlagsMask) | Zero | Sign;
    
    return HKHubArchInstructionOperationResultSuccess | (Dest == &Processor->state.pc ? HKHubArchInstructionOperationResultFlagSkipPC : 0);
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationNOT(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    const size_t Cycles = 1 + ((State->operand[0].type == HKHubArchInstructionOperandM) * (HKHubArchProcessorSpeedMemoryRead + HKHubArchProcessorSpeedMemoryWrite));
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= Cycles;
    uint8_t *Dest = HKHubArchInstructionOperandDestinationValue(Processor, &State->operand[0]);
    
    const uint8_t Result = ~*Dest;
    const HKHubArchProcessorFlags Zero = (Result == 0 ? HKHubArchProcessorFlagsZero : 0);
    const HKHubArchProcessorFlags Sign = (Result & 0x80 ? HKHubArchProcessorFlagsSign : 0);
    
    *Dest = Result;
    Processor->state.flags = (Processor->state.flags & ~HKHubArchProcessorFlagsMask) | Zero | Sign;
    
    return HKHubArchInstructionOperationResultSuccess | (Dest == &Processor->state.pc ? HKHubArchInstructionOperationResultFlagSkipPC : 0);
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationNEG(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    const size_t Cycles = 1 + ((State->operand[0].type == HKHubArchInstructionOperandM) * (HKHubArchProcessorSpeedMemoryRead + HKHubArchProcessorSpeedMemoryWrite));
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= Cycles;
    uint8_t *Dest = HKHubArchInstructionOperandDestinationValue(Processor, &State->operand[0]);
    
    const uint8_t Result = -*Dest;
    const HKHubArchProcessorFlags Zero = (Result == 0 ? HKHubArchProcessorFlagsZero : 0);
    const HKHubArchProcessorFlags Carry = (*Dest ? HKHubArchProcessorFlagsCarry : 0);
    const HKHubArchProcessorFlags Sign = (Result & 0x80 ? HKHubArchProcessorFlagsSign : 0);
    const HKHubArchProcessorFlags Overflow = ((*Dest & 0x80) && (Result & 0x80) ? HKHubArchProcessorFlagsOverflow : 0);
    
    *Dest = Result;
    Processor->state.flags = (Processor->state.flags & ~HKHubArchProcessorFlagsMask) | Zero | Carry | Sign | Overflow;
    
    return HKHubArchInstructionOperationResultSuccess | (Dest == &Processor->state.pc ? HKHubArchInstructionOperationResultFlagSkipPC : 0);
}

#pragma mark Signals

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationHLT(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    Processor->status = HKHubArchProcessorStatusIdle;
    
    return HKHubArchInstructionOperationResultSuccess | HKHubArchInstructionOperationResultFlagSkipPC;
}

#pragma mark I/O

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationSEND(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    size_t Cycles = 4;
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    HKHubArchInstructionOperationResult Result = HKHubArchInstructionOperationResultSuccess;
    HKHubArchPortID Port = *(const uint8_t*)HKHubArchInstructionOperandSourceValue(Processor, &State->operand[0]);
    HKHubArchPortConnection *Conn = CCDictionaryGetValue(Processor->ports, &Port);
    _Bool Success = FALSE;
    
    if (Processor->message.type == HKHubArchProcessorMessageComplete)
    {
        Cycles += Processor->message.wait;
        Cycles += Processor->message.data.size * HKHubArchProcessorSpeedPortTransmission;
        Cycles += Processor->message.data.size * HKHubArchProcessorSpeedMemoryRead;
        
        if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
        
        Success = TRUE;
    }
    
    else if (Conn)
    {
        Processor->message.wait = 0;
        Processor->message.timestamp = Processor->cycles - Cycles;
        Processor->message.port = Port;
        Processor->message.type = HKHubArchProcessorMessageSend;
        Processor->message.data = (HKHubArchPortMessage){
            .size = State->operand[1].type != HKHubArchInstructionOperandNA ? *(const uint8_t*)HKHubArchInstructionOperandSourceValue(Processor, &State->operand[1]) : 0,
            .offset = State->operand[2].type != HKHubArchInstructionOperandNA ? (uint8_t)(HKHubArchInstructionOperandSourceValue(Processor, &State->operand[2]) - Processor->memory) : 0,
            .memory = Processor->memory
        };
        
        const HKHubArchPort *Interface = HKHubArchPortConnectionGetOppositePort(*Conn, Processor, Port);
        
        HKHubArchPortResponse Response = Interface->receiver ? Interface->receiver(*Conn, Interface->device, Interface->id, &Processor->message.data, Processor, Processor->message.timestamp, &Processor->message.wait) : HKHubArchPortResponseTimeout;
        
        switch (Response)
        {
            case HKHubArchPortResponseSuccess:
                Cycles += Processor->message.wait;
                Cycles += Processor->message.data.size * HKHubArchProcessorSpeedPortTransmission;
                Cycles += Processor->message.data.size * HKHubArchProcessorSpeedMemoryRead;
                
                if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
                
                Success = TRUE;
                break;
                
            case HKHubArchPortResponseTimeout:
                Cycles += 8;
                break;
                
            case HKHubArchPortResponseRetry:
                return HKHubArchInstructionOperationResultFailure | HKHubArchInstructionOperationResultFlagPipelineStall;
                
            case HKHubArchPortResponseDefer:
                return HKHubArchInstructionOperationResultFailure;
        }
    }
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->state.flags = (Processor->state.flags & ~HKHubArchProcessorFlagsZero) | (Success ? 0 : HKHubArchProcessorFlagsZero);
    Processor->cycles -= Cycles;
    Processor->message.type = HKHubArchProcessorMessageClear;
    
    return Result;
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationRECV(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    size_t Cycles = 4;
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    HKHubArchInstructionOperationResult Result = HKHubArchInstructionOperationResultSuccess;
    HKHubArchPortID Port = *(const uint8_t*)HKHubArchInstructionOperandSourceValue(Processor, &State->operand[0]);
    HKHubArchPortConnection *Conn = CCDictionaryGetValue(Processor->ports, &Port);
    _Bool Success = FALSE;
    
    if (Processor->message.type == HKHubArchProcessorMessageComplete)
    {
        Cycles += Processor->message.wait;
        Cycles += Processor->message.data.size * HKHubArchProcessorSpeedPortTransmission;
        Cycles += Processor->message.data.size * HKHubArchProcessorSpeedMemoryWrite;
        
        if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
        
        Processor->state.debug.modified.size = Processor->message.data.size;
        
        Success = TRUE;
    }
    
    else if (Conn)
    {
        Processor->message.wait = 0;
        Processor->message.timestamp = Processor->cycles - Cycles;
        Processor->message.offset = (uint8_t)(HKHubArchInstructionOperandStateValue(Processor, &State->operand[1], FALSE) - Processor->memory);
        Processor->message.port = Port;
        Processor->message.type = HKHubArchProcessorMessageReceive;
        
        const HKHubArchPort *Interface = HKHubArchPortConnectionGetOppositePort(*Conn, Processor, Port);
        
        HKHubArchPortResponse Response = Interface->sender ? Interface->sender(*Conn, Interface->device, Interface->id, &Processor->message.data, Processor, Processor->message.timestamp, &Processor->message.wait) : HKHubArchPortResponseTimeout;
        
        switch (Response)
        {
            case HKHubArchPortResponseSuccess:
                Cycles += Processor->message.wait;
                Cycles += Processor->message.data.size * HKHubArchProcessorSpeedPortTransmission;
                Cycles += Processor->message.data.size * HKHubArchProcessorSpeedMemoryWrite;
                
                if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
                
                Success = TRUE;
                
                uint8_t Offset = Processor->message.offset;
                for (size_t Loop = 0; Loop < Processor->message.data.size; Loop++)
                {
                    Processor->memory[Offset + Loop] = Processor->message.data.memory[Processor->message.data.offset + Loop];
                }
                
                Processor->state.debug.modified.offset = Offset;
                Processor->state.debug.modified.size = Processor->message.data.size;
                break;
                
            case HKHubArchPortResponseTimeout:
                Cycles += 8;
                break;
                
            case HKHubArchPortResponseRetry:
                return HKHubArchInstructionOperationResultFailure | HKHubArchInstructionOperationResultFlagPipelineStall;
                
            case HKHubArchPortResponseDefer:
                return HKHubArchInstructionOperationResultFailure;
        }
    }
    
    if (Processor->cycles < Cycles) return HKHubArchInstructionOperationResultFailure;
    
    Processor->state.flags = (Processor->state.flags & ~HKHubArchProcessorFlagsZero) | (Success ? 0 : HKHubArchProcessorFlagsZero);
    Processor->cycles -= Cycles;
    Processor->message.type = HKHubArchProcessorMessageClear;
    
    return Result;
}

#pragma mark Branching

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJMP(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    if (Processor->cycles < 1) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= 1;
    Processor->state.pc += State->operand[0].value;
    
    return HKHubArchInstructionOperationResultSuccess | HKHubArchInstructionOperationResultFlagSkipPC;
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJZ(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    if (Processor->cycles < 1) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= 1;
    
    if (Processor->state.flags & HKHubArchProcessorFlagsZero)
    {
        Processor->state.pc += State->operand[0].value;
        
        return HKHubArchInstructionOperationResultSuccess | HKHubArchInstructionOperationResultFlagSkipPC;
    }
    
    return HKHubArchInstructionOperationResultSuccess;
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJNZ(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    if (Processor->cycles < 1) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= 1;
    
    if ((Processor->state.flags & HKHubArchProcessorFlagsZero) == 0)
    {
        Processor->state.pc += State->operand[0].value;
        
        return HKHubArchInstructionOperationResultSuccess | HKHubArchInstructionOperationResultFlagSkipPC;
    }
    
    return HKHubArchInstructionOperationResultSuccess;
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJS(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    if (Processor->cycles < 1) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= 1;
    
    if (Processor->state.flags & HKHubArchProcessorFlagsSign)
    {
        Processor->state.pc += State->operand[0].value;
        
        return HKHubArchInstructionOperationResultSuccess | HKHubArchInstructionOperationResultFlagSkipPC;
    }
    
    return HKHubArchInstructionOperationResultSuccess;
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJNS(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    if (Processor->cycles < 1) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= 1;
    
    if ((Processor->state.flags & HKHubArchProcessorFlagsSign) == 0)
    {
        Processor->state.pc += State->operand[0].value;
        
        return HKHubArchInstructionOperationResultSuccess | HKHubArchInstructionOperationResultFlagSkipPC;
    }
    
    return HKHubArchInstructionOperationResultSuccess;
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJO(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    if (Processor->cycles < 1) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= 1;
    
    if (Processor->state.flags & HKHubArchProcessorFlagsOverflow)
    {
        Processor->state.pc += State->operand[0].value;
        
        return HKHubArchInstructionOperationResultSuccess | HKHubArchInstructionOperationResultFlagSkipPC;
    }
    
    return HKHubArchInstructionOperationResultSuccess;
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJNO(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    if (Processor->cycles < 1) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= 1;
    
    if ((Processor->state.flags & HKHubArchProcessorFlagsOverflow) == 0)
    {
        Processor->state.pc += State->operand[0].value;
        
        return HKHubArchInstructionOperationResultSuccess | HKHubArchInstructionOperationResultFlagSkipPC;
    }
    
    return HKHubArchInstructionOperationResultSuccess;
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJSL(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    if (Processor->cycles < 1) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= 1;
    
    if ((_Bool)(Processor->state.flags & HKHubArchProcessorFlagsSign) != (_Bool)(Processor->state.flags & HKHubArchProcessorFlagsOverflow))
    {
        Processor->state.pc += State->operand[0].value;
        
        return HKHubArchInstructionOperationResultSuccess | HKHubArchInstructionOperationResultFlagSkipPC;
    }
    
    return HKHubArchInstructionOperationResultSuccess;
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJSGE(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    if (Processor->cycles < 1) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= 1;
    
    if ((_Bool)(Processor->state.flags & HKHubArchProcessorFlagsSign) == (_Bool)(Processor->state.flags & HKHubArchProcessorFlagsOverflow))
    {
        Processor->state.pc += State->operand[0].value;
        
        return HKHubArchInstructionOperationResultSuccess | HKHubArchInstructionOperationResultFlagSkipPC;
    }
    
    return HKHubArchInstructionOperationResultSuccess;
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJSLE(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    if (Processor->cycles < 1) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= 1;
    
    if ((Processor->state.flags & HKHubArchProcessorFlagsZero) || ((_Bool)(Processor->state.flags & HKHubArchProcessorFlagsSign) != (_Bool)(Processor->state.flags & HKHubArchProcessorFlagsOverflow)))
    {
        Processor->state.pc += State->operand[0].value;
        
        return HKHubArchInstructionOperationResultSuccess | HKHubArchInstructionOperationResultFlagSkipPC;
    }
    
    return HKHubArchInstructionOperationResultSuccess;
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJSG(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    if (Processor->cycles < 1) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= 1;
    
    if (((Processor->state.flags & HKHubArchProcessorFlagsZero) == 0) && ((_Bool)(Processor->state.flags & HKHubArchProcessorFlagsSign) == (_Bool)(Processor->state.flags & HKHubArchProcessorFlagsOverflow)))
    {
        Processor->state.pc += State->operand[0].value;
        
        return HKHubArchInstructionOperationResultSuccess | HKHubArchInstructionOperationResultFlagSkipPC;
    }
    
    return HKHubArchInstructionOperationResultSuccess;
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJUL(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    if (Processor->cycles < 1) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= 1;
    
    if (Processor->state.flags & HKHubArchProcessorFlagsCarry)
    {
        Processor->state.pc += State->operand[0].value;
        
        return HKHubArchInstructionOperationResultSuccess | HKHubArchInstructionOperationResultFlagSkipPC;
    }
    
    return HKHubArchInstructionOperationResultSuccess;
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJUGE(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    if (Processor->cycles < 1) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= 1;
    
    if ((Processor->state.flags & HKHubArchProcessorFlagsCarry) == 0)
    {
        Processor->state.pc += State->operand[0].value;
        
        return HKHubArchInstructionOperationResultSuccess | HKHubArchInstructionOperationResultFlagSkipPC;
    }
    
    return HKHubArchInstructionOperationResultSuccess;
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJULE(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    if (Processor->cycles < 1) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= 1;
    
    if ((Processor->state.flags & HKHubArchProcessorFlagsCarry) || (Processor->state.flags & HKHubArchProcessorFlagsZero))
    {
        Processor->state.pc += State->operand[0].value;
        
        return HKHubArchInstructionOperationResultSuccess | HKHubArchInstructionOperationResultFlagSkipPC;
    }
    
    return HKHubArchInstructionOperationResultSuccess;
}

static HKHubArchInstructionOperationResult HKHubArchInstructionOperationJUG(HKHubArchProcessor Processor, const HKHubArchInstructionState *State)
{
    if (Processor->cycles < 1) return HKHubArchInstructionOperationResultFailure;
    
    Processor->cycles -= 1;
    
    if (((Processor->state.flags & HKHubArchProcessorFlagsCarry) == 0) && ((Processor->state.flags & HKHubArchProcessorFlagsZero) == 0))
    {
        Processor->state.pc += State->operand[0].value;
        
        return HKHubArchInstructionOperationResultSuccess | HKHubArchInstructionOperationResultFlagSkipPC;
    }
    
    return HKHubArchInstructionOperationResultSuccess;
}
