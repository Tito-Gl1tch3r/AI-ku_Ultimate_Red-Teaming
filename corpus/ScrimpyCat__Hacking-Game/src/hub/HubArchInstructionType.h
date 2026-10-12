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

#ifndef HackingGame_HubArchInstructionType_h
#define HackingGame_HubArchInstructionType_h

#include "Base.h"

#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wflag-enum"
typedef CC_FLAG_ENUM(HKHubArchInstructionOperand, uint8_t) {
    HKHubArchInstructionOperandNA = (1 << 0),
    HKHubArchInstructionOperandI = (1 << 1),
    HKHubArchInstructionOperandR = (1 << 2),
    HKHubArchInstructionOperandM = (1 << 3),
    HKHubArchInstructionOperandRM = HKHubArchInstructionOperandR | HKHubArchInstructionOperandM,
    HKHubArchInstructionOperandRel = (1 << 4) | HKHubArchInstructionOperandI
};
#pragma clang diagnostic pop

typedef enum {
    HKHubArchInstructionMemoryOperationMask = 3,
    HKHubArchInstructionMemoryOperationSrc = (1 << 0),
    HKHubArchInstructionMemoryOperationDst = (1 << 1),
    
    HKHubArchInstructionMemoryOperationOp1 = 0,
    HKHubArchInstructionMemoryOperationOp2 = 2,
    HKHubArchInstructionMemoryOperationOp3 = 4,
    
    HKHubArchInstructionMemoryOperationNone = 0,
    HKHubArchInstructionMemoryOperationS = (HKHubArchInstructionMemoryOperationSrc << HKHubArchInstructionMemoryOperationOp1),
    HKHubArchInstructionMemoryOperationD = (HKHubArchInstructionMemoryOperationDst << HKHubArchInstructionMemoryOperationOp1),
    HKHubArchInstructionMemoryOperationB = ((HKHubArchInstructionMemoryOperationSrc | HKHubArchInstructionMemoryOperationDst) << HKHubArchInstructionMemoryOperationOp1),
    
    HKHubArchInstructionMemoryOperationSS = (HKHubArchInstructionMemoryOperationSrc << HKHubArchInstructionMemoryOperationOp1) | (HKHubArchInstructionMemoryOperationSrc << HKHubArchInstructionMemoryOperationOp2),
    HKHubArchInstructionMemoryOperationSD = (HKHubArchInstructionMemoryOperationSrc << HKHubArchInstructionMemoryOperationOp1) | (HKHubArchInstructionMemoryOperationDst << HKHubArchInstructionMemoryOperationOp2),
    HKHubArchInstructionMemoryOperationSB = HKHubArchInstructionMemoryOperationSS | HKHubArchInstructionMemoryOperationSD,
    HKHubArchInstructionMemoryOperationDS = (HKHubArchInstructionMemoryOperationDst << HKHubArchInstructionMemoryOperationOp1) | (HKHubArchInstructionMemoryOperationSrc << HKHubArchInstructionMemoryOperationOp2),
    HKHubArchInstructionMemoryOperationDD = (HKHubArchInstructionMemoryOperationDst << HKHubArchInstructionMemoryOperationOp1) | (HKHubArchInstructionMemoryOperationDst << HKHubArchInstructionMemoryOperationOp2),
    HKHubArchInstructionMemoryOperationDB = HKHubArchInstructionMemoryOperationDS | HKHubArchInstructionMemoryOperationDD,
    HKHubArchInstructionMemoryOperationBS = HKHubArchInstructionMemoryOperationSS | HKHubArchInstructionMemoryOperationDS,
    HKHubArchInstructionMemoryOperationBD = HKHubArchInstructionMemoryOperationSD | HKHubArchInstructionMemoryOperationDD,
    HKHubArchInstructionMemoryOperationBB = HKHubArchInstructionMemoryOperationBS | HKHubArchInstructionMemoryOperationSB,
    
    HKHubArchInstructionMemoryOperationSSS = (HKHubArchInstructionMemoryOperationSrc << HKHubArchInstructionMemoryOperationOp1) | (HKHubArchInstructionMemoryOperationSrc << HKHubArchInstructionMemoryOperationOp2) | (HKHubArchInstructionMemoryOperationSrc << HKHubArchInstructionMemoryOperationOp3),
    HKHubArchInstructionMemoryOperationSSD = (HKHubArchInstructionMemoryOperationSrc << HKHubArchInstructionMemoryOperationOp1) | (HKHubArchInstructionMemoryOperationSrc << HKHubArchInstructionMemoryOperationOp2) | (HKHubArchInstructionMemoryOperationDst << HKHubArchInstructionMemoryOperationOp3),
    HKHubArchInstructionMemoryOperationSSB = HKHubArchInstructionMemoryOperationSSS | HKHubArchInstructionMemoryOperationSSD,
    HKHubArchInstructionMemoryOperationSDS = (HKHubArchInstructionMemoryOperationSrc << HKHubArchInstructionMemoryOperationOp1) | (HKHubArchInstructionMemoryOperationDst << HKHubArchInstructionMemoryOperationOp2) | (HKHubArchInstructionMemoryOperationSrc << HKHubArchInstructionMemoryOperationOp3),
    HKHubArchInstructionMemoryOperationSDD = (HKHubArchInstructionMemoryOperationSrc << HKHubArchInstructionMemoryOperationOp1) | (HKHubArchInstructionMemoryOperationDst << HKHubArchInstructionMemoryOperationOp2) | (HKHubArchInstructionMemoryOperationDst << HKHubArchInstructionMemoryOperationOp3),
    HKHubArchInstructionMemoryOperationSDB = HKHubArchInstructionMemoryOperationSDS | HKHubArchInstructionMemoryOperationSDD,
    HKHubArchInstructionMemoryOperationSBS = HKHubArchInstructionMemoryOperationSSS | HKHubArchInstructionMemoryOperationSDS,
    HKHubArchInstructionMemoryOperationSBD = HKHubArchInstructionMemoryOperationSSD | HKHubArchInstructionMemoryOperationSDD,
    HKHubArchInstructionMemoryOperationSBB = HKHubArchInstructionMemoryOperationSBS | HKHubArchInstructionMemoryOperationSBD,
    HKHubArchInstructionMemoryOperationDSS = (HKHubArchInstructionMemoryOperationDst << HKHubArchInstructionMemoryOperationOp1) | (HKHubArchInstructionMemoryOperationSrc << HKHubArchInstructionMemoryOperationOp2) | (HKHubArchInstructionMemoryOperationSrc << HKHubArchInstructionMemoryOperationOp3),
    HKHubArchInstructionMemoryOperationDSD = (HKHubArchInstructionMemoryOperationDst << HKHubArchInstructionMemoryOperationOp1) | (HKHubArchInstructionMemoryOperationSrc << HKHubArchInstructionMemoryOperationOp2) | (HKHubArchInstructionMemoryOperationDst << HKHubArchInstructionMemoryOperationOp3),
    HKHubArchInstructionMemoryOperationDSB = HKHubArchInstructionMemoryOperationDSS | HKHubArchInstructionMemoryOperationDSD,
    HKHubArchInstructionMemoryOperationDDS = (HKHubArchInstructionMemoryOperationDst << HKHubArchInstructionMemoryOperationOp1) | (HKHubArchInstructionMemoryOperationDst << HKHubArchInstructionMemoryOperationOp2) | (HKHubArchInstructionMemoryOperationSrc << HKHubArchInstructionMemoryOperationOp3),
    HKHubArchInstructionMemoryOperationDDD = (HKHubArchInstructionMemoryOperationDst << HKHubArchInstructionMemoryOperationOp1) | (HKHubArchInstructionMemoryOperationDst << HKHubArchInstructionMemoryOperationOp2) | (HKHubArchInstructionMemoryOperationDst << HKHubArchInstructionMemoryOperationOp3),
    HKHubArchInstructionMemoryOperationDDB = HKHubArchInstructionMemoryOperationDDS | HKHubArchInstructionMemoryOperationDDD,
    HKHubArchInstructionMemoryOperationDBS = HKHubArchInstructionMemoryOperationDSS | HKHubArchInstructionMemoryOperationDDS,
    HKHubArchInstructionMemoryOperationDBD = HKHubArchInstructionMemoryOperationDSD | HKHubArchInstructionMemoryOperationDDD,
    HKHubArchInstructionMemoryOperationDBB = HKHubArchInstructionMemoryOperationDBS | HKHubArchInstructionMemoryOperationDBD,
    HKHubArchInstructionMemoryOperationBSS = HKHubArchInstructionMemoryOperationSSS | HKHubArchInstructionMemoryOperationDSS,
    HKHubArchInstructionMemoryOperationBSD = HKHubArchInstructionMemoryOperationSSD | HKHubArchInstructionMemoryOperationDSD,
    HKHubArchInstructionMemoryOperationBSB = HKHubArchInstructionMemoryOperationBSS | HKHubArchInstructionMemoryOperationBSD,
    HKHubArchInstructionMemoryOperationBDS = HKHubArchInstructionMemoryOperationSDS | HKHubArchInstructionMemoryOperationDDS,
    HKHubArchInstructionMemoryOperationBDD = HKHubArchInstructionMemoryOperationSDD | HKHubArchInstructionMemoryOperationDDD,
    HKHubArchInstructionMemoryOperationBDB = HKHubArchInstructionMemoryOperationBDD | HKHubArchInstructionMemoryOperationDDB,
    HKHubArchInstructionMemoryOperationBBS = HKHubArchInstructionMemoryOperationBSS | HKHubArchInstructionMemoryOperationBDS,
    HKHubArchInstructionMemoryOperationBBD = HKHubArchInstructionMemoryOperationBSD | HKHubArchInstructionMemoryOperationBDD,
    HKHubArchInstructionMemoryOperationBBB = HKHubArchInstructionMemoryOperationBBS | HKHubArchInstructionMemoryOperationBBD
} HKHubArchInstructionMemoryOperation;

typedef CC_FLAG_ENUM(HKHubArchInstructionControlFlow, uint8_t) {
    HKHubArchInstructionControlFlowEvaluationMask = 1,
    HKHubArchInstructionControlFlowEvaluationUnconditional = (0 << 0),
    HKHubArchInstructionControlFlowEvaluationConditional = (1 << 0),
    
    HKHubArchInstructionControlFlowEffectMask = (3 << 1),
    HKHubArchInstructionControlFlowEffectNone = (0 << 1),
    HKHubArchInstructionControlFlowEffectBranch = (1 << 1),
    HKHubArchInstructionControlFlowEffectPause = (2 << 1),
    HKHubArchInstructionControlFlowEffectIO = (3 << 1)
};

typedef CC_FLAG_ENUM(HKHubArchInstructionRegister, uint8_t) {
    /// Bit that will be set for special purpose registers (must also check the @b HKHubArchInstructionRegisterGeneralPurpose is not set)
    HKHubArchInstructionRegisterSpecialPurpose = (1 << 1),
    /// Bit that will be set for general purpose registers
    HKHubArchInstructionRegisterGeneralPurpose = (1 << 2),
    HKHubArchInstructionRegisterGeneralPurposeIndexMask = 3,
    HKHubArchInstructionRegisterSpecialPurposeIndexMask = 1,
    
    HKHubArchInstructionRegisterR0 = 0 | HKHubArchInstructionRegisterGeneralPurpose,
    HKHubArchInstructionRegisterR1 = 1 | HKHubArchInstructionRegisterGeneralPurpose,
    HKHubArchInstructionRegisterR2 = 2 | HKHubArchInstructionRegisterGeneralPurpose,
    HKHubArchInstructionRegisterR3 = 3 | HKHubArchInstructionRegisterGeneralPurpose,
    
    HKHubArchInstructionRegisterFlags = 0 | HKHubArchInstructionRegisterSpecialPurpose,
    HKHubArchInstructionRegisterPC = 1 | HKHubArchInstructionRegisterSpecialPurpose
};

typedef CC_ENUM(HKHubArchInstructionMemory, uint8_t) {
    HKHubArchInstructionMemoryOffset,           //[0]
    HKHubArchInstructionMemoryRegister,         //[r0]
    HKHubArchInstructionMemoryRelativeOffset,   //[r0+0]
    HKHubArchInstructionMemoryRelativeRegister  //[r0+r0]
};

typedef struct {
    HKHubArchInstructionOperand type; //HKHubArchInstructionOperandNA or HKHubArchInstructionOperandI or HKHubArchInstructionOperandR or HKHubArchInstructionOperandM
    union {
        uint8_t value; //type = HKHubArchInstructionOperandI
        HKHubArchInstructionRegister reg; //type = HKHubArchInstructionOperandR
        struct {
            HKHubArchInstructionMemory type;
            union {
                uint8_t offset; //memory.type = HKHubArchInstructionMemoryOffset
                HKHubArchInstructionRegister reg; //memory.type = HKHubArchInstructionMemoryRegister
                struct {
                    uint8_t offset;
                    HKHubArchInstructionRegister reg;
                } relativeOffset; //memory.type = HKHubArchInstructionMemoryRelativeOffset
                HKHubArchInstructionRegister relativeReg[2]; //memory.type = HKHubArchInstructionMemoryRelativeRegister
            };
        } memory; //type = HKHubArchInstructionOperandM
    };
} HKHubArchInstructionOperandValue;

typedef struct {
    int8_t opcode; //-1 = invalid
    HKHubArchInstructionOperandValue operand[3];
} HKHubArchInstructionState;

typedef enum {
    HKHubArchInstructionOperationResultFailure,
    HKHubArchInstructionOperationResultSuccess,
    HKHubArchInstructionOperationResultMask = 1,
    
    HKHubArchInstructionOperationResultFlagSkipPC = (1 << 1),
    HKHubArchInstructionOperationResultFlagPipelineStall = (1 << 2),
    HKHubArchInstructionOperationResultFlagInvalidOp = (1 << 3)
} HKHubArchInstructionOperationResult;

/*!
 * @brief Check if the register is a general purpose register.
 * @param Register The register.
 * @return Whether it's a general purpose register.
 */
static CC_FORCE_INLINE _Bool HKHubArchInstructionRegisterIsGeneralPurpose(HKHubArchInstructionRegister Register);

/*!
 * @brief Check if the register is a special purpose register.
 * @param Register The register.
 * @return Whether it's a special purpose register.
 */
static CC_FORCE_INLINE _Bool HKHubArchInstructionRegisterIsSpecialPurpose(HKHubArchInstructionRegister Register);

#pragma mark -

static CC_FORCE_INLINE _Bool HKHubArchInstructionRegisterIsGeneralPurpose(HKHubArchInstructionRegister Register)
{
    return Register & HKHubArchInstructionRegisterGeneralPurpose;
}

static CC_FORCE_INLINE _Bool HKHubArchInstructionRegisterIsSpecialPurpose(HKHubArchInstructionRegister Register)
{
    return (Register & (HKHubArchInstructionRegisterSpecialPurpose | HKHubArchInstructionRegisterGeneralPurpose)) == HKHubArchInstructionRegisterSpecialPurpose;
}

#endif
