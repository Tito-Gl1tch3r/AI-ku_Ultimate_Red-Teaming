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

#include "HubArchExpressions.h"
#include "HubArchInstruction.h"

CCExpression HKHubArchExpressionDisassemble(CCExpression Expression)
{
    const size_t ArgCount = CCCollectionGetCount(CCExpressionGetList(Expression)) - 1;
    
    if (ArgCount == 2)
    {
        CCExpression Bytes = CCExpressionEvaluate(*(CCExpression*)CCOrderedCollectionGetElementAtIndex(CCExpressionGetList(Expression), 1));
        CCExpression Offset = CCExpressionEvaluate(*(CCExpression*)CCOrderedCollectionGetElementAtIndex(CCExpressionGetList(Expression), 2));
        
        if (((CCExpressionGetType(Bytes) == CCExpressionValueTypeList) && (CCCollectionGetCount(CCExpressionGetList(Bytes)) == 256)) && (CCExpressionGetType(Offset) == CCExpressionValueTypeInteger))
        {
            uint8_t Data[6], Address = CCExpressionGetInteger(Offset);
            for (uint8_t Loop = 0; Loop < sizeof(Data) / sizeof(typeof(*Data)); Loop++)
            {
                CCExpression Byte = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(CCExpressionGetList(Bytes), (uint8_t)(Address + Loop));
                if (CCExpressionGetType(Byte) != CCExpressionValueTypeInteger)
                {
                    CC_EXPRESSION_EVALUATOR_LOG_FUNCTION_ERROR("disassemble", "bytes:list offset:integer");
                    
                    return Expression;
                }
                
                Data[Loop] = CCExpressionGetInteger(Byte);
            }
            
            HKHubArchInstructionState Instruction;
            uint8_t Count = HKHubArchInstructionDecode(0, Data, &Instruction);
            CCString Disassembly = HKHubArchInstructionDisassemble(&Instruction);
            
            CCExpression Result = CCExpressionCreateList(CC_STD_ALLOCATOR);
            CCOrderedCollectionAppendElement(CCExpressionGetList(Result), &(CCExpression){ CCExpressionCreateInteger(CC_STD_ALLOCATOR, Count) });
            CCOrderedCollectionAppendElement(CCExpressionGetList(Result), &(CCExpression){ CCExpressionCreateString(CC_STD_ALLOCATOR, Disassembly ? Disassembly : CCStringCopy(CC_STRING("")), FALSE) });
            
            return Result;
        }
    }
    
    CC_EXPRESSION_EVALUATOR_LOG_FUNCTION_ERROR("disassemble", "bytes:list offset:integer");
    
    return Expression;
}
