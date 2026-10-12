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
#include "HubArchInstruction.h"


typedef enum {
    HKHubArchJITRegisterAL = 0,
    HKHubArchJITRegisterCL,
    HKHubArchJITRegisterDL,
    HKHubArchJITRegisterBL,
    HKHubArchJITRegisterAH,
    HKHubArchJITRegisterCH,
    HKHubArchJITRegisterDH,
    HKHubArchJITRegisterBH,
    
    HKHubArchJITRegisterSPL = HKHubArchJITRegisterAH,
    HKHubArchJITRegisterBPL = HKHubArchJITRegisterCH,
    HKHubArchJITRegisterSIL = HKHubArchJITRegisterDH,
    HKHubArchJITRegisterDIL = HKHubArchJITRegisterBH,
    
    HKHubArchJITRegisterAX = 0,
    HKHubArchJITRegisterCX,
    HKHubArchJITRegisterDX,
    HKHubArchJITRegisterBX,
    HKHubArchJITRegisterSP,
    HKHubArchJITRegisterBP,
    HKHubArchJITRegisterSI,
    HKHubArchJITRegisterDI,
    
    HKHubArchJITRegisterEAX = 0,
    HKHubArchJITRegisterECX,
    HKHubArchJITRegisterEDX,
    HKHubArchJITRegisterEBX,
    HKHubArchJITRegisterESP,
    HKHubArchJITRegisterEBP,
    HKHubArchJITRegisterESI,
    HKHubArchJITRegisterEDI,
    
    HKHubArchJITRegisterRAX = 0,
    HKHubArchJITRegisterRCX,
    HKHubArchJITRegisterRDX,
    HKHubArchJITRegisterRBX,
    HKHubArchJITRegisterRSP,
    HKHubArchJITRegisterRBP,
    HKHubArchJITRegisterRSI,
    HKHubArchJITRegisterRDI,
    
    HKHubArchJITRegisterR8B = 0,
    HKHubArchJITRegisterR9B,
    HKHubArchJITRegisterR10B,
    HKHubArchJITRegisterR11B,
    HKHubArchJITRegisterR12B,
    HKHubArchJITRegisterR13B,
    HKHubArchJITRegisterR14B,
    HKHubArchJITRegisterR15B,
    
    HKHubArchJITRegisterR8D = 0,
    HKHubArchJITRegisterR9D,
    HKHubArchJITRegisterR10D,
    HKHubArchJITRegisterR11D,
    HKHubArchJITRegisterR12D,
    HKHubArchJITRegisterR13D,
    HKHubArchJITRegisterR14D,
    HKHubArchJITRegisterR15D,
    
    HKHubArchJITRegisterR8 = 0,
    HKHubArchJITRegisterR9,
    HKHubArchJITRegisterR10,
    HKHubArchJITRegisterR11,
    HKHubArchJITRegisterR12,
    HKHubArchJITRegisterR13,
    HKHubArchJITRegisterR14,
    HKHubArchJITRegisterR15,
    
    HKHubArchJITRegisterCompatibilityR0 = HKHubArchJITRegisterBL,
    HKHubArchJITRegisterCompatibilityR1 = HKHubArchJITRegisterBH,
    HKHubArchJITRegisterCompatibilityR2 = HKHubArchJITRegisterCL,
    HKHubArchJITRegisterCompatibilityR3 = HKHubArchJITRegisterCH,
    HKHubArchJITRegisterCompatibilityFlags = HKHubArchJITRegisterDL,
    HKHubArchJITRegisterCompatibilityPC = HKHubArchJITRegisterDH,
    HKHubArchJITRegisterCompatibilityCycles = HKHubArchJITRegisterRSI,
    HKHubArchJITRegisterCompatibilityMemory = HKHubArchJITRegisterRDI
} HKHubArchJITRegister;

enum {
    HKHubArchJITRMSIB = HKHubArchJITRegisterRSP
};

typedef enum {
    HKHubArchJITModAddress,
    HKHubArchJITModAddressDisp8,
    HKHubArchJITModAddressDisp32,
    HKHubArchJITModRegister
} HKHubArchJITMod;

typedef enum {
    HKHubArchJITOpcodeAddMR8 = 0,
    HKHubArchJITOpcodeAddRM8 = 2,
    HKHubArchJITOpcodeSubMR8 = 0x28,
    HKHubArchJITOpcodeSubRM8 = 0x2a,
    HKHubArchJITOpcodeOrMR8 = 8,
    HKHubArchJITOpcodeOrRM8 = 0x0a,
    HKHubArchJITOpcodeXorMR8 = 0x30,
    HKHubArchJITOpcodeXorMR = 0x31,
    HKHubArchJITOpcodeXorRM8 = 0x32,
    HKHubArchJITOpcodeAndMR8 = 0x20,
    HKHubArchJITOpcodeAndRM8 = 0x22,
    HKHubArchJITOpcodeCmpMR8 = 0x38,
    HKHubArchJITOpcodeCmpRM8 = 0x3a,
    HKHubArchJITOpcodePushR = 0x50,
    HKHubArchJITOpcodePopR = 0x58,
    HKHubArchJITOpcodeMovMR8 = 0x88,
    HKHubArchJITOpcodeMovMR = 0x89,
    HKHubArchJITOpcodeMovRM8 = 0x8a,
    HKHubArchJITOpcodeMovRM = 0x8b,
    HKHubArchJITOpcodeArithmeticMI8 = 0x80,
    HKHubArchJITOpcodeArithmeticMIn = 0x81,
    HKHubArchJITOpcodeArithmeticMI = 0x83,
    HKHubArchJITOpcodeLahf = 0x9f,
    HKHubArchJITOpcodeBitAdjustMI8 = 0xc0,
    HKHubArchJITOpcodeBitAdjustMI = 0xc1,
    HKHubArchJITOpcodeBitAdjust1MI8 = 0xd0,
    HKHubArchJITOpcodeBitAdjust1MI = 0xd1,
    HKHubArchJITOpcodeBitAdjustMC8 = 0xd2,
    HKHubArchJITOpcodeNop = 0x90,
    HKHubArchJITOpcodeRetn = 0xc3,
    HKHubArchJITOpcodeMovOI8 = 0xb0,
    HKHubArchJITOpcodeMovOI = 0xb8,
    HKHubArchJITOpcodeMoveMI8 = 0xc6,
    HKHubArchJITOpcodeTestMR8 = 0x84,
    HKHubArchJITOpcodeCallD = 0xe8,
    HKHubArchJITOpcodeOneOpArithmeticM8 = 0xf6,
    HKHubArchJITOpcodeOneOpArithmeticM = 0xf7,
    HKHubArchJITOpcodeOneOpBranchM = 0xff,
    HKHubArchJITOpcodeCdq = 0x99
} HKHubArchJITOpcode;

typedef enum {
    HKHubArchJITJumpAbove = 0x77,
    HKHubArchJITJumpAboveEqual = 0x73,
    HKHubArchJITJumpBelow = 0x72,
    HKHubArchJITJumpBelowEqual = 0x76,
    HKHubArchJITJumpCarry = 0x72,
    HKHubArchJITJumpEqual = 0x74,
    HKHubArchJITJumpGreater = 0x7f,
    HKHubArchJITJumpGreaterEqual = 0x7d,
    HKHubArchJITJumpLess = 0x7c,
    HKHubArchJITJumpLessEqual = 0x7e,
    HKHubArchJITJumpNotAbove = 0x76,
    HKHubArchJITJumpNotAboveEqual = 0x72,
    HKHubArchJITJumpNotBelow = 0x73,
    HKHubArchJITJumpNotBelowEqual = 0x77,
    HKHubArchJITJumpNotCarry = 0x73,
    HKHubArchJITJumpNotEqual = 0x75,
    HKHubArchJITJumpNotGreater = 0x7e,
    HKHubArchJITJumpNotGreaterEqual = 0x7c,
    HKHubArchJITJumpNotLess = 0x7d,
    HKHubArchJITJumpNotLessEqual = 0x7f,
    HKHubArchJITJumpOverflow = 0x70,
    HKHubArchJITJumpSign = 0x78,
    HKHubArchJITJumpZero = 0x74,
    HKHubArchJITJumpNotOverflow = 0x71,
    HKHubArchJITJumpNotSign = 0x79,
    HKHubArchJITJumpNotZero = 0x75,
    HKHubArchJITJumpUnconditional = 0xeb
} HKHubArchJITJump;

typedef enum {
    HKHubArchJITArithmeticAdd,
    HKHubArchJITArithmeticOr,
    HKHubArchJITArithmeticAdc,
    HKHubArchJITArithmeticSbb,
    HKHubArchJITArithmeticAnd,
    HKHubArchJITArithmeticSub,
    HKHubArchJITArithmeticXor,
    HKHubArchJITArithmeticCmp
} HKHubArchJITArithmetic;

typedef enum {
    HKHubArchJITBitAdjustRol,
    HKHubArchJITBitAdjustRor,
    HKHubArchJITBitAdjustRcl,
    HKHubArchJITBitAdjustRcr,
    HKHubArchJITBitAdjustShl,
    HKHubArchJITBitAdjustShr,
    HKHubArchJITBitAdjustSal,
    HKHubArchJITBitAdjustSar
} HKHubArchJITBitAdjust;

typedef enum {
    HKHubArchJITOneOpArithmeticTest,
    HKHubArchJITOneOpArithmeticNot = 2,
    HKHubArchJITOneOpArithmeticNeg,
    HKHubArchJITOneOpArithmeticMul,
    HKHubArchJITOneOpArithmeticImul,
    HKHubArchJITOneOpArithmeticDiv,
    HKHubArchJITOneOpArithmeticIdiv
} HKHubArchJITOneOpArithmetic;

typedef enum {
    HKHubArchJITOneOpBranchInc,
    HKHubArchJITOneOpBranchDec,
    HKHubArchJITOneOpBranchCall,
    HKHubArchJITOneOpBranchCallF,
    HKHubArchJITOneOpBranchJmp,
    HKHubArchJITOneOpBranchJmpF,
    HKHubArchJITOneOpBranchPush
} HKHubArchJITOneOpBranch;

typedef enum {
    HKHubArchJITMoveMov
} HKHubArchJITMove;

enum {
    HKHubArchJIT0fPrefixOpcodeSeto = 0x90,
    HKHubArchJIT0fPrefixOpcodeSetz = 0x94,
    HKHubArchJIT0fPrefixOpcodeSetnz = 0x95,
    HKHubArchJIT0fPrefixOpcodeSetna = 0x96,
    HKHubArchJIT0fPrefixOpcodeSeta = 0x97,
    HKHubArchJIT0fPrefixOpcodeSets = 0x98,
    HKHubArchJIT0fPrefixOpcodeMovzxRM8 = 0xb6,
    HKHubArchJIT0fPrefixOpcodeMovsxRM8 = 0xbe
};

enum {
    HKHubArchJITRex = 0x40,
    HKHubArchJITRexB = 0x41,
    HKHubArchJITRexX = 0x42,
    HKHubArchJITRexR = 0x44,
    HKHubArchJITRexRB = HKHubArchJITRexR | HKHubArchJITRexB,
    HKHubArchJITRexW = 0x48,
    HKHubArchJIT16Bit = 0x66
};

typedef struct {
    uint8_t *jump;
    int32_t *rel;
    uint8_t pc;
} HKHubArchJITJumpRef;

CC_ARRAY_DECLARE(HKHubArchJITJumpRef);

#if CC_HARDWARE_ARCH_X86_64
static uint8_t HKHubArchJITGetRegister(HKHubArchInstructionRegister Reg)
{
    switch (Reg)
    {
        case HKHubArchInstructionRegisterR0:
            return HKHubArchJITRegisterCompatibilityR0;
            
        case HKHubArchInstructionRegisterR1:
            return HKHubArchJITRegisterCompatibilityR1;
            
        case HKHubArchInstructionRegisterR2:
            return HKHubArchJITRegisterCompatibilityR2;
            
        case HKHubArchInstructionRegisterR3:
            return HKHubArchJITRegisterCompatibilityR3;
            
        case HKHubArchInstructionRegisterFlags:
            return HKHubArchJITRegisterCompatibilityFlags;
            
        case HKHubArchInstructionRegisterPC:
            return HKHubArchJITRegisterCompatibilityPC;
            
        default:
            break;
    }
    
    CCAssertLog(0, "Unsupported register type");
    
    return 0;
}

static CC_FORCE_INLINE uint8_t HKHubArchJITModRM(HKHubArchJITMod Mod, uint8_t Reg, uint8_t Rm)
{
    return (Mod << 6) | (Reg << 3) | Rm;
}

static CC_FORCE_INLINE uint8_t HKHubArchJITSIB(uint8_t Scale, HKHubArchJITRegister Index, HKHubArchJITRegister Base)
{
    return (Scale << 6) | (Index << 3) | Base;
}

static uint8_t HKHubArchJITGetModRM(const HKHubArchExecutionGraphInstruction *Instruction)
{
    if (Instruction->state.operand[0].type == HKHubArchInstructionOperandR)
    {
        if (Instruction->state.operand[1].type == HKHubArchInstructionOperandR)
        {
            return HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITGetRegister(Instruction->state.operand[1].reg), HKHubArchJITGetRegister(Instruction->state.operand[0].reg));
        }
    }
    
    return 0;
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionSeto(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Reg)
{
    Ptr[(*Index)++] = 0x0f;
    Ptr[(*Index)++] = HKHubArchJIT0fPrefixOpcodeSeto;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, 0, Reg);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionSetz(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Reg)
{
    Ptr[(*Index)++] = 0x0f;
    Ptr[(*Index)++] = HKHubArchJIT0fPrefixOpcodeSetz;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, 0, Reg);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionSetnz(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Reg)
{
    Ptr[(*Index)++] = 0x0f;
    Ptr[(*Index)++] = HKHubArchJIT0fPrefixOpcodeSetnz;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, 0, Reg);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionSetna(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Reg)
{
    Ptr[(*Index)++] = 0x0f;
    Ptr[(*Index)++] = HKHubArchJIT0fPrefixOpcodeSetna;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, 0, Reg);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionSeta(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Reg)
{
    Ptr[(*Index)++] = 0x0f;
    Ptr[(*Index)++] = HKHubArchJIT0fPrefixOpcodeSeta;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, 0, Reg);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionSets(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Reg)
{
    Ptr[(*Index)++] = 0x0f;
    Ptr[(*Index)++] = HKHubArchJIT0fPrefixOpcodeSets;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, 0, Reg);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionMovzxRM8(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Dst, HKHubArchJITRegister Src)
{
    Ptr[(*Index)++] = 0x0f;
    Ptr[(*Index)++] = HKHubArchJIT0fPrefixOpcodeMovzxRM8;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Dst, Src);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionMovsxRM8(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Dst, HKHubArchJITRegister Src)
{
    Ptr[(*Index)++] = 0x0f;
    Ptr[(*Index)++] = HKHubArchJIT0fPrefixOpcodeMovsxRM8;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Dst, Src);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionSubMR8(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Dst, HKHubArchJITRegister Src)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodeSubMR8;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Src, Dst);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionOrMR8(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Dst, HKHubArchJITRegister Src)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodeOrMR8;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Src, Dst);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionAndMR8(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Dst, HKHubArchJITRegister Src)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodeAndMR8;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Src, Dst);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionTestMR8(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Dst, HKHubArchJITRegister Src)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodeTestMR8;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Src, Dst);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionXorMR8(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Dst, HKHubArchJITRegister Src)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodeXorMR8;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Src, Dst);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionXorMR(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Dst, HKHubArchJITRegister Src)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodeXorMR;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Src, Dst);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionPushR(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Reg)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodePushR + Reg;
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionPopR(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Reg)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodePopR + Reg;
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionMovOI8(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Reg, uint8_t Imm8)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodeMovOI8 + Reg;
    Ptr[(*Index)++] = Imm8;
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionMovMR8(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Dst, HKHubArchJITRegister Src)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodeMovMR8;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Src, Dst);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionMovMR(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Dst, HKHubArchJITRegister Src)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodeMovMR;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Src, Dst);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionMovOI(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Reg, uint32_t Imm32)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodeMovOI + Reg;
    *(uint32_t*)&Ptr[*Index] = Imm32;
    *Index += 4;
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionMovOI64(uint8_t *Ptr, size_t *Index, HKHubArchJITRegister Reg, uint64_t Imm64)
{
    Ptr[(*Index)++] = HKHubArchJITRexW;
    Ptr[(*Index)++] = HKHubArchJITOpcodeMovOI + Reg;
    *(uint64_t*)&Ptr[*Index] = Imm64;
    *Index += 8;
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionArithmeticMI8(uint8_t *Ptr, size_t *Index, HKHubArchJITArithmetic Type, HKHubArchJITRegister Reg, uint8_t Imm8)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodeArithmeticMI8;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Type, Reg);
    Ptr[(*Index)++] = Imm8;
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionArithmeticMI(uint8_t *Ptr, size_t *Index, HKHubArchJITArithmetic Type, HKHubArchJITRegister Reg, uint8_t Imm8)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodeArithmeticMI;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Type, Reg);
    Ptr[(*Index)++] = Imm8;
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionArithmeticMIn(uint8_t *Ptr, size_t *Index, HKHubArchJITArithmetic Type, HKHubArchJITRegister Reg, uint32_t Imm32)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodeArithmeticMIn;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Type, Reg);
    *(uint32_t*)&Ptr[*Index] = Imm32;
    *Index += 4;
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionBitAdjustMI8(uint8_t *Ptr, size_t *Index, HKHubArchJITBitAdjust Type, HKHubArchJITRegister Reg, uint8_t Imm8)
{
    if (Imm8 == 1)
    {
        Ptr[(*Index)++] = HKHubArchJITOpcodeBitAdjust1MI8;
        Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Type, Reg);
    }
    
    else if (Imm8)
    {
        Ptr[(*Index)++] = HKHubArchJITOpcodeBitAdjustMI8;
        Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Type, Reg);
        Ptr[(*Index)++] = Imm8;
    }
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionBitAdjustMI(uint8_t *Ptr, size_t *Index, HKHubArchJITBitAdjust Type, HKHubArchJITRegister Reg, uint8_t Imm8)
{
    if (Imm8 == 1)
    {
        Ptr[(*Index)++] = HKHubArchJITOpcodeBitAdjust1MI;
        Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Type, Reg);
    }
    
    else if (Imm8)
    {
        Ptr[(*Index)++] = HKHubArchJITOpcodeBitAdjustMI;
        Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Type, Reg);
        Ptr[(*Index)++] = Imm8;
    }
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionBitAdjustMC8(uint8_t *Ptr, size_t *Index, HKHubArchJITBitAdjust Type, HKHubArchJITRegister Reg)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodeBitAdjustMC8;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Type, Reg);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionArithmeticM8(uint8_t *Ptr, size_t *Index, HKHubArchJITOneOpArithmetic Type, HKHubArchJITRegister Reg)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodeOneOpArithmeticM8;
    Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, Type, Reg);
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionCall(uint8_t *Ptr, size_t *Index, uintptr_t Address, HKHubArchJITRegister Reg)
{
    ptrdiff_t Rel = (Address - (ptrdiff_t)(Ptr + *Index)) - 5;
    if ((Rel < INT32_MIN) || (Rel > INT32_MAX))
    {
        HKHubArchJITAddInstructionMovOI64(Ptr, Index, Reg, Address);
        Ptr[(*Index)++] = HKHubArchJITOpcodeOneOpBranchM;
        Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpBranchCall, Reg);
    }
    
    else
    {
        Ptr[(*Index)++] = HKHubArchJITOpcodeCallD;
        *(int32_t*)&Ptr[*Index] = (int32_t)Rel;
        *Index += 4;
    }
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionJumpRel8(uint8_t *Ptr, size_t *Index, HKHubArchJITJump Type, int8_t Rel8)
{
    Ptr[(*Index)++] = Type;
    Ptr[(*Index)++] = Rel8;
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionJumpRel32(uint8_t *Ptr, size_t *Index, HKHubArchJITJump Type, int32_t Rel32)
{
    if (Type != HKHubArchJITJumpUnconditional)
    {
        Ptr[(*Index)++] = 0x0f;
        Type += 0x10;
    }
    
    else Type = 0xe9;
    
    Ptr[(*Index)++] = Type;
    *(int32_t*)&Ptr[*Index] = Rel32;
    
    *Index += 4;
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionReturn(uint8_t *Ptr, size_t *Index)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodeRetn;
}

static void HKHubArchJITCopyFlagsSCZPresetO(uint8_t *Ptr, size_t *Index)
{
    Ptr[(*Index)++] = HKHubArchJITOpcodeLahf;
    
    /*
     sz0a0p1c 0000000o
     z0a0p1c0 000000os = AX rol 1
     c0z0a0p1          = AH ror 2
     0z0a0p10 00000osc = AX rol 1
     z0a0p100          = AH << 1
     0a0p1000 0000oscz = AX rol 1
     */
    Ptr[(*Index)++] = HKHubArchJIT16Bit;
    HKHubArchJITAddInstructionBitAdjustMI(Ptr, Index, HKHubArchJITBitAdjustRol, HKHubArchJITRegisterAX, 1);
    HKHubArchJITAddInstructionBitAdjustMI8(Ptr, Index, HKHubArchJITBitAdjustRor, HKHubArchJITRegisterAH, 2);
    Ptr[(*Index)++] = HKHubArchJIT16Bit;
    HKHubArchJITAddInstructionBitAdjustMI(Ptr, Index, HKHubArchJITBitAdjustRol, HKHubArchJITRegisterAX, 1);
    HKHubArchJITAddInstructionBitAdjustMI8(Ptr, Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAH, 1);
    Ptr[(*Index)++] = HKHubArchJIT16Bit;
    HKHubArchJITAddInstructionBitAdjustMI(Ptr, Index, HKHubArchJITBitAdjustRol, HKHubArchJITRegisterAX, 1);
    HKHubArchJITAddInstructionArithmeticMI8(Ptr, Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterCompatibilityFlags, 0xf0);
    HKHubArchJITAddInstructionOrMR8(Ptr, Index, HKHubArchJITRegisterCompatibilityFlags, HKHubArchJITRegisterAL);
}

static void HKHubArchJITCopyFlags(uint8_t *Ptr, size_t *Index)
{
    HKHubArchJITAddInstructionSeto(Ptr, Index, HKHubArchJITRegisterAL);
    
    HKHubArchJITCopyFlagsSCZPresetO(Ptr, Index);
}

static void HKHubArchJITCheckCycles(uint8_t *Ptr, size_t *Index, size_t Cost, const HKHubArchExecutionGraphInstruction *Instruction)
{
    size_t Cycles = Cost;
    const HKHubArchInstructionMemoryOperation MemoryOp = HKHubArchInstructionGetMemoryOperation(&Instruction->state);
    for (size_t Loop = 0; Loop < 3; Loop++)
    {
        if (Instruction->state.operand[Loop].type == HKHubArchInstructionOperandM)
        {
            _Static_assert(HKHubArchInstructionMemoryOperationOp1 == 0 &&
                           HKHubArchInstructionMemoryOperationOp2 == 2 &&
                           HKHubArchInstructionMemoryOperationOp3 == 4, "Expects the following operand mask layout");
            
            Cycles += (((MemoryOp >> (Loop * 2)) & HKHubArchInstructionMemoryOperationSrc) ? HKHubArchProcessorSpeedMemoryRead : 0) + (((MemoryOp >> (Loop * 2)) & HKHubArchInstructionMemoryOperationDst) ? HKHubArchProcessorSpeedMemoryWrite : 0);
        }
    }
    
    Ptr[(*Index)++] = HKHubArchJITRexW;
    HKHubArchJITAddInstructionArithmeticMI(Ptr, Index, HKHubArchJITArithmeticSub, HKHubArchJITRegisterCompatibilityCycles, Cycles);
    HKHubArchJITAddInstructionJumpRel8(Ptr, Index, HKHubArchJITJumpNotBelow, 5);
    Ptr[(*Index)++] = HKHubArchJITRexW;
    HKHubArchJITAddInstructionArithmeticMI(Ptr, Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterCompatibilityCycles, Cycles);
    HKHubArchJITAddInstructionReturn(Ptr, Index);
}

static void HKHubArchJITCheckMemoryAccess(uint8_t *Ptr, size_t *Index, const HKHubArchExecutionGraphInstruction *Instruction, HKHubArchJITRegister Offset)
{
    const HKHubArchInstructionMemoryOperation MemoryOp = HKHubArchInstructionGetMemoryOperation(&Instruction->state);
    for (size_t Loop = 0; Loop < 3; Loop++)
    {
        if ((((MemoryOp >> (Loop * 2)) & HKHubArchInstructionMemoryOperationDst)) && (Instruction->state.operand[Loop].type == HKHubArchInstructionOperandM))
        {
            /*
             TODO: If memory operand is a literal then it can avoid adding a check and instead add it to a list of invalidated memory addresses.
             then after creation of the jit it invalidates all of those constant addresses.
             */
            HKHubArchJITAddInstructionPushR(Ptr, Index, HKHubArchJITRegisterRBX);
            HKHubArchJITAddInstructionPushR(Ptr, Index, HKHubArchJITRegisterRCX);
            HKHubArchJITAddInstructionPushR(Ptr, Index, HKHubArchJITRegisterRDX);
            HKHubArchJITAddInstructionPushR(Ptr, Index, HKHubArchJITRegisterRSI);
            HKHubArchJITAddInstructionPushR(Ptr, Index, HKHubArchJITRegisterRDI);
            
            if (Instruction->state.operand[Loop].memory.type == HKHubArchInstructionMemoryOffset)
            {
                Ptr[(*Index)++] = HKHubArchJITRexW;
                HKHubArchJITAddInstructionXorMR(Ptr, Index, HKHubArchJITRegisterRSI, HKHubArchJITRegisterRSI);
                Ptr[(*Index)++] = HKHubArchJITRex;
                HKHubArchJITAddInstructionMovOI8(Ptr, Index, HKHubArchJITRegisterSIL, Instruction->state.operand[Loop].memory.offset);
            }
            
            else
            {
                HKHubArchJITAddInstructionMovMR(Ptr, Index, HKHubArchJITRegisterRSI, Offset);
            }
            
            const int32_t JitField = (int32_t)(offsetof(HKHubArchProcessorInfo, cache.jit) - offsetof(HKHubArchProcessorInfo, memory));
            
            Ptr[(*Index)++] = HKHubArchJITRexW;
            Ptr[(*Index)++] = HKHubArchJITOpcodeMovRM;
            if ((JitField < INT8_MIN) || (JitField > INT8_MAX))
            {
                Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModAddressDisp32, HKHubArchJITRegisterRDI, HKHubArchJITRegisterCompatibilityMemory);
                *(int32_t*)&Ptr[*Index] = JitField;
                *Index += 4;
            }
            
            else
            {
                Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModAddressDisp8, HKHubArchJITRegisterRDI, HKHubArchJITRegisterCompatibilityMemory);
                *(int8_t*)&Ptr[(*Index)++] = (int8_t)JitField;
            }
            
            Ptr[(*Index)++] = HKHubArchJITRexW;
            HKHubArchJITAddInstructionXorMR(Ptr, Index, HKHubArchJITRegisterRDX, HKHubArchJITRegisterRDX);
            Ptr[(*Index)++] = HKHubArchJITOpcodeOneOpBranchM;
            Ptr[(*Index)++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpBranchInc, HKHubArchJITRegisterEDX);
            
            HKHubArchJITAddInstructionCall(Ptr, Index, (uintptr_t)HKHubArchJITInvalidateBlocks, HKHubArchJITRegisterRAX);
            
            HKHubArchJITAddInstructionPopR(Ptr, Index, HKHubArchJITRegisterRDI);
            HKHubArchJITAddInstructionPopR(Ptr, Index, HKHubArchJITRegisterRSI);
            HKHubArchJITAddInstructionPopR(Ptr, Index, HKHubArchJITRegisterRDX);
            HKHubArchJITAddInstructionPopR(Ptr, Index, HKHubArchJITRegisterRCX);
            HKHubArchJITAddInstructionPopR(Ptr, Index, HKHubArchJITRegisterRBX);
        }
    }
}

static size_t HKHubArchJITGenerate0OperandMutator(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, uint8_t Type, size_t Cost, _Bool FlagsAffected)
{
    const size_t Size = HKHubArchInstructionSizeOfEncoding(&Instruction->state);
    
    size_t Index = 0;
    HKHubArchJITCheckCycles(Ptr, &Index, Cost + (Size * HKHubArchProcessorSpeedMemoryRead), Instruction);
    
    if (Type != HKHubArchJITOpcodeNop)
    {
        Ptr[Index++] = Type;
        
        if (FlagsAffected) HKHubArchJITCopyFlags(Ptr, &Index);
    }
    
    HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterCompatibilityPC, Size);
    
    return Index;
}

static size_t HKHubArchJITGenerate1OperandMutator(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, uint8_t Type, HKHubArchJITOpcode OpcodeM, size_t Cost, _Bool FlagsAffected, _Bool ManualFlagTest, _Bool MemoryCheck)
{
    const size_t Size = HKHubArchInstructionSizeOfEncoding(&Instruction->state);
    
    size_t Index = 0;
    HKHubArchJITCheckCycles(Ptr, &Index, Cost + (Size * HKHubArchProcessorSpeedMemoryRead), Instruction);
    
    if (Instruction->state.operand[0].type == HKHubArchInstructionOperandR)
    {
        HKHubArchJITRegister Dst = HKHubArchJITGetRegister(Instruction->state.operand[0].reg);
        
        Ptr[Index++] = OpcodeM;
        Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, Type, Dst);
        
        if (FlagsAffected)
        {
            if (ManualFlagTest)
            {
                HKHubArchJITAddInstructionTestMR8(Ptr, &Index, Dst, Dst);
                HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                HKHubArchJITAddInstructionSets(Ptr, &Index, HKHubArchJITRegisterAH);
                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAH, 2);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterCompatibilityFlags, 0xf0);
                HKHubArchJITAddInstructionOrMR8(Ptr, &Index, HKHubArchJITRegisterCompatibilityFlags, HKHubArchJITRegisterAL);
                HKHubArchJITAddInstructionOrMR8(Ptr, &Index, HKHubArchJITRegisterCompatibilityFlags, HKHubArchJITRegisterAH);
            }
            
            else HKHubArchJITCopyFlags(Ptr, &Index);
        }
        
        if (HKHubArchInstructionRegisterIsSpecialPurpose(Instruction->state.operand[0].reg) && (Instruction->state.operand[0].reg == HKHubArchInstructionRegisterPC) && ((HKHubArchInstructionGetMemoryOperation(&Instruction->state) >> HKHubArchInstructionMemoryOperationOp1) & HKHubArchInstructionMemoryOperationDst)) HKHubArchJITAddInstructionReturn(Ptr, &Index);
        else HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterCompatibilityPC, Size);
    }
    
    else if (Instruction->state.operand[0].type == HKHubArchInstructionOperandM)
    {
        switch (Instruction->state.operand[0].memory.type)
        {
            case HKHubArchInstructionMemoryOffset:
                Ptr[Index++] = OpcodeM;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddressDisp32, Type, HKHubArchJITRegisterCompatibilityMemory);
                *(uint32_t*)&Ptr[Index] = Instruction->state.operand[0].memory.offset;
                Index += 4;
                break;
                
            case HKHubArchInstructionMemoryRegister:
                HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.reg));
                Ptr[Index++] = OpcodeM;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, Type, HKHubArchJITRMSIB);
                Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                break;
                
            case HKHubArchInstructionMemoryRelativeOffset:
                HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeOffset.reg));
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterAL, Instruction->state.operand[0].memory.relativeOffset.offset);
                Ptr[Index++] = OpcodeM;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, Type, HKHubArchJITRMSIB);
                Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                break;
                
            case HKHubArchInstructionMemoryRelativeRegister:
                HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeReg[0]));
                Ptr[Index++] = HKHubArchJITOpcodeAddMR8;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeReg[1]), HKHubArchJITRegisterAL);
                Ptr[Index++] = OpcodeM;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, Type, HKHubArchJITRMSIB);
                Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                break;
        }
        
        if (MemoryCheck)
        {
            HKHubArchJITAddInstructionPushR(Ptr, &Index, HKHubArchJITRegisterRAX);
            HKHubArchJITCheckMemoryAccess(Ptr, &Index, Instruction, HKHubArchJITRegisterRAX);
            HKHubArchJITAddInstructionPopR(Ptr, &Index, HKHubArchJITRegisterRAX);
        }
        
        if (FlagsAffected)
        {
            if (ManualFlagTest)
            {
                switch (Instruction->state.operand[0].memory.type)
                {
                    case HKHubArchInstructionMemoryOffset:
                        Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                        Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddressDisp32, HKHubArchJITRegisterAL, HKHubArchJITRegisterCompatibilityMemory);
                        *(uint32_t*)&Ptr[Index] = Instruction->state.operand[0].memory.offset;
                        Index += 4;
                        break;
                        
                    case HKHubArchInstructionMemoryRegister:
                        Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                        Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAL, HKHubArchJITRMSIB);
                        Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                        break;
                        
                    case HKHubArchInstructionMemoryRelativeOffset:
                        Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                        Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAL, HKHubArchJITRMSIB);
                        Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                        break;
                        
                    case HKHubArchInstructionMemoryRelativeRegister:
                        Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                        Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAL, HKHubArchJITRMSIB);
                        Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                        break;
                }
                
                HKHubArchJITAddInstructionTestMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAL);
                HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                HKHubArchJITAddInstructionSets(Ptr, &Index, HKHubArchJITRegisterAH);
                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAH, 2);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterCompatibilityFlags, 0xf0);
                HKHubArchJITAddInstructionOrMR8(Ptr, &Index, HKHubArchJITRegisterCompatibilityFlags, HKHubArchJITRegisterAL);
                HKHubArchJITAddInstructionOrMR8(Ptr, &Index, HKHubArchJITRegisterCompatibilityFlags, HKHubArchJITRegisterAH);
            }
            
            else HKHubArchJITCopyFlags(Ptr, &Index);
        }
        
        HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterCompatibilityPC, Size);
    }
    
    return Index;
}

static size_t HKHubArchJITGenerate2OperandMutator(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, uint8_t Type, HKHubArchJITOpcode OpcodeMR, HKHubArchJITOpcode OpcodeRM, HKHubArchJITOpcode OpcodeMI, size_t Cost, _Bool FlagsAffected, _Bool MemoryCheck)
{
    const size_t Size = HKHubArchInstructionSizeOfEncoding(&Instruction->state);
    
    size_t Index = 0;
    HKHubArchJITCheckCycles(Ptr, &Index, Cost + (Size * HKHubArchProcessorSpeedMemoryRead), Instruction);
    
    if (Instruction->state.operand[0].type == HKHubArchInstructionOperandR)
    {
        if (Instruction->state.operand[1].type == HKHubArchInstructionOperandR)
        {
            Ptr[Index++] = OpcodeMR;
            Ptr[Index++] = HKHubArchJITGetModRM(Instruction);
        }
        
        else if (Instruction->state.operand[1].type == HKHubArchInstructionOperandI)
        {
            Ptr[Index++] = OpcodeMI;
            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, Type, HKHubArchJITGetRegister(Instruction->state.operand[0].reg));
            Ptr[Index++] = Instruction->state.operand[1].value;
        }
        
        else if (Instruction->state.operand[1].type == HKHubArchInstructionOperandM)
        {
            switch (Instruction->state.operand[1].memory.type)
            {
                case HKHubArchInstructionMemoryOffset:
                    Ptr[Index++] = OpcodeRM;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddressDisp32, HKHubArchJITGetRegister(Instruction->state.operand[0].reg), HKHubArchJITRegisterCompatibilityMemory);
                    *(uint32_t*)&Ptr[Index] = Instruction->state.operand[1].memory.offset;
                    Index += 4;
                    break;
                    
                case HKHubArchInstructionMemoryRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.reg));
                    Ptr[Index++] = OpcodeRM;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITGetRegister(Instruction->state.operand[0].reg), HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
                    
                case HKHubArchInstructionMemoryRelativeOffset:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.relativeOffset.reg));
                    HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterAL, Instruction->state.operand[1].memory.relativeOffset.offset);
                    Ptr[Index++] = OpcodeRM;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITGetRegister(Instruction->state.operand[0].reg), HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
                    
                case HKHubArchInstructionMemoryRelativeRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.relativeReg[0]));
                    Ptr[Index++] = HKHubArchJITOpcodeAddMR8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.relativeReg[1]), HKHubArchJITRegisterAL);
                    Ptr[Index++] = OpcodeRM;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITGetRegister(Instruction->state.operand[0].reg), HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
            }
        }
        
        if (FlagsAffected) HKHubArchJITCopyFlags(Ptr, &Index);
        
        if (HKHubArchInstructionRegisterIsSpecialPurpose(Instruction->state.operand[0].reg) && (Instruction->state.operand[0].reg == HKHubArchInstructionRegisterPC) && ((HKHubArchInstructionGetMemoryOperation(&Instruction->state) >> HKHubArchInstructionMemoryOperationOp1) & HKHubArchInstructionMemoryOperationDst)) HKHubArchJITAddInstructionReturn(Ptr, &Index);
        else HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterCompatibilityPC, Size);
    }
    
    else if (Instruction->state.operand[0].type == HKHubArchInstructionOperandM)
    {
        if (Instruction->state.operand[1].type == HKHubArchInstructionOperandR)
        {
            switch (Instruction->state.operand[0].memory.type)
            {
                case HKHubArchInstructionMemoryOffset:
                    Ptr[Index++] = OpcodeMR;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddressDisp32, HKHubArchJITGetRegister(Instruction->state.operand[1].reg), HKHubArchJITRegisterCompatibilityMemory);
                    *(uint32_t*)&Ptr[Index] = Instruction->state.operand[0].memory.offset;
                    Index += 4;
                    break;
                    
                case HKHubArchInstructionMemoryRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.reg));
                    Ptr[Index++] = OpcodeMR;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITGetRegister(Instruction->state.operand[1].reg), HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
                    
                case HKHubArchInstructionMemoryRelativeOffset:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeOffset.reg));
                    HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterAL, Instruction->state.operand[0].memory.relativeOffset.offset);
                    Ptr[Index++] = OpcodeMR;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITGetRegister(Instruction->state.operand[1].reg), HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
                    
                case HKHubArchInstructionMemoryRelativeRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeReg[0]));
                    Ptr[Index++] = HKHubArchJITOpcodeAddMR8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeReg[1]), HKHubArchJITRegisterAL);
                    Ptr[Index++] = OpcodeMR;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITGetRegister(Instruction->state.operand[1].reg), HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
            }
            
            if (MemoryCheck) HKHubArchJITCheckMemoryAccess(Ptr, &Index, Instruction, HKHubArchJITRegisterRAX);
        }
        
        else if (Instruction->state.operand[1].type == HKHubArchInstructionOperandI)
        {
            switch (Instruction->state.operand[0].memory.type)
            {
                case HKHubArchInstructionMemoryOffset:
                    Ptr[Index++] = OpcodeMI;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddressDisp32, Type, HKHubArchJITRegisterCompatibilityMemory);
                    *(uint32_t*)&Ptr[Index] = Instruction->state.operand[0].memory.offset;
                    Index += 4;
                    Ptr[Index++] = Instruction->state.operand[1].value;
                    break;
                    
                case HKHubArchInstructionMemoryRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.reg));
                    Ptr[Index++] = OpcodeMI;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, Type, HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    Ptr[Index++] = Instruction->state.operand[1].value;
                    break;
                    
                case HKHubArchInstructionMemoryRelativeOffset:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeOffset.reg));
                    HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterAL, Instruction->state.operand[0].memory.relativeOffset.offset);
                    Ptr[Index++] = OpcodeMI;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, Type, HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    Ptr[Index++] = Instruction->state.operand[1].value;
                    break;
                    
                case HKHubArchInstructionMemoryRelativeRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeReg[0]));
                    Ptr[Index++] = HKHubArchJITOpcodeAddMR8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeReg[1]), HKHubArchJITRegisterAL);
                    Ptr[Index++] = OpcodeMI;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, Type, HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    Ptr[Index++] = Instruction->state.operand[1].value;
                    break;
            }
            
            if (MemoryCheck) HKHubArchJITCheckMemoryAccess(Ptr, &Index, Instruction, HKHubArchJITRegisterRAX);
        }
        
        else if (Instruction->state.operand[1].type == HKHubArchInstructionOperandM)
        {
            switch (Instruction->state.operand[0].memory.type)
            {
                case HKHubArchInstructionMemoryOffset:
                    HKHubArchJITAddInstructionMovOI(Ptr, &Index, HKHubArchJITRegisterEBP, Instruction->state.operand[0].memory.offset);
                    break;
                    
                case HKHubArchInstructionMemoryRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEBP, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.reg));
                    break;
                    
                case HKHubArchInstructionMemoryRelativeOffset:
                    Ptr[Index++] = HKHubArchJITOpcodeMovMR8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeOffset.reg), HKHubArchJITRegisterAL);
                    HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterAL, Instruction->state.operand[0].memory.relativeOffset.offset);
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEBP, HKHubArchJITRegisterAL);
                    break;
                    
                case HKHubArchInstructionMemoryRelativeRegister:
                    Ptr[Index++] = HKHubArchJITOpcodeMovMR8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeReg[0]), HKHubArchJITRegisterAL);
                    Ptr[Index++] = HKHubArchJITOpcodeAddMR8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeReg[1]), HKHubArchJITRegisterAL);
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEBP, HKHubArchJITRegisterAL);
                    break;
            }
            
            if (MemoryCheck)
            {
                HKHubArchJITAddInstructionPushR(Ptr, &Index, HKHubArchJITRegisterRBP);
                HKHubArchJITCheckMemoryAccess(Ptr, &Index, Instruction, HKHubArchJITRegisterRBP);
                HKHubArchJITAddInstructionPopR(Ptr, &Index, HKHubArchJITRegisterRBP);
            }
            
            switch (Instruction->state.operand[1].memory.type)
            {
                case HKHubArchInstructionMemoryOffset:
                    Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddressDisp32, HKHubArchJITRegisterAL, HKHubArchJITRegisterCompatibilityMemory);
                    *(uint32_t*)&Ptr[Index] = Instruction->state.operand[1].memory.offset;
                    Index += 4;
                    break;
                    
                case HKHubArchInstructionMemoryRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.reg));
                    Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAL, HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
                    
                case HKHubArchInstructionMemoryRelativeOffset:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.relativeOffset.reg));
                    HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterAL, Instruction->state.operand[1].memory.relativeOffset.offset);
                    Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAL, HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
                    
                case HKHubArchInstructionMemoryRelativeRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.relativeReg[0]));
                    Ptr[Index++] = HKHubArchJITOpcodeAddMR8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.relativeReg[1]), HKHubArchJITRegisterAL);
                    Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAL, HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
            }
            
            Ptr[Index++] = OpcodeMR;
            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAL, HKHubArchJITRMSIB);
            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
        }
        
        if (FlagsAffected) HKHubArchJITCopyFlags(Ptr, &Index);
        
        HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterCompatibilityPC, Size);
    }
    
    return Index;
}

static CC_FORCE_INLINE void HKHubArchJITAddInstructionBitAdjustMR8(uint8_t *Ptr, size_t *Index, HKHubArchJITBitAdjust Type, HKHubArchJITRegister Dst, HKHubArchJITRegister Src)
{
    HKHubArchJITRegister Target = Dst;
    
    if (Src != HKHubArchJITRegisterCL)
    {
        HKHubArchJITAddInstructionMovMR8(Ptr, Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterCL);
        HKHubArchJITAddInstructionMovMR8(Ptr, Index, HKHubArchJITRegisterCL, Src);
        
        if (Dst == HKHubArchJITRegisterCL) Target = HKHubArchJITRegisterAL;
    }
    
    HKHubArchJITAddInstructionBitAdjustMC8(Ptr, Index, Type, Target);
    
    if (Src != HKHubArchJITRegisterCL) HKHubArchJITAddInstructionMovMR8(Ptr, Index, HKHubArchJITRegisterCL, HKHubArchJITRegisterAL);
}

static size_t HKHubArchJITGenerate2OperandBitMutator(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, uint8_t Type, size_t Cost, _Bool FlagsAffected)
{
    const size_t Size = HKHubArchInstructionSizeOfEncoding(&Instruction->state);
    
    size_t Index = 0;
    HKHubArchJITCheckCycles(Ptr, &Index, Cost + (Size * HKHubArchProcessorSpeedMemoryRead), Instruction);
    
    if (Instruction->state.operand[0].type == HKHubArchInstructionOperandR)
    {
        if (Instruction->state.operand[1].type == HKHubArchInstructionOperandR)
        {
            const HKHubArchJITRegister Dst = HKHubArchJITGetRegister(Instruction->state.operand[0].reg), Src = HKHubArchJITGetRegister(Instruction->state.operand[1].reg);
            
            HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterCL);
            HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAH, Dst);
            
            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterCL, 8);
            HKHubArchJITAddInstructionSubMR8(Ptr, &Index, HKHubArchJITRegisterCL, (Src == HKHubArchJITRegisterCL ? HKHubArchJITRegisterAL : Src));
            HKHubArchJITAddInstructionJumpRel8(Ptr, &Index, HKHubArchJITJumpCarry, 2);
            HKHubArchJITAddInstructionBitAdjustMC8(Ptr, &Index, (Type == HKHubArchJITBitAdjustShl ? HKHubArchJITBitAdjustShr : HKHubArchJITBitAdjustShl), HKHubArchJITRegisterAH);
            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, HKHubArchJITRegisterAH, HKHubArchJITRegisterAH);
            Ptr[Index++] = HKHubArchJITRexB;
            HKHubArchJITAddInstructionSetnz(Ptr, &Index, HKHubArchJITRegisterR8B);
            HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterCL, HKHubArchJITRegisterAL);
            
            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, Dst, Dst);
            HKHubArchJITAddInstructionBitAdjustMR8(Ptr, &Index, Type, Dst, Src);
        }
        
        else if (Instruction->state.operand[1].type == HKHubArchInstructionOperandI)
        {
            const HKHubArchJITRegister Dst = HKHubArchJITGetRegister(Instruction->state.operand[0].reg);
            
            if (Instruction->state.operand[1].value)
            {
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterCL);
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAH, Dst);
                
                HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterCL, 8);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticSub, HKHubArchJITRegisterCL, Instruction->state.operand[1].value);
                HKHubArchJITAddInstructionJumpRel8(Ptr, &Index, HKHubArchJITJumpCarry, 2);
                HKHubArchJITAddInstructionBitAdjustMC8(Ptr, &Index, (Type == HKHubArchJITBitAdjustShl ? HKHubArchJITBitAdjustShr : HKHubArchJITBitAdjustShl), HKHubArchJITRegisterAH);
                HKHubArchJITAddInstructionTestMR8(Ptr, &Index, HKHubArchJITRegisterAH, HKHubArchJITRegisterAH);
                Ptr[Index++] = HKHubArchJITRexB;
                HKHubArchJITAddInstructionSetnz(Ptr, &Index, HKHubArchJITRegisterR8B);
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterCL, HKHubArchJITRegisterAL);
                
                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, Type, Dst, Instruction->state.operand[1].value);
            }
            
            else
            {
                // optimize, can do this afterwards and set AL directly
                Ptr[Index++] = HKHubArchJITRexRB;
                HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterR8B, HKHubArchJITRegisterR8B);
                
                HKHubArchJITAddInstructionTestMR8(Ptr, &Index, Dst, Dst);
            }            
        }
        
        else if (Instruction->state.operand[1].type == HKHubArchInstructionOperandM)
        {
            switch (Instruction->state.operand[1].memory.type)
            {
                case HKHubArchInstructionMemoryOffset:
                    Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddressDisp32, HKHubArchJITRegisterAH, HKHubArchJITRegisterCompatibilityMemory);
                    *(uint32_t*)&Ptr[Index] = Instruction->state.operand[1].memory.offset;
                    Index += 4;
                    break;
                    
                case HKHubArchInstructionMemoryRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.reg));
                    Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAH, HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
                    
                case HKHubArchInstructionMemoryRelativeOffset:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.relativeOffset.reg));
                    HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterAL, Instruction->state.operand[1].memory.relativeOffset.offset);
                    Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAH, HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
                    
                case HKHubArchInstructionMemoryRelativeRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.relativeReg[0]));
                    Ptr[Index++] = HKHubArchJITOpcodeAddMR8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.relativeReg[1]), HKHubArchJITRegisterAL);
                    Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAH, HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
            }
            
            const HKHubArchJITRegister Dst = HKHubArchJITGetRegister(Instruction->state.operand[0].reg);
            
            Ptr[Index++] = HKHubArchJITRexB;
            HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterR8B, HKHubArchJITRegisterCL);
            HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAL, Dst);
            
            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterCL, 8);
            HKHubArchJITAddInstructionSubMR8(Ptr, &Index, HKHubArchJITRegisterCL, HKHubArchJITRegisterAH);
            HKHubArchJITAddInstructionJumpRel8(Ptr, &Index, HKHubArchJITJumpCarry, 2);
            HKHubArchJITAddInstructionBitAdjustMC8(Ptr, &Index, (Type == HKHubArchJITBitAdjustShl ? HKHubArchJITBitAdjustShr : HKHubArchJITBitAdjustShl), HKHubArchJITRegisterAL);
            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAL);
            Ptr[Index++] = HKHubArchJITRexR;
            HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterCL, HKHubArchJITRegisterR8B);
            Ptr[Index++] = HKHubArchJITRexB;
            HKHubArchJITAddInstructionSetnz(Ptr, &Index, HKHubArchJITRegisterR8B);
            
            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, Dst, Dst);
            HKHubArchJITAddInstructionBitAdjustMR8(Ptr, &Index, Type, Dst, HKHubArchJITRegisterAH);
        }
        
        if (FlagsAffected)
        {
            Ptr[Index++] = HKHubArchJITRexR;
            HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterR8B);
            HKHubArchJITCopyFlagsSCZPresetO(Ptr, &Index);
        }
        
        if (HKHubArchInstructionRegisterIsSpecialPurpose(Instruction->state.operand[0].reg) && (Instruction->state.operand[0].reg == HKHubArchInstructionRegisterPC) && ((HKHubArchInstructionGetMemoryOperation(&Instruction->state) >> HKHubArchInstructionMemoryOperationOp1) & HKHubArchInstructionMemoryOperationDst)) HKHubArchJITAddInstructionReturn(Ptr, &Index);
        else HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterCompatibilityPC, Size);
    }
    
    return Index;
}

static size_t HKHubArchJITGenerate2OperandDivisionMutator(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, size_t Cost, _Bool Signed, _Bool Mod, _Bool MemoryCheck)
{
    const size_t Size = HKHubArchInstructionSizeOfEncoding(&Instruction->state);
    
    size_t Index = 0;
    HKHubArchJITCheckCycles(Ptr, &Index, Cost + (Size * HKHubArchProcessorSpeedMemoryRead), Instruction);
    
    if (Instruction->state.operand[0].type == HKHubArchInstructionOperandR)
    {
        if (Instruction->state.operand[1].type == HKHubArchInstructionOperandR)
        {
            const HKHubArchJITRegister Dst = HKHubArchJITGetRegister(Instruction->state.operand[0].reg), Src = HKHubArchJITGetRegister(Instruction->state.operand[1].reg);
            HKHubArchJITRegister Result, Flags;
            
            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, Src, Src);
            HKHubArchJITAddInstructionJumpRel8(Ptr, &Index, HKHubArchJITJumpZero, Signed ? 54 : 14);
            
            if (Signed)
            {
                Result = HKHubArchJITRegisterAH;
                Flags = HKHubArchJITRegisterAL;
                
                HKHubArchJITAddInstructionMovsxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, Dst);
                Ptr[Index++] = HKHubArchJITRexB;
                HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterR8D, HKHubArchJITRegisterEDX);
                HKHubArchJITAddInstructionMovsxRM8(Ptr, &Index, HKHubArchJITRegisterEDX, Src);
                Ptr[Index++] = HKHubArchJITRexB;
                HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterR9D, HKHubArchJITRegisterEDX); // TODO: if Src is low can set r9 directly
                Ptr[Index++] = HKHubArchJITOpcodeCdq;
                Ptr[Index++] = HKHubArchJITRexB;
                Ptr[Index++] = HKHubArchJITOpcodeOneOpArithmeticM;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpArithmeticIdiv, HKHubArchJITRegisterR9D);
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAH, Mod ? HKHubArchJITRegisterDL : HKHubArchJITRegisterAL);
                Ptr[Index++] = HKHubArchJITRexR;
                HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterEDX, HKHubArchJITRegisterR8D);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, 0x80);
                HKHubArchJITAddInstructionAndMR8(Ptr, &Index, Flags, Dst);
                HKHubArchJITAddInstructionAndMR8(Ptr, &Index, Flags, Src);
                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShr, HKHubArchJITRegisterAL, 4);
                Ptr[Index++] = HKHubArchJITRexB;
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterR9B, HKHubArchJITRegisterAL);
            }
            
            else
            {
                if (Mod)
                {
                    Result = HKHubArchJITRegisterAH;
                    Flags = HKHubArchJITRegisterAL;
                }
                
                else
                {
                    Result = HKHubArchJITRegisterAL;
                    Flags = HKHubArchJITRegisterAH;
                }
                
                HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, Dst);
                Ptr[Index++] = HKHubArchJITOpcodeOneOpArithmeticM8;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpArithmeticDiv, Src);
            }
            
            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, Result, Result);
            HKHubArchJITAddInstructionSetz(Ptr, &Index, Flags);
            HKHubArchJITAddInstructionMovMR8(Ptr, &Index, Dst, Result);
            
            if (Signed)
            {
                HKHubArchJITAddInstructionSets(Ptr, &Index, HKHubArchJITRegisterAH);
                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAH, 2);
                HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAH);
                Ptr[Index++] = HKHubArchJITRexR;
                HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterR9B);
            }
            
            HKHubArchJITAddInstructionJumpRel8(Ptr, &Index, HKHubArchJITJumpUnconditional, 4);
            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, Flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero);
            HKHubArchJITAddInstructionXorMR8(Ptr, &Index, Dst, Dst);
            
            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterCompatibilityFlags, 0xf0);
            HKHubArchJITAddInstructionOrMR8(Ptr, &Index, HKHubArchJITRegisterCompatibilityFlags, Flags);
        }
        
        else if (Instruction->state.operand[1].type == HKHubArchInstructionOperandI)
        {
            const HKHubArchJITRegister Dst = HKHubArchJITGetRegister(Instruction->state.operand[0].reg);
            
            if (Signed)
            {
                if (Mod)
                {
                    switch (Instruction->state.operand[1].value)
                    {
                        case 0:
                            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero);
                            HKHubArchJITAddInstructionXorMR8(Ptr, &Index, Dst, Dst);
                            break;
                            
                        case 1:
                            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsZero);
                            HKHubArchJITAddInstructionXorMR8(Ptr, &Index, Dst, Dst);
                            break;
                            
                        case 255:
                            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticCmp, Dst, 0x80);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAL, 3);
                            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticOr, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsZero);
                            HKHubArchJITAddInstructionXorMR8(Ptr, &Index, Dst, Dst);
                            break;
                            
                        default:
                            Ptr[Index++] = HKHubArchJITRexB;
                            HKHubArchJITAddInstructionMovOI(Ptr, &Index, HKHubArchJITRegisterR8D, (int8_t)Instruction->state.operand[1].value);
                            HKHubArchJITAddInstructionMovsxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, Dst);
                            Ptr[Index++] = HKHubArchJITRexB;
                            HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterR9D, HKHubArchJITRegisterEDX);
                            
                            Ptr[Index++] = HKHubArchJITOpcodeCdq;
                            Ptr[Index++] = HKHubArchJITRexB;
                            Ptr[Index++] = HKHubArchJITOpcodeOneOpArithmeticM;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpArithmeticIdiv, HKHubArchJITRegisterR8D);
                            
                            HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAH, HKHubArchJITRegisterDL);
                            Ptr[Index++] = HKHubArchJITRexR;
                            HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterEDX, HKHubArchJITRegisterR9D);
                            
                            if (Instruction->state.operand[1].value & 0x80)
                            {
                                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, 0x80);
                                HKHubArchJITAddInstructionAndMR8(Ptr, &Index, HKHubArchJITRegisterAL, Dst);
                                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShr, HKHubArchJITRegisterAL, 4);
                                Ptr[Index++] = HKHubArchJITRexB;
                                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterR9B, HKHubArchJITRegisterAL);
                            }
                            
                            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, HKHubArchJITRegisterAH, HKHubArchJITRegisterAH);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            HKHubArchJITAddInstructionMovMR8(Ptr, &Index, Dst, HKHubArchJITRegisterAH);
                            HKHubArchJITAddInstructionSets(Ptr, &Index, HKHubArchJITRegisterAH);
                            HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAH, 2);
                            HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAH);
                            
                            if (Instruction->state.operand[1].value & 0x80)
                            {
                                Ptr[Index++] = HKHubArchJITRexR;
                                HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterR9B);
                            }
                            break;
                    }
                }
                
                else
                {
                    switch (Instruction->state.operand[1].value)
                    {
                        case 0:
                            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero);
                            HKHubArchJITAddInstructionXorMR8(Ptr, &Index, Dst, Dst);
                            break;
                            
                        case 1:
                            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticCmp, Dst, 0);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            HKHubArchJITAddInstructionSets(Ptr, &Index, HKHubArchJITRegisterAH);
                            HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAH, 2);
                            HKHubArchJITAddInstructionOrMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAH);
                            break;
                            
                        case 255:
                            HKHubArchJITAddInstructionArithmeticM8(Ptr, &Index, HKHubArchJITOneOpArithmeticNeg, Dst);
                            HKHubArchJITAddInstructionSeto(Ptr, &Index, HKHubArchJITRegisterAL);
                            Ptr[Index++] = HKHubArchJITOpcodeLahf;
                            Ptr[Index++] = HKHubArchJIT16Bit;
                            HKHubArchJITAddInstructionBitAdjustMI(Ptr, &Index, HKHubArchJITBitAdjustRol, HKHubArchJITRegisterAX, 1);
                            HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAL, 1);
                            Ptr[Index++] = HKHubArchJIT16Bit;
                            HKHubArchJITAddInstructionBitAdjustMI(Ptr, &Index, HKHubArchJITBitAdjustRol, HKHubArchJITRegisterAX, 1);
                            break;
                            
                        default:
                            Ptr[Index++] = HKHubArchJITRexB;
                            HKHubArchJITAddInstructionMovOI(Ptr, &Index, HKHubArchJITRegisterR8D, (int8_t)Instruction->state.operand[1].value);
                            HKHubArchJITAddInstructionMovsxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, Dst);
                            Ptr[Index++] = HKHubArchJITRexB;
                            HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterR9D, HKHubArchJITRegisterEDX);
                            
                            Ptr[Index++] = HKHubArchJITOpcodeCdq;
                            Ptr[Index++] = HKHubArchJITRexB;
                            Ptr[Index++] = HKHubArchJITOpcodeOneOpArithmeticM;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpArithmeticIdiv, HKHubArchJITRegisterR8D);
                            
                            HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAH, HKHubArchJITRegisterAL);
                            Ptr[Index++] = HKHubArchJITRexR;
                            HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterEDX, HKHubArchJITRegisterR9D);
                            
                            if (Instruction->state.operand[1].value & 0x80)
                            {
                                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, 0x80);
                                HKHubArchJITAddInstructionAndMR8(Ptr, &Index, HKHubArchJITRegisterAL, Dst);
                                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShr, HKHubArchJITRegisterAL, 4);
                                Ptr[Index++] = HKHubArchJITRexB;
                                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterR9B, HKHubArchJITRegisterAL);
                            }
                            
                            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, HKHubArchJITRegisterAH, HKHubArchJITRegisterAH);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            HKHubArchJITAddInstructionMovMR8(Ptr, &Index, Dst, HKHubArchJITRegisterAH);
                            HKHubArchJITAddInstructionSets(Ptr, &Index, HKHubArchJITRegisterAH);
                            HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAH, 2);
                            HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAH);
                            
                            if (Instruction->state.operand[1].value & 0x80)
                            {
                                Ptr[Index++] = HKHubArchJITRexR;
                                HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterR9B);
                            }
                            break;
                    }
                }
            }
            
            else
            {
                if (Mod)
                {
                    switch (Instruction->state.operand[1].value)
                    {
                        case 0:
                            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero);
                            HKHubArchJITAddInstructionXorMR8(Ptr, &Index, Dst, Dst);
                            break;
                            
                        case 1:
                            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsZero);
                            HKHubArchJITAddInstructionXorMR8(Ptr, &Index, Dst, Dst);
                            break;
                            
                        case 2:
                            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, Dst, 1);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 4:
                            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, Dst, 3);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 8:
                            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, Dst, 7);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 16:
                            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, Dst, 15);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 32:
                            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, Dst, 31);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 64:
                            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, Dst, 63);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 128:
                            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, Dst, 127);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 129 ... 255:
                            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticCmp, Dst, -(256 - Instruction->state.operand[1].value));
                            HKHubArchJITAddInstructionJumpRel8(Ptr, &Index, HKHubArchJITJumpBelow, 3);
                            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, Dst, 256 - Instruction->state.operand[1].value);
                            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, Dst, Dst);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        default:
                            Ptr[Index++] = HKHubArchJITRexB;
                            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterR8B, Instruction->state.operand[1].value);
                            HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, Dst);
                            Ptr[Index++] = HKHubArchJITRexB;
                            Ptr[Index++] = HKHubArchJITOpcodeOneOpArithmeticM8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpArithmeticDiv, HKHubArchJITRegisterR8B);
                            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, HKHubArchJITRegisterAH, HKHubArchJITRegisterAH);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            HKHubArchJITAddInstructionMovMR8(Ptr, &Index, Dst, HKHubArchJITRegisterAH);
                            break;
                    }
                }
                
                else
                {
                    switch (Instruction->state.operand[1].value)
                    {
                        case 0:
                            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero);
                            HKHubArchJITAddInstructionXorMR8(Ptr, &Index, Dst, Dst);
                            break;
                            
                        case 1:
                            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticCmp, Dst, 0);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 2:
                            HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShr, Dst, 1);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 4:
                            HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShr, Dst, 2);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 8:
                            HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShr, Dst, 3);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 16:
                            HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShr, Dst, 4);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 32:
                            HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShr, Dst, 5);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 64:
                            HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShr, Dst, 6);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 128:
                            HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShr, Dst, 7);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 129 ... 255:
                            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticCmp, Dst, -(256 - Instruction->state.operand[1].value) - 1);
                            HKHubArchJITAddInstructionSeta(Ptr, &Index, Dst);
                            HKHubArchJITAddInstructionSetna(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        default:
                            Ptr[Index++] = HKHubArchJITRexB;
                            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterR8B, Instruction->state.operand[1].value);
                            HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, Dst);
                            Ptr[Index++] = HKHubArchJITRexB;
                            Ptr[Index++] = HKHubArchJITOpcodeOneOpArithmeticM8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpArithmeticDiv, HKHubArchJITRegisterR8B);
                            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAL);
                            HKHubArchJITAddInstructionMovMR8(Ptr, &Index, Dst, HKHubArchJITRegisterAL);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                    }
                }
            }
            
            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterCompatibilityFlags, 0xf0);
            HKHubArchJITAddInstructionOrMR8(Ptr, &Index, HKHubArchJITRegisterCompatibilityFlags, HKHubArchJITRegisterAL);
        }
        
        else if (Instruction->state.operand[1].type == HKHubArchInstructionOperandM)
        {
            switch (Instruction->state.operand[1].memory.type)
            {
                case HKHubArchInstructionMemoryOffset:
                    Ptr[Index++] = HKHubArchJITRexR;
                    
                    if (Signed)
                    {
                        Ptr[Index++] = 0x0f;
                        Ptr[Index++] = HKHubArchJIT0fPrefixOpcodeMovsxRM8;
                    }
                    
                    else Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                    
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddressDisp32, HKHubArchJITRegisterR8B, HKHubArchJITRegisterCompatibilityMemory);
                    *(uint32_t*)&Ptr[Index] = Instruction->state.operand[1].memory.offset;
                    Index += 4;
                    break;
                    
                case HKHubArchInstructionMemoryRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.reg));
                    Ptr[Index++] = HKHubArchJITRexR;
                    
                    if (Signed)
                    {
                        Ptr[Index++] = 0x0f;
                        Ptr[Index++] = HKHubArchJIT0fPrefixOpcodeMovsxRM8;
                    }
                    
                    else Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                    
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterR8B, HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
                    
                case HKHubArchInstructionMemoryRelativeOffset:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.relativeOffset.reg));
                    HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterAL, Instruction->state.operand[1].memory.relativeOffset.offset);
                    Ptr[Index++] = HKHubArchJITRexR;
                    
                    if (Signed)
                    {
                        Ptr[Index++] = 0x0f;
                        Ptr[Index++] = HKHubArchJIT0fPrefixOpcodeMovsxRM8;
                    }
                    
                    else Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                    
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterR8B, HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
                    
                case HKHubArchInstructionMemoryRelativeRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.relativeReg[0]));
                    Ptr[Index++] = HKHubArchJITOpcodeAddMR8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.relativeReg[1]), HKHubArchJITRegisterAL);
                    Ptr[Index++] = HKHubArchJITRexR;
                    
                    if (Signed)
                    {
                        Ptr[Index++] = 0x0f;
                        Ptr[Index++] = HKHubArchJIT0fPrefixOpcodeMovsxRM8;
                    }
                    
                    else Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                    
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterR8B, HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
            }
            
            const HKHubArchJITRegister Dst = HKHubArchJITGetRegister(Instruction->state.operand[0].reg), Src = HKHubArchJITRegisterR8B;
            HKHubArchJITRegister Result, Flags;
            
            Ptr[Index++] = HKHubArchJITRexRB;
            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, Src, Src);
            HKHubArchJITAddInstructionJumpRel8(Ptr, &Index, HKHubArchJITJumpZero, Signed ? 47 : 15);
            
            if (Signed)
            {
                Result = HKHubArchJITRegisterAH;
                Flags = HKHubArchJITRegisterAL;
                
                HKHubArchJITAddInstructionMovsxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, Dst);
                Ptr[Index++] = HKHubArchJITRexB;
                HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterR9D, HKHubArchJITRegisterEDX);
                Ptr[Index++] = HKHubArchJITOpcodeCdq;
                Ptr[Index++] = HKHubArchJITRexB;
                Ptr[Index++] = HKHubArchJITOpcodeOneOpArithmeticM;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpArithmeticIdiv, Src);
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAH, Mod ? HKHubArchJITRegisterDL : HKHubArchJITRegisterAL);
                Ptr[Index++] = HKHubArchJITRexR;
                HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterEDX, HKHubArchJITRegisterR9D);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, 0x80);
                HKHubArchJITAddInstructionAndMR8(Ptr, &Index, HKHubArchJITRegisterAL, Dst);
                Ptr[Index++] = HKHubArchJITRexB;
                HKHubArchJITAddInstructionAndMR8(Ptr, &Index, Src, HKHubArchJITRegisterAL);
                Ptr[Index++] = HKHubArchJITRexB;
                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShr, Src, 4);
            }
            
            else
            {
                if (Mod)
                {
                    Result = HKHubArchJITRegisterAH;
                    Flags = HKHubArchJITRegisterAL;
                }
                
                else
                {
                    Result = HKHubArchJITRegisterAL;
                    Flags = HKHubArchJITRegisterAH;
                }
                
                HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, Dst);
                Ptr[Index++] = HKHubArchJITRexB;
                Ptr[Index++] = HKHubArchJITOpcodeOneOpArithmeticM8;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpArithmeticDiv, Src);
            }
            
            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, Result, Result);
            HKHubArchJITAddInstructionSetz(Ptr, &Index, Flags);
            HKHubArchJITAddInstructionMovMR8(Ptr, &Index, Dst, Result);
            
            if (Signed)
            {
                HKHubArchJITAddInstructionSets(Ptr, &Index, HKHubArchJITRegisterAH);
                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAH, 2);
                HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAH);
                Ptr[Index++] = HKHubArchJITRexR;
                HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterR8B);
            }
            
            HKHubArchJITAddInstructionJumpRel8(Ptr, &Index, HKHubArchJITJumpUnconditional, 4);
            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, Flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero);
            HKHubArchJITAddInstructionXorMR8(Ptr, &Index, Dst, Dst);
            
            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterCompatibilityFlags, 0xf0);
            HKHubArchJITAddInstructionOrMR8(Ptr, &Index, HKHubArchJITRegisterCompatibilityFlags, Flags);
        }
        
        if (HKHubArchInstructionRegisterIsSpecialPurpose(Instruction->state.operand[0].reg) && (Instruction->state.operand[0].reg == HKHubArchInstructionRegisterPC) && ((HKHubArchInstructionGetMemoryOperation(&Instruction->state) >> HKHubArchInstructionMemoryOperationOp1) & HKHubArchInstructionMemoryOperationDst)) HKHubArchJITAddInstructionReturn(Ptr, &Index);
        else HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterCompatibilityPC, Size);
    }
    
    else if (Instruction->state.operand[0].type == HKHubArchInstructionOperandM)
    {
        if (Instruction->state.operand[1].type == HKHubArchInstructionOperandR)
        {
            switch (Instruction->state.operand[0].memory.type)
            {
                case HKHubArchInstructionMemoryOffset:
                    HKHubArchJITAddInstructionMovOI(Ptr, &Index, HKHubArchJITRegisterEBP, Instruction->state.operand[0].memory.offset);
                    break;
                    
                case HKHubArchInstructionMemoryRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEBP, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.reg));
                    break;
                    
                case HKHubArchInstructionMemoryRelativeOffset:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEBP, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeOffset.reg));
                    Ptr[Index++] = HKHubArchJITRex;
                    HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterEBP, Instruction->state.operand[0].memory.relativeOffset.offset);
                    break;
                    
                case HKHubArchInstructionMemoryRelativeRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeReg[0]));
                    Ptr[Index++] = HKHubArchJITOpcodeAddMR8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeReg[1]), HKHubArchJITRegisterAL);
                    HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterEBP, HKHubArchJITRegisterEAX);
                    break;
            }
            
            if (MemoryCheck)
            {
                HKHubArchJITAddInstructionPushR(Ptr, &Index, HKHubArchJITRegisterRBP);
                HKHubArchJITCheckMemoryAccess(Ptr, &Index, Instruction, HKHubArchJITRegisterRBP);
                HKHubArchJITAddInstructionPopR(Ptr, &Index, HKHubArchJITRegisterRBP);
            }
            
            const HKHubArchJITRegister Src = HKHubArchJITGetRegister(Instruction->state.operand[1].reg);
            HKHubArchJITRegister Result, Flags;
            
            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, Src, Src);
            HKHubArchJITAddInstructionJumpRel8(Ptr, &Index, HKHubArchJITJumpZero, Signed ? 57 : 16);
            
            if (Signed)
            {
                Result = HKHubArchJITRegisterAH;
                Flags = HKHubArchJITRegisterAL;
                
                Ptr[Index++] = 0x0f;
                Ptr[Index++] = HKHubArchJIT0fPrefixOpcodeMovsxRM8;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterEAX, HKHubArchJITRMSIB);
                Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                Ptr[Index++] = HKHubArchJITRexB;
                HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterR8D, HKHubArchJITRegisterEDX);
                HKHubArchJITAddInstructionMovsxRM8(Ptr, &Index, HKHubArchJITRegisterEDX, Src);
                Ptr[Index++] = HKHubArchJITRexB;
                HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterR9D, HKHubArchJITRegisterEDX); // TODO: if Src is low can set r9 directly
                Ptr[Index++] = HKHubArchJITOpcodeCdq;
                Ptr[Index++] = HKHubArchJITRexB;
                Ptr[Index++] = HKHubArchJITOpcodeOneOpArithmeticM;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpArithmeticIdiv, HKHubArchJITRegisterR9D);
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAH, Mod ? HKHubArchJITRegisterDL : HKHubArchJITRegisterAL);
                Ptr[Index++] = HKHubArchJITRexR;
                HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterEDX, HKHubArchJITRegisterR8D);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, 0x80);
                Ptr[Index++] = HKHubArchJITOpcodeAndRM8;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAL, HKHubArchJITRMSIB);
                Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                HKHubArchJITAddInstructionAndMR8(Ptr, &Index, HKHubArchJITRegisterAL, Src);
                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShr, HKHubArchJITRegisterAL, 4);
                Ptr[Index++] = HKHubArchJITRexB;
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterR9B, HKHubArchJITRegisterAL);
            }
            
            else
            {
                if (Mod)
                {
                    Result = HKHubArchJITRegisterAH;
                    Flags = HKHubArchJITRegisterAL;
                }
                
                else
                {
                    Result = HKHubArchJITRegisterAL;
                    Flags = HKHubArchJITRegisterAH;
                }
                
                Ptr[Index++] = 0x0f;
                Ptr[Index++] = HKHubArchJIT0fPrefixOpcodeMovzxRM8;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterEAX, HKHubArchJITRMSIB);
                Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                Ptr[Index++] = HKHubArchJITOpcodeOneOpArithmeticM8;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpArithmeticDiv, Src);
            }
            
            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, Result, Result);
            HKHubArchJITAddInstructionSetz(Ptr, &Index, Flags);
            Ptr[Index++] = HKHubArchJITOpcodeMovMR8;
            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, Result, HKHubArchJITRMSIB);
            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
            
            if (Signed)
            {
                HKHubArchJITAddInstructionSets(Ptr, &Index, HKHubArchJITRegisterAH);
                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAH, 2);
                HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAH);
                Ptr[Index++] = HKHubArchJITRexR;
                HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterR9B);
            }
            
            HKHubArchJITAddInstructionJumpRel8(Ptr, &Index, HKHubArchJITJumpUnconditional, 6);
            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, Flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero);
            Ptr[Index++] = HKHubArchJITOpcodeMoveMI8;
            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITMoveMov, HKHubArchJITRMSIB);
            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
            Ptr[Index++] = 0;
            
            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterCompatibilityFlags, 0xf0);
            HKHubArchJITAddInstructionOrMR8(Ptr, &Index, HKHubArchJITRegisterCompatibilityFlags, Flags);
        }
        
        else if (Instruction->state.operand[1].type == HKHubArchInstructionOperandI)
        {
            switch (Instruction->state.operand[0].memory.type)
            {
                case HKHubArchInstructionMemoryOffset:
                    HKHubArchJITAddInstructionMovOI(Ptr, &Index, HKHubArchJITRegisterEBP, Instruction->state.operand[0].memory.offset);
                    break;
                    
                case HKHubArchInstructionMemoryRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEBP, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.reg));
                    break;
                    
                case HKHubArchInstructionMemoryRelativeOffset:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEBP, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeOffset.reg));
                    Ptr[Index++] = HKHubArchJITRex;
                    HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterEBP, Instruction->state.operand[0].memory.relativeOffset.offset);
                    break;
                    
                case HKHubArchInstructionMemoryRelativeRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeReg[0]));
                    Ptr[Index++] = HKHubArchJITOpcodeAddMR8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeReg[1]), HKHubArchJITRegisterAL);
                    HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterEBP, HKHubArchJITRegisterEAX);
                    break;
            }
            
            if (MemoryCheck)
            {
                HKHubArchJITAddInstructionPushR(Ptr, &Index, HKHubArchJITRegisterRBP);
                HKHubArchJITCheckMemoryAccess(Ptr, &Index, Instruction, HKHubArchJITRegisterRBP);
                HKHubArchJITAddInstructionPopR(Ptr, &Index, HKHubArchJITRegisterRBP);
            }
            
            if (Signed)
            {
                if (Mod)
                {
                    switch (Instruction->state.operand[1].value)
                    {
                        case 0:
                            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero);
                            Ptr[Index++] = HKHubArchJITOpcodeMoveMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITMoveMov, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 0;
                            break;
                            
                        case 1:
                            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsZero);
                            Ptr[Index++] = HKHubArchJITOpcodeMoveMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITMoveMov, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 0;
                            break;
                            
                        case 255:
                            Ptr[Index++] = HKHubArchJITOpcodeArithmeticMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITArithmeticCmp, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 0x80;
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAL, 3);
                            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticOr, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsZero);
                            Ptr[Index++] = HKHubArchJITOpcodeMoveMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITMoveMov, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 0;
                            break;
                            
                        default:
                            Ptr[Index++] = HKHubArchJITRexB;
                            HKHubArchJITAddInstructionMovOI(Ptr, &Index, HKHubArchJITRegisterR8D, (int8_t)Instruction->state.operand[1].value);
                            Ptr[Index++] = 0x0f;
                            Ptr[Index++] = HKHubArchJIT0fPrefixOpcodeMovsxRM8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterEAX, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = HKHubArchJITRexB;
                            HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterR9D, HKHubArchJITRegisterEDX);
                            
                            Ptr[Index++] = HKHubArchJITOpcodeCdq;
                            Ptr[Index++] = HKHubArchJITRexB;
                            Ptr[Index++] = HKHubArchJITOpcodeOneOpArithmeticM;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpArithmeticIdiv, HKHubArchJITRegisterR8D);
                            
                            HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAH, HKHubArchJITRegisterDL);
                            Ptr[Index++] = HKHubArchJITRexR;
                            HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterEDX, HKHubArchJITRegisterR9D);
                            
                            if (Instruction->state.operand[1].value & 0x80)
                            {
                                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, 0x80);
                                Ptr[Index++] = HKHubArchJITOpcodeAndRM8;
                                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAL, HKHubArchJITRMSIB);
                                Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShr, HKHubArchJITRegisterAL, 4);
                                Ptr[Index++] = HKHubArchJITRexB;
                                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterR9B, HKHubArchJITRegisterAL);
                            }
                            
                            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, HKHubArchJITRegisterAH, HKHubArchJITRegisterAH);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            
                            Ptr[Index++] = HKHubArchJITOpcodeMovMR8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAH, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            HKHubArchJITAddInstructionSets(Ptr, &Index, HKHubArchJITRegisterAH);
                            HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAH, 2);
                            HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAH);
                            
                            if (Instruction->state.operand[1].value & 0x80)
                            {
                                Ptr[Index++] = HKHubArchJITRexR;
                                HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterR9B);
                            }
                            break;
                    }
                }
                
                else
                {
                    switch (Instruction->state.operand[1].value)
                    {
                        case 0:
                            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero);
                            Ptr[Index++] = HKHubArchJITOpcodeMoveMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITMoveMov, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 0;
                            break;
                            
                        case 1:
                            Ptr[Index++] = HKHubArchJITOpcodeArithmeticMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITArithmeticCmp, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 0;
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            HKHubArchJITAddInstructionSets(Ptr, &Index, HKHubArchJITRegisterAH);
                            HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAH, 2);
                            HKHubArchJITAddInstructionOrMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAH);
                            break;
                            
                        case 255:
                            Ptr[Index++] = HKHubArchJITOpcodeOneOpArithmeticM8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITOneOpArithmeticNeg, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            HKHubArchJITAddInstructionSeto(Ptr, &Index, HKHubArchJITRegisterAL);
                            Ptr[Index++] = HKHubArchJITOpcodeLahf;
                            Ptr[Index++] = HKHubArchJIT16Bit;
                            HKHubArchJITAddInstructionBitAdjustMI(Ptr, &Index, HKHubArchJITBitAdjustRol, HKHubArchJITRegisterAX, 1);
                            HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAL, 1);
                            Ptr[Index++] = HKHubArchJIT16Bit;
                            HKHubArchJITAddInstructionBitAdjustMI(Ptr, &Index, HKHubArchJITBitAdjustRol, HKHubArchJITRegisterAX, 1);
                            break;
                            
                        default:
                            Ptr[Index++] = HKHubArchJITRexB;
                            HKHubArchJITAddInstructionMovOI(Ptr, &Index, HKHubArchJITRegisterR8D, (int8_t)Instruction->state.operand[1].value);
                            Ptr[Index++] = 0x0f;
                            Ptr[Index++] = HKHubArchJIT0fPrefixOpcodeMovsxRM8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterEAX, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = HKHubArchJITRexB;
                            HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterR9D, HKHubArchJITRegisterEDX);
                            
                            Ptr[Index++] = HKHubArchJITOpcodeCdq;
                            Ptr[Index++] = HKHubArchJITRexB;
                            Ptr[Index++] = HKHubArchJITOpcodeOneOpArithmeticM;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpArithmeticIdiv, HKHubArchJITRegisterR8D);
                            
                            HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAH, HKHubArchJITRegisterAL);
                            Ptr[Index++] = HKHubArchJITRexR;
                            HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterEDX, HKHubArchJITRegisterR9D);
                            
                            if (Instruction->state.operand[1].value & 0x80)
                            {
                                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, 0x80);
                                Ptr[Index++] = HKHubArchJITOpcodeAndRM8;
                                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAL, HKHubArchJITRMSIB);
                                Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShr, HKHubArchJITRegisterAL, 4);
                                Ptr[Index++] = HKHubArchJITRexB;
                                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterR9B, HKHubArchJITRegisterAL);
                            }
                            
                            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, HKHubArchJITRegisterAH, HKHubArchJITRegisterAH);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            
                            Ptr[Index++] = HKHubArchJITOpcodeMovMR8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAH, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            HKHubArchJITAddInstructionSets(Ptr, &Index, HKHubArchJITRegisterAH);
                            HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAH, 2);
                            HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAH);
                            
                            if (Instruction->state.operand[1].value & 0x80)
                            {
                                Ptr[Index++] = HKHubArchJITRexR;
                                HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterR9B);
                            }
                            break;
                    }
                }
            }
            
            else
            {
                if (Mod)
                {
                    switch (Instruction->state.operand[1].value)
                    {
                        case 0:
                            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero);
                            Ptr[Index++] = HKHubArchJITOpcodeMoveMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITMoveMov, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 0;
                            break;
                            
                        case 1:
                            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsZero);
                            Ptr[Index++] = HKHubArchJITOpcodeMoveMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITMoveMov, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 0;
                            break;
                            
                        case 2:
                            Ptr[Index++] = HKHubArchJITOpcodeArithmeticMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITArithmeticAnd, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 1;
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 4:
                            Ptr[Index++] = HKHubArchJITOpcodeArithmeticMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITArithmeticAnd, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 3;
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 8:
                            Ptr[Index++] = HKHubArchJITOpcodeArithmeticMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITArithmeticAnd, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 7;
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 16:
                            Ptr[Index++] = HKHubArchJITOpcodeArithmeticMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITArithmeticAnd, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 15;
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 32:
                            Ptr[Index++] = HKHubArchJITOpcodeArithmeticMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITArithmeticAnd, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 31;
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 64:
                            Ptr[Index++] = HKHubArchJITOpcodeArithmeticMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITArithmeticAnd, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 63;
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 128:
                            Ptr[Index++] = HKHubArchJITOpcodeArithmeticMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITArithmeticAnd, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 127;
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 129 ... 255:
                            Ptr[Index++] = HKHubArchJITOpcodeArithmeticMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITArithmeticCmp, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = -(256 - Instruction->state.operand[1].value);
                            HKHubArchJITAddInstructionJumpRel8(Ptr, &Index, HKHubArchJITJumpBelow, 4);
                            Ptr[Index++] = HKHubArchJITOpcodeArithmeticMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITArithmeticAdd, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 256 - Instruction->state.operand[1].value;
                            Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAL, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAL);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        default:
                            Ptr[Index++] = HKHubArchJITRexB;
                            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterR8B, Instruction->state.operand[1].value);
                            Ptr[Index++] = 0x0f;
                            Ptr[Index++] = HKHubArchJIT0fPrefixOpcodeMovzxRM8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterEAX, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = HKHubArchJITRexB;
                            Ptr[Index++] = HKHubArchJITOpcodeOneOpArithmeticM8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpArithmeticDiv, HKHubArchJITRegisterR8B);
                            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, HKHubArchJITRegisterAH, HKHubArchJITRegisterAH);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            Ptr[Index++] = HKHubArchJITOpcodeMovMR8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAH, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            break;
                    }
                }
                
                else
                {
                    switch (Instruction->state.operand[1].value)
                    {
                        case 0:
                            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero);
                            Ptr[Index++] = HKHubArchJITOpcodeMoveMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITMoveMov, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 0;
                            break;
                            
                        case 1:
                            Ptr[Index++] = HKHubArchJITOpcodeArithmeticMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITArithmeticCmp, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 0;
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 2:
                            Ptr[Index++] = HKHubArchJITOpcodeBitAdjust1MI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITBitAdjustShr, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 4:
                            Ptr[Index++] = HKHubArchJITOpcodeBitAdjustMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITBitAdjustShr, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 2;
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 8:
                            Ptr[Index++] = HKHubArchJITOpcodeBitAdjustMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITBitAdjustShr, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 3;
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 16:
                            Ptr[Index++] = HKHubArchJITOpcodeBitAdjustMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITBitAdjustShr, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 4;
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 32:
                            Ptr[Index++] = HKHubArchJITOpcodeBitAdjustMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITBitAdjustShr, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 5;
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 64:
                            Ptr[Index++] = HKHubArchJITOpcodeBitAdjustMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITBitAdjustShr, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 6;
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 128:
                            Ptr[Index++] = HKHubArchJITOpcodeBitAdjustMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITBitAdjustShr, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = 7;
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        case 129 ... 255:
                            Ptr[Index++] = HKHubArchJITOpcodeArithmeticMI8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITArithmeticCmp, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = -(256 - Instruction->state.operand[1].value) - 1;
                            Ptr[Index++] = 0x0f;
                            Ptr[Index++] = HKHubArchJIT0fPrefixOpcodeSeta;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, 0, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            HKHubArchJITAddInstructionSetna(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                            
                        default:
                            Ptr[Index++] = HKHubArchJITRexB;
                            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, HKHubArchJITRegisterR8B, Instruction->state.operand[1].value);
                            Ptr[Index++] = 0x0f;
                            Ptr[Index++] = HKHubArchJIT0fPrefixOpcodeMovzxRM8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterEAX, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            Ptr[Index++] = HKHubArchJITRexB;
                            Ptr[Index++] = HKHubArchJITOpcodeOneOpArithmeticM8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpArithmeticDiv, HKHubArchJITRegisterR8B);
                            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAL);
                            Ptr[Index++] = HKHubArchJITOpcodeMovMR8;
                            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAL, HKHubArchJITRMSIB);
                            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                            HKHubArchJITAddInstructionSetz(Ptr, &Index, HKHubArchJITRegisterAL);
                            break;
                    }
                }
            }
            
            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterCompatibilityFlags, 0xf0);
            HKHubArchJITAddInstructionOrMR8(Ptr, &Index, HKHubArchJITRegisterCompatibilityFlags, HKHubArchJITRegisterAL);
        }
        
        else if (Instruction->state.operand[1].type == HKHubArchInstructionOperandM)
        {
            switch (Instruction->state.operand[0].memory.type)
            {
                case HKHubArchInstructionMemoryOffset:
                    HKHubArchJITAddInstructionMovOI(Ptr, &Index, HKHubArchJITRegisterEBP, Instruction->state.operand[0].memory.offset);
                    break;
                    
                case HKHubArchInstructionMemoryRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEBP, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.reg));
                    break;
                    
                case HKHubArchInstructionMemoryRelativeOffset:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEBP, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeOffset.reg));
                    Ptr[Index++] = HKHubArchJITRex;
                    HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterEBP, Instruction->state.operand[0].memory.relativeOffset.offset);
                    break;
                    
                case HKHubArchInstructionMemoryRelativeRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeReg[0]));
                    Ptr[Index++] = HKHubArchJITOpcodeAddMR8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITGetRegister(Instruction->state.operand[0].memory.relativeReg[1]), HKHubArchJITRegisterAL);
                    HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterEBP, HKHubArchJITRegisterEAX);
                    break;
            }
            
            if (MemoryCheck)
            {
                HKHubArchJITAddInstructionPushR(Ptr, &Index, HKHubArchJITRegisterRBP);
                HKHubArchJITCheckMemoryAccess(Ptr, &Index, Instruction, HKHubArchJITRegisterRBP);
                HKHubArchJITAddInstructionPopR(Ptr, &Index, HKHubArchJITRegisterRBP);
            }
            
            switch (Instruction->state.operand[1].memory.type)
            {
                case HKHubArchInstructionMemoryOffset:
                    Ptr[Index++] = HKHubArchJITRexR;
                    
                    if (Signed)
                    {
                        Ptr[Index++] = 0x0f;
                        Ptr[Index++] = HKHubArchJIT0fPrefixOpcodeMovsxRM8;
                    }
                    
                    else Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                    
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddressDisp32, HKHubArchJITRegisterR8B, HKHubArchJITRegisterCompatibilityMemory);
                    *(uint32_t*)&Ptr[Index] = Instruction->state.operand[1].memory.offset;
                    Index += 4;
                    break;
                    
                case HKHubArchInstructionMemoryRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.reg));
                    Ptr[Index++] = HKHubArchJITRexR;
                    
                    if (Signed)
                    {
                        Ptr[Index++] = 0x0f;
                        Ptr[Index++] = HKHubArchJIT0fPrefixOpcodeMovsxRM8;
                    }
                    
                    else Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                    
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterR8B, HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
                    
                case HKHubArchInstructionMemoryRelativeOffset:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.relativeOffset.reg));
                    HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterAL, Instruction->state.operand[1].memory.relativeOffset.offset);
                    Ptr[Index++] = HKHubArchJITRexR;
                    
                    if (Signed)
                    {
                        Ptr[Index++] = 0x0f;
                        Ptr[Index++] = HKHubArchJIT0fPrefixOpcodeMovsxRM8;
                    }
                    
                    else Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                    
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterR8B, HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
                    
                case HKHubArchInstructionMemoryRelativeRegister:
                    HKHubArchJITAddInstructionMovzxRM8(Ptr, &Index, HKHubArchJITRegisterEAX, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.relativeReg[0]));
                    Ptr[Index++] = HKHubArchJITOpcodeAddMR8;
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITGetRegister(Instruction->state.operand[1].memory.relativeReg[1]), HKHubArchJITRegisterAL);
                    Ptr[Index++] = HKHubArchJITRexR;
                    
                    if (Signed)
                    {
                        Ptr[Index++] = 0x0f;
                        Ptr[Index++] = HKHubArchJIT0fPrefixOpcodeMovsxRM8;
                    }
                    
                    else Ptr[Index++] = HKHubArchJITOpcodeMovRM8;
                    
                    Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterR8B, HKHubArchJITRMSIB);
                    Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRAX, HKHubArchJITRegisterCompatibilityMemory);
                    break;
            }
            
            const HKHubArchJITRegister Src = HKHubArchJITRegisterR8B;
            HKHubArchJITRegister Result, Flags;
            
            Ptr[Index++] = HKHubArchJITRexRB;
            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, Src, Src);
            HKHubArchJITAddInstructionJumpRel8(Ptr, &Index, HKHubArchJITJumpZero, Signed ? 50 : 17);
            
            if (Signed)
            {
                Result = HKHubArchJITRegisterAH;
                Flags = HKHubArchJITRegisterAL;
                
                Ptr[Index++] = 0x0f;
                Ptr[Index++] = HKHubArchJIT0fPrefixOpcodeMovsxRM8;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterEAX, HKHubArchJITRMSIB);
                Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                Ptr[Index++] = HKHubArchJITRexB;
                HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterR9D, HKHubArchJITRegisterEDX);
                Ptr[Index++] = HKHubArchJITOpcodeCdq;
                Ptr[Index++] = HKHubArchJITRexB;
                Ptr[Index++] = HKHubArchJITOpcodeOneOpArithmeticM;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpArithmeticIdiv, HKHubArchJITRegisterR8D);
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAH, Mod ? HKHubArchJITRegisterDL : HKHubArchJITRegisterAL);
                Ptr[Index++] = HKHubArchJITRexR;
                HKHubArchJITAddInstructionMovMR(Ptr, &Index, HKHubArchJITRegisterEDX, HKHubArchJITRegisterR9D);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, 0x80);
                Ptr[Index++] = HKHubArchJITOpcodeAndRM8;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterAL, HKHubArchJITRMSIB);
                Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                Ptr[Index++] = HKHubArchJITRexB;
                HKHubArchJITAddInstructionAndMR8(Ptr, &Index, HKHubArchJITRegisterR8B, HKHubArchJITRegisterAL);
                Ptr[Index++] = HKHubArchJITRexB;
                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShr, HKHubArchJITRegisterR8B, 4);
            }
            
            else
            {
                if (Mod)
                {
                    Result = HKHubArchJITRegisterAH;
                    Flags = HKHubArchJITRegisterAL;
                }
                
                else
                {
                    Result = HKHubArchJITRegisterAL;
                    Flags = HKHubArchJITRegisterAH;
                }
                
                Ptr[Index++] = 0x0f;
                Ptr[Index++] = HKHubArchJIT0fPrefixOpcodeMovzxRM8;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITRegisterEAX, HKHubArchJITRMSIB);
                Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
                Ptr[Index++] = HKHubArchJITRexB;
                Ptr[Index++] = HKHubArchJITOpcodeOneOpArithmeticM8;
                Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModRegister, HKHubArchJITOneOpArithmeticDiv, Src);
            }
            
            HKHubArchJITAddInstructionTestMR8(Ptr, &Index, Result, Result);
            HKHubArchJITAddInstructionSetz(Ptr, &Index, Flags);
            Ptr[Index++] = HKHubArchJITOpcodeMovMR8;
            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, Result, HKHubArchJITRMSIB);
            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
            
            if (Signed)
            {
                HKHubArchJITAddInstructionSets(Ptr, &Index, HKHubArchJITRegisterAH);
                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAH, 2);
                HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAH);
                Ptr[Index++] = HKHubArchJITRexR;
                HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterR8B);
            }
            
            HKHubArchJITAddInstructionJumpRel8(Ptr, &Index, HKHubArchJITJumpUnconditional, 6);
            HKHubArchJITAddInstructionMovOI8(Ptr, &Index, Flags, HKHubArchProcessorFlagsOverflow | HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero);
            Ptr[Index++] = HKHubArchJITOpcodeMoveMI8;
            Ptr[Index++] = HKHubArchJITModRM(HKHubArchJITModAddress, HKHubArchJITMoveMov, HKHubArchJITRMSIB);
            Ptr[Index++] = HKHubArchJITSIB(0, HKHubArchJITRegisterRBP, HKHubArchJITRegisterCompatibilityMemory);
            Ptr[Index++] = 0;
            
            HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterCompatibilityFlags, 0xf0);
            HKHubArchJITAddInstructionOrMR8(Ptr, &Index, HKHubArchJITRegisterCompatibilityFlags, Flags);
        }
        
        HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterCompatibilityPC, Size);
    }
    
    return Index;
}

static size_t HKHubArchJITGenerate1OperandJump(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, HKHubArchJITJump Type, size_t Cost, CCArray(HKHubArchJITJumpRef) Jumps)
{
    const size_t Size = HKHubArchInstructionSizeOfEncoding(&Instruction->state);
    
    size_t Index = 0;
    HKHubArchJITCheckCycles(Ptr, &Index, Cost + (Size * HKHubArchProcessorSpeedMemoryRead), Instruction);
    
    if (Type != HKHubArchJITJumpUnconditional)
    {
        switch (Type)
        {
            case HKHubArchJITJumpZero:
            case HKHubArchJITJumpNotZero:
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterCompatibilityFlags);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsZero);
                break;
                
            case HKHubArchJITJumpSign:
                Type = HKHubArchJITJumpZero;
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterCompatibilityFlags);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsSign);
                break;
                
            case HKHubArchJITJumpNotSign:
                Type = HKHubArchJITJumpNotZero;
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterCompatibilityFlags);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsSign);
                break;
                
            case HKHubArchJITJumpOverflow:
                Type = HKHubArchJITJumpZero;
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterCompatibilityFlags);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsOverflow);
                break;
                
            case HKHubArchJITJumpNotOverflow:
                Type = HKHubArchJITJumpNotZero;
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterCompatibilityFlags);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsOverflow);
                break;
                
            case HKHubArchJITJumpCarry:
                Type = HKHubArchJITJumpZero;
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterCompatibilityFlags);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsCarry);
                break;
                
            case HKHubArchJITJumpNotCarry:
                Type = HKHubArchJITJumpNotZero;
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterCompatibilityFlags);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsCarry);
                break;
                
            case HKHubArchJITJumpBelowEqual:
                Type = HKHubArchJITJumpZero;
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterCompatibilityFlags);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero);
                break;
                
            case HKHubArchJITJumpNotBelowEqual:
                Type = HKHubArchJITJumpNotZero;
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterCompatibilityFlags);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsCarry | HKHubArchProcessorFlagsZero);
                break;
                
            case HKHubArchJITJumpLess:
                Type = HKHubArchJITJumpZero;
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterCompatibilityFlags);
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAH, HKHubArchJITRegisterCompatibilityFlags);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsSign);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAH, HKHubArchProcessorFlagsOverflow);
                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAL, 1);
                HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAH);
                break;
                
            case HKHubArchJITJumpNotLess:
                Type = HKHubArchJITJumpNotZero;
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterCompatibilityFlags);
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAH, HKHubArchJITRegisterCompatibilityFlags);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsSign);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAH, HKHubArchProcessorFlagsOverflow);
                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAL, 1);
                HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAH);
                break;
                
            case HKHubArchJITJumpLessEqual:
                Type = HKHubArchJITJumpZero;
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterCompatibilityFlags);
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAH, HKHubArchJITRegisterCompatibilityFlags);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsZero);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAH, HKHubArchProcessorFlagsOverflow);
                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAL, 1);
                HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAH);
                break;
                
            case HKHubArchJITJumpNotLessEqual:
                Type = HKHubArchJITJumpNotZero;
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterCompatibilityFlags);
                HKHubArchJITAddInstructionMovMR8(Ptr, &Index, HKHubArchJITRegisterAH, HKHubArchJITRegisterCompatibilityFlags);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAL, HKHubArchProcessorFlagsSign | HKHubArchProcessorFlagsZero);
                HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAnd, HKHubArchJITRegisterAH, HKHubArchProcessorFlagsOverflow);
                HKHubArchJITAddInstructionBitAdjustMI8(Ptr, &Index, HKHubArchJITBitAdjustShl, HKHubArchJITRegisterAL, 1);
                HKHubArchJITAddInstructionXorMR8(Ptr, &Index, HKHubArchJITRegisterAL, HKHubArchJITRegisterAH);
                break;
                
            default:
                break;
        }
        
        HKHubArchJITAddInstructionJumpRel32(Ptr, &Index, Type, 8);
    }
    
    HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterCompatibilityPC, Instruction->state.operand[0].value);
    
    CCArrayAppendElement(Jumps, &(HKHubArchJITJumpRef){ .jump = Ptr + Index, .rel = (int32_t*)(Ptr + Index + 1), .pc = Instruction->offset + Instruction->state.operand[0].value });
    HKHubArchJITAddInstructionJumpRel32(Ptr, &Index, HKHubArchJITJumpUnconditional, 0);
    
    if (Type != HKHubArchJITJumpUnconditional) HKHubArchJITAddInstructionArithmeticMI8(Ptr, &Index, HKHubArchJITArithmeticAdd, HKHubArchJITRegisterCompatibilityPC, Size);
    
    return Index;
}

static size_t HKHubArchJITGenerateAdd(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, HKHubArchJITOptions Options)
{
    return HKHubArchJITGenerate2OperandMutator(Ptr, Instruction, HKHubArchJITArithmeticAdd, HKHubArchJITOpcodeAddMR8, HKHubArchJITOpcodeAddRM8, HKHubArchJITOpcodeArithmeticMI8, 2, TRUE, Options & HKHubArchJITOptionsWatchMemory);
}

static size_t HKHubArchJITGenerateSub(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, HKHubArchJITOptions Options)
{
    return HKHubArchJITGenerate2OperandMutator(Ptr, Instruction, HKHubArchJITArithmeticSub, HKHubArchJITOpcodeSubMR8, HKHubArchJITOpcodeSubRM8, HKHubArchJITOpcodeArithmeticMI8, 2, TRUE, Options & HKHubArchJITOptionsWatchMemory);
}

static size_t HKHubArchJITGenerateUdiv(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, HKHubArchJITOptions Options)
{
    return HKHubArchJITGenerate2OperandDivisionMutator(Ptr, Instruction, 3, FALSE, FALSE, Options & HKHubArchJITOptionsWatchMemory);
}

static size_t HKHubArchJITGenerateSdiv(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, HKHubArchJITOptions Options)
{
    return HKHubArchJITGenerate2OperandDivisionMutator(Ptr, Instruction, 3, TRUE, FALSE, Options & HKHubArchJITOptionsWatchMemory);
}

static size_t HKHubArchJITGenerateUmod(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, HKHubArchJITOptions Options)
{
    return HKHubArchJITGenerate2OperandDivisionMutator(Ptr, Instruction, 3, FALSE, TRUE, Options & HKHubArchJITOptionsWatchMemory);
}

static size_t HKHubArchJITGenerateSmod(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, HKHubArchJITOptions Options)
{
    return HKHubArchJITGenerate2OperandDivisionMutator(Ptr, Instruction, 3, TRUE, TRUE, Options & HKHubArchJITOptionsWatchMemory);
}

static size_t HKHubArchJITGenerateOr(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, HKHubArchJITOptions Options)
{
    return HKHubArchJITGenerate2OperandMutator(Ptr, Instruction, HKHubArchJITArithmeticOr, HKHubArchJITOpcodeOrMR8, HKHubArchJITOpcodeOrRM8, HKHubArchJITOpcodeArithmeticMI8, 1, TRUE, Options & HKHubArchJITOptionsWatchMemory);
}

static size_t HKHubArchJITGenerateXor(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, HKHubArchJITOptions Options)
{
    return HKHubArchJITGenerate2OperandMutator(Ptr, Instruction, HKHubArchJITArithmeticXor, HKHubArchJITOpcodeXorMR8, HKHubArchJITOpcodeXorRM8, HKHubArchJITOpcodeArithmeticMI8, 1, TRUE, Options & HKHubArchJITOptionsWatchMemory);
}

static size_t HKHubArchJITGenerateAnd(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, HKHubArchJITOptions Options)
{
    return HKHubArchJITGenerate2OperandMutator(Ptr, Instruction, HKHubArchJITArithmeticAnd, HKHubArchJITOpcodeAndMR8, HKHubArchJITOpcodeAndRM8, HKHubArchJITOpcodeArithmeticMI8, 1, TRUE, Options & HKHubArchJITOptionsWatchMemory);
}

static size_t HKHubArchJITGenerateCmp(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, HKHubArchJITOptions Options)
{
    return HKHubArchJITGenerate2OperandMutator(Ptr, Instruction, HKHubArchJITArithmeticCmp, HKHubArchJITOpcodeCmpMR8, HKHubArchJITOpcodeCmpRM8, HKHubArchJITOpcodeArithmeticMI8, 2, TRUE, Options & HKHubArchJITOptionsWatchMemory);
}

static size_t HKHubArchJITGenerateMov(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, HKHubArchJITOptions Options)
{
    return HKHubArchJITGenerate2OperandMutator(Ptr, Instruction, HKHubArchJITMoveMov, HKHubArchJITOpcodeMovMR8, HKHubArchJITOpcodeMovRM8, HKHubArchJITOpcodeMoveMI8, 1, FALSE, Options & HKHubArchJITOptionsWatchMemory);
}

static size_t HKHubArchJITGenerateShl(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction)
{
    return HKHubArchJITGenerate2OperandBitMutator(Ptr, Instruction, HKHubArchJITBitAdjustShl, 1, TRUE);
}

static size_t HKHubArchJITGenerateShr(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction)
{
    return HKHubArchJITGenerate2OperandBitMutator(Ptr, Instruction, HKHubArchJITBitAdjustShr, 1, TRUE);
}

static size_t HKHubArchJITGenerateNeg(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, HKHubArchJITOptions Options)
{
    return HKHubArchJITGenerate1OperandMutator(Ptr, Instruction, HKHubArchJITOneOpArithmeticNeg, HKHubArchJITOpcodeOneOpArithmeticM8, 1, TRUE, FALSE, Options & HKHubArchJITOptionsWatchMemory);
}

static size_t HKHubArchJITGenerateNot(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, HKHubArchJITOptions Options)
{
    return HKHubArchJITGenerate1OperandMutator(Ptr, Instruction, HKHubArchJITOneOpArithmeticNot, HKHubArchJITOpcodeOneOpArithmeticM8, 1, TRUE, TRUE, Options & HKHubArchJITOptionsWatchMemory);
}

static size_t HKHubArchJITGenerateNop(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction)
{
    return HKHubArchJITGenerate0OperandMutator(Ptr, Instruction, HKHubArchJITOpcodeNop, 0, FALSE);
}

static size_t HKHubArchJITGenerateJz(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, CCArray(HKHubArchJITJumpRef) Jumps)
{
    return HKHubArchJITGenerate1OperandJump(Ptr, Instruction, HKHubArchJITJumpZero, 1, Jumps);
}

static size_t HKHubArchJITGenerateJnz(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, CCArray(HKHubArchJITJumpRef) Jumps)
{
    return HKHubArchJITGenerate1OperandJump(Ptr, Instruction, HKHubArchJITJumpNotZero, 1, Jumps);
}

static size_t HKHubArchJITGenerateJs(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, CCArray(HKHubArchJITJumpRef) Jumps)
{
    return HKHubArchJITGenerate1OperandJump(Ptr, Instruction, HKHubArchJITJumpSign, 1, Jumps);
}

static size_t HKHubArchJITGenerateJns(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, CCArray(HKHubArchJITJumpRef) Jumps)
{
    return HKHubArchJITGenerate1OperandJump(Ptr, Instruction, HKHubArchJITJumpNotSign, 1, Jumps);
}

static size_t HKHubArchJITGenerateJo(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, CCArray(HKHubArchJITJumpRef) Jumps)
{
    return HKHubArchJITGenerate1OperandJump(Ptr, Instruction, HKHubArchJITJumpOverflow, 1, Jumps);
}

static size_t HKHubArchJITGenerateJno(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, CCArray(HKHubArchJITJumpRef) Jumps)
{
    return HKHubArchJITGenerate1OperandJump(Ptr, Instruction, HKHubArchJITJumpNotOverflow, 1, Jumps);
}

static size_t HKHubArchJITGenerateJsl(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, CCArray(HKHubArchJITJumpRef) Jumps)
{
    return HKHubArchJITGenerate1OperandJump(Ptr, Instruction, HKHubArchJITJumpLess, 1, Jumps);
}

static size_t HKHubArchJITGenerateJsge(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, CCArray(HKHubArchJITJumpRef) Jumps)
{
    return HKHubArchJITGenerate1OperandJump(Ptr, Instruction, HKHubArchJITJumpGreaterEqual, 1, Jumps);
}

static size_t HKHubArchJITGenerateJsle(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, CCArray(HKHubArchJITJumpRef) Jumps)
{
    return HKHubArchJITGenerate1OperandJump(Ptr, Instruction, HKHubArchJITJumpLessEqual, 1, Jumps);
}

static size_t HKHubArchJITGenerateJsg(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, CCArray(HKHubArchJITJumpRef) Jumps)
{
    return HKHubArchJITGenerate1OperandJump(Ptr, Instruction, HKHubArchJITJumpGreater, 1, Jumps);
}

static size_t HKHubArchJITGenerateJul(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, CCArray(HKHubArchJITJumpRef) Jumps)
{
    return HKHubArchJITGenerate1OperandJump(Ptr, Instruction, HKHubArchJITJumpBelow, 1, Jumps);
}

static size_t HKHubArchJITGenerateJuge(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, CCArray(HKHubArchJITJumpRef) Jumps)
{
    return HKHubArchJITGenerate1OperandJump(Ptr, Instruction, HKHubArchJITJumpAboveEqual, 1, Jumps);
}

static size_t HKHubArchJITGenerateJule(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, CCArray(HKHubArchJITJumpRef) Jumps)
{
    return HKHubArchJITGenerate1OperandJump(Ptr, Instruction, HKHubArchJITJumpBelowEqual, 1, Jumps);
}

static size_t HKHubArchJITGenerateJug(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, CCArray(HKHubArchJITJumpRef) Jumps)
{
    return HKHubArchJITGenerate1OperandJump(Ptr, Instruction, HKHubArchJITJumpAbove, 1, Jumps);
}

static size_t HKHubArchJITGenerateJmp(uint8_t *Ptr, const HKHubArchExecutionGraphInstruction *Instruction, CCArray(HKHubArchJITJumpRef) Jumps)
{
    return HKHubArchJITGenerate1OperandJump(Ptr, Instruction, HKHubArchJITJumpUnconditional, 1, Jumps);
}

_Bool HKHubArchJITGenerateBlock(HKHubArchJIT JIT, HKHubArchJITBlock *JITBlock, void *Ptr, CCLinkedList(HKHubArchExecutionGraphInstruction) Block, HKHubArchJITOptions Options)
{
    /*
     rax : reserved
     
     bl : r0
     bh : r1
     cl : r2
     ch : r3
     
     dl : flags
     dh : pc
     
     rsi : cycles
     rdi : memory
     
     rbp : reserved
     rsp : reserved
     r8 : reserved
     r9 : reserved
     */
    CCArray(HKHubArchJITJumpRef) Jumps = CCArrayCreate(CC_STD_ALLOCATOR, sizeof(HKHubArchJITJumpRef), 8);
    CCDictionary(uint8_t, size_t) Offsets = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeMedium | CCDictionaryHintHeavyInserting, sizeof(uint8_t), sizeof(size_t), NULL);
    
    CCEnumerable Enumerable;
    CCLinkedListGetEnumerable(Block, &Enumerable);
    
    size_t Index = 0, InstructionIndex = 0, ReturnIndex = 0;
    for (const HKHubArchExecutionGraphInstruction *Instruction = CCEnumerableGetCurrent(&Enumerable); Instruction; Instruction = CCEnumerableNext(&Enumerable), InstructionIndex++)
    {
        switch (Instruction->state.opcode)
        {
            case 0:
            case 1:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateAdd(&Ptr[Index], Instruction, Options);
                break;
                
            case 2:
            case 6:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateMov(&Ptr[Index], Instruction, Options);
                break;
                
            case 4:
            case 5:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateSub(&Ptr[Index], Instruction, Options);
                break;
                
            case 12:
            case 13:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateSdiv(&Ptr[Index], Instruction, Options);
                break;
                
            case 16:
            case 17:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateUdiv(&Ptr[Index], Instruction, Options);
                break;
                
            case 20:
            case 21:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateSmod(&Ptr[Index], Instruction, Options);
                break;
                
            case 24:
            case 25:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateUmod(&Ptr[Index], Instruction, Options);
                break;
                
            case 28:
            case 29:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateCmp(&Ptr[Index], Instruction, Options);
                break;
                
            case 32:
            case 33:
                if (Instruction->state.operand[0].type == HKHubArchInstructionOperandM)
                {
                    // TODO: Support memory destination
                    if (Index != ReturnIndex)
                    {
                        HKHubArchJITAddInstructionReturn(Ptr, &Index);
                        ReturnIndex = Index;
                    }
                }
                
                else
                {
                    CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                    CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                    Index += HKHubArchJITGenerateShl(&Ptr[Index], Instruction);
                }
                break;
                
            case 36:
            case 37:
                if (Instruction->state.operand[0].type == HKHubArchInstructionOperandM)
                {
                    // TODO: Support memory destination
                    if (Index != ReturnIndex)
                    {
                        HKHubArchJITAddInstructionReturn(Ptr, &Index);
                        ReturnIndex = Index;
                    }
                }
                
                else
                {
                    CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                    CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                    Index += HKHubArchJITGenerateShr(&Ptr[Index], Instruction);
                }
                break;
                
            case 40:
            case 41:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateXor(&Ptr[Index], Instruction, Options);
                break;
                
            case 44:
            case 45:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateOr(&Ptr[Index], Instruction, Options);
                break;
                
            case 46:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateNeg(&Ptr[Index], Instruction, Options);
                break;
                
            case 48:
            case 49:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateAnd(&Ptr[Index], Instruction, Options);
                break;
                
            case 50:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateNot(&Ptr[Index], Instruction, Options);
                break;
                
            case 62:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateNop(&Ptr[Index], Instruction);
                break;
                
            case 3:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateJz(&Ptr[Index], Instruction, Jumps);
                break;
                
            case 7:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateJnz(&Ptr[Index], Instruction, Jumps);
                break;
                
            case 11:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateJs(&Ptr[Index], Instruction, Jumps);
                break;
                
            case 15:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateJns(&Ptr[Index], Instruction, Jumps);
                break;
                
            case 19:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateJo(&Ptr[Index], Instruction, Jumps);
                break;
                
            case 23:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateJno(&Ptr[Index], Instruction, Jumps);
                break;
                
            case 52:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateJsl(&Ptr[Index], Instruction, Jumps);
                break;
                
            case 53:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateJsge(&Ptr[Index], Instruction, Jumps);
                break;
                
            case 54:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateJsle(&Ptr[Index], Instruction, Jumps);
                break;
                
            case 55:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateJsg(&Ptr[Index], Instruction, Jumps);
                break;
                
            case 56:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateJul(&Ptr[Index], Instruction, Jumps);
                break;
                
            case 57:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateJuge(&Ptr[Index], Instruction, Jumps);
                break;
                
            case 58:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateJule(&Ptr[Index], Instruction, Jumps);
                break;
                
            case 59:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateJug(&Ptr[Index], Instruction, Jumps);
                break;
                
            case 63:
                CCDictionarySetValue(Offsets, &Instruction->offset, &Index);
                CCArrayAppendElement(JITBlock->map, &(HKHubArchJITBlockRelativeEntry){ .entry = (uintptr_t)(Ptr + Index), .index = InstructionIndex });
                Index += HKHubArchJITGenerateJmp(&Ptr[Index], Instruction, Jumps);
                break;
                
            default:
                if (Index != ReturnIndex)
                {
                    HKHubArchJITAddInstructionReturn(Ptr, &Index);
                    ReturnIndex = Index;
                }
                break;
        }
    }
    
    for (size_t Loop = 0, Count = CCArrayGetCount(Jumps); Loop < Count; Loop++)
    {
        const HKHubArchJITJumpRef *Ref = CCArrayGetElementAtIndex(Jumps, Loop);
        size_t *Index = CCDictionaryGetValue(Offsets, &Ref->pc);
        
        if (Index) *Ref->rel = (int32_t)(*Index - ((ptrdiff_t)Ref->rel - (ptrdiff_t)Ptr) - 4);
        else *Ref->jump = HKHubArchJITOpcodeRetn;
    }
    
    CCDictionaryDestroy(Offsets);
    CCArrayDestroy(Jumps);
    
    if (Index != ReturnIndex)
    {
        HKHubArchJITAddInstructionReturn(Ptr, &Index);
        
        return TRUE;
    }
    
    return Index;
}

void HKHubArchJITRemoveEntry(void *Entry)
{
    HKHubArchJITAddInstructionReturn(Entry, &(size_t){ 0 });
}

void HKHubArchJITCall(HKHubArchJIT JIT, HKHubArchProcessor Processor)
{
    const HKHubArchJITBlockReferenceEntry *Entry = CCDictionaryGetValue(JIT->map, &Processor->state.pc);
    if (!Entry) return;
    
#define HK_HUB_ARCH_JIT_Processor_r0 56
#define HK_HUB_ARCH_JIT_Processor_r1 57
#define HK_HUB_ARCH_JIT_Processor_r2 58
#define HK_HUB_ARCH_JIT_Processor_r3 59
#define HK_HUB_ARCH_JIT_Processor_pc 60
#define HK_HUB_ARCH_JIT_Processor_flags 61
#define HK_HUB_ARCH_JIT_Processor_cycles 160
#define HK_HUB_ARCH_JIT_Processor_memory 180
    
    _Static_assert(HK_HUB_ARCH_JIT_Processor_r0 == offsetof(typeof(*Processor), state.r[0]) &&
                   HK_HUB_ARCH_JIT_Processor_r1 == offsetof(typeof(*Processor), state.r[1]) &&
                   HK_HUB_ARCH_JIT_Processor_r2 == offsetof(typeof(*Processor), state.r[2]) &&
                   HK_HUB_ARCH_JIT_Processor_r3 == offsetof(typeof(*Processor), state.r[3]) &&
                   HK_HUB_ARCH_JIT_Processor_pc == offsetof(typeof(*Processor), state.pc) &&
                   HK_HUB_ARCH_JIT_Processor_flags == offsetof(typeof(*Processor), state.flags) &&
                   HK_HUB_ARCH_JIT_Processor_cycles == offsetof(typeof(*Processor), cycles) &&
                   HK_HUB_ARCH_JIT_Processor_memory == offsetof(typeof(*Processor), memory), "Need to update the offsets");
    
#define HK_HUB_ARCH_JIT_LABEL(label) HK_HUB_ARCH_JIT_LABEL_(label, HK_HUB_ARCH_JIT_##label)
#define HK_HUB_ARCH_JIT_LABEL_(label, value) HK_HUB_ARCH_JIT_LABEL__(label, value)
#define HK_HUB_ARCH_JIT_LABEL__(label, value) ".set " #label ", " #value "\n"
    
    asm(HK_HUB_ARCH_JIT_LABEL(Processor_r0)
        HK_HUB_ARCH_JIT_LABEL(Processor_r1)
        HK_HUB_ARCH_JIT_LABEL(Processor_r2)
        HK_HUB_ARCH_JIT_LABEL(Processor_r3)
        HK_HUB_ARCH_JIT_LABEL(Processor_pc)
        HK_HUB_ARCH_JIT_LABEL(Processor_flags)
        HK_HUB_ARCH_JIT_LABEL(Processor_cycles)
        HK_HUB_ARCH_JIT_LABEL(Processor_memory)
        "movq %0, %%rax\n"
        "movb Processor_r0(%%rax), %%bl\n"
        "movb Processor_r1(%%rax), %%bh\n"
        "movb Processor_r2(%%rax), %%cl\n"
        "movb Processor_r3(%%rax), %%ch\n"
        "movb Processor_flags(%%rax), %%dl\n"
        "movb Processor_pc(%%rax), %%dh\n"
        "movq Processor_cycles(%%rax), %%rsi\n"
        "leaq Processor_memory(%%rax), %%rdi\n"
        "pushq %%rbp\n"
        "pushq %%rax\n"
        "xorq %%rbp, %%rbp\n"
        "xorq %%rax, %%rax\n"
        "callq *%1\n"
        "popq %%rax\n"
        "popq %%rbp\n"
        "movb %%bl, Processor_r0(%%rax)\n"
        "movb %%bh, Processor_r1(%%rax)\n"
        "movb %%cl, Processor_r2(%%rax)\n"
        "movb %%ch, Processor_r3(%%rax)\n"
        "movb %%dl, Processor_flags(%%rax)\n"
        "movb %%dh, Processor_pc(%%rax)\n"
        "movq %%rsi, Processor_cycles(%%rax)\n"
        :
        : "m" (Processor), "m" (Entry->entry)
        : "rax", "rbx", "rcx", "rdx", "rsi", "rdi", "r8", "r9", "memory");
}
#endif
