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

#include "HubProcessorComponent.h"
#include "HubArchAssembly.h"

const CCString HKHubProcessorComponentName = CC_STRING("hub");

static const CCComponentExpressionDescriptor HKHubProcessorComponentDescriptor = {
    .id = HK_HUB_PROCESSOR_COMPONENT_ID,
    .initialize = NULL,
    .deserialize = HKHubProcessorComponentDeserializer,
    .serialize = NULL
};

void HKHubProcessorComponentRegister(void)
{
    CCComponentRegister(HK_HUB_PROCESSOR_COMPONENT_ID, HKHubProcessorComponentName, CC_STD_ALLOCATOR, sizeof(HKHubProcessorComponentClass), HKHubProcessorComponentInitialize, NULL, HKHubProcessorComponentDeallocate);
    
    CCComponentExpressionRegister(CC_STRING("hub"), &HKHubProcessorComponentDescriptor, TRUE);
}

void HKHubProcessorComponentDeregister(void)
{
    CCComponentDeregister(HK_HUB_PROCESSOR_COMPONENT_ID);
}

static CCComponentExpressionArgumentDeserializer Arguments[] = {
    { .name = CC_STRING("name:"), .serializedType = CCExpressionValueTypeUnspecified, .setterType = CCComponentExpressionArgumentTypeString, .setter = HKHubProcessorComponentSetName }
};

void HKHubProcessorComponentDeserializer(CCComponent Component, CCExpression Arg, _Bool Deferred)
{
    if (CCExpressionGetType(Arg) == CCExpressionValueTypeList)
    {
        const size_t ArgCount = CCCollectionGetCount(CCExpressionGetList(Arg));
        if (ArgCount >= 2)
        {
            CCExpression NameExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(CCExpressionGetList(Arg), 0);
            if (CCExpressionGetType(NameExpr) == CCExpressionValueTypeAtom)
            {
                CCString Name = CCExpressionGetAtom(NameExpr);
                if (CCStringEqual(Name, CC_STRING("program:")))
                {
                    CCEnumerator Enumerator;
                    CCCollectionGetEnumerator(CCExpressionGetList(Arg), &Enumerator);
                    
                    CCExpression *File = CCCollectionEnumeratorNext(&Enumerator);
                    if ((File) && (CCExpressionGetType(*File) == CCExpressionValueTypeString))
                    {
                        CC_STRING_TEMP_BUFFER(Buffer, CCExpressionGetString(*File))
                        {
                            FSPath Path = FSPathCreate(Buffer);
                            
                            FSHandle Handle;
                            if (FSHandleOpen(Path, FSHandleTypeRead, &Handle) == FSOperationSuccess)
                            {
                                size_t Size = FSManagerGetSize(Path), DefineSize = 600, Index = 0;
                                char *Source;
                                CC_SAFE_Malloc(Source, sizeof(char) * (Size + DefineSize + 2));
                                
                                for (CCExpression *Option; (Option = CCCollectionEnumeratorNext(&Enumerator)); )
                                {
                                    if (CCExpressionGetType(*Option) == CCExpressionValueTypeList)
                                    {
                                        CCOrderedCollection(CCExpression) List = CCExpressionGetList(*Option);
                                        const size_t OptionCount = CCCollectionGetCount(List);
                                        
                                        if (OptionCount >= 2)
                                        {
                                            CCExpression NameExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(List, 0);
                                            
                                            if (CCExpressionGetType(NameExpr) == CCExpressionValueTypeAtom)
                                            {
                                                CCString Name = CCExpressionGetAtom(NameExpr);
                                                
                                                if (CCStringEqual(Name, CC_STRING("define:")))
                                                {
                                                    if (OptionCount == 3)
                                                    {
                                                        CCExpression DefineExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(List, 1);
                                                        CCExpression ValueExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(List, 2);
                                                        
                                                        if ((CCExpressionGetType(DefineExpr) == CCExpressionValueTypeString) && (CCExpressionGetType(ValueExpr) == CCExpressionValueTypeInteger))
                                                        {
                                                            CCString Define = CCExpressionGetString(DefineExpr);
                                                            const size_t Length = 32 + CCStringGetSize(Define);
                                                            
                                                            if ((Index + Length) > DefineSize)
                                                            {
                                                                DefineSize += ((Length / 600) + 1) * 600;
                                                                CC_SAFE_Realloc(Source, sizeof(char) * (Size + DefineSize + 1))
                                                            }
                                                            
                                                            CC_STRING_TEMP_BUFFER(Buffer, Define)
                                                            {
                                                                Index += sprintf(&Source[Index], ".define %s,%d\n", Buffer, CCExpressionGetInteger(ValueExpr));
                                                            }
                                                        }
                                                        
                                                        else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("define", "string integer");
                                                    }
                                                    
                                                    else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("define", "string integer");
                                                }
                                            }
                                        }
                                    }
                                }
                                
                                FSHandleRead(Handle, &Size, &Source[Index], FSBehaviourDefault);
                                Source[Index + Size] = '\n';
                                Source[Index + Size + 1] = 0;
                                
                                FSHandleClose(Handle);
                                
                                CCOrderedCollection(HKHubArchAssemblyASTNode) AST = HKHubArchAssemblyParse(Source);
                                
                                CCOrderedCollection(HKHubArchAssemblyASTError) Errors = NULL;
                                HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors);
                                CCCollectionDestroy(AST);
                                
                                if (Binary)
                                {
                                    HKHubProcessorComponentSetProcessor(Component, HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary));
                                    HKHubArchBinaryDestroy(Binary); //TODO: Possibly store binary in the component, so the processor can be rebooted
                                }
                                
                                else if (Errors)
                                {
                                    CC_LOG_ERROR("Unable to assemble program (%s)", Buffer);
                                    HKHubArchAssemblyPrintError(Errors);
                                    CCCollectionDestroy(Errors);
                                }
                                
                                CC_SAFE_Free(Source);
                            }
                            
                            else CC_LOG_ERROR("Could not open file (%s) for argument (program:)", Buffer);
                            
                            FSPathDestroy(Path);
                        }
                    }
                    
                    else CC_LOG_ERROR("Expect value for argument (program:) to be a string");
                    
                    return;
                }
                
                else if (CCStringEqual(Name, CC_STRING("state:")))
                {
                    HKHubArchProcessor Processor = HKHubProcessorComponentGetProcessor(Component);
                    if (Processor)
                    {
                        CCEnumerator Enumerator;
                        CCCollectionGetEnumerator(CCExpressionGetList(Arg), &Enumerator);
                        
                        CCExpression *Data = CCCollectionEnumeratorNext(&Enumerator);
                        if ((Data) && (CCExpressionGetType(*Data) == CCExpressionValueTypeList))
                        {
                            CCOrderedCollection(CCExpression) Memory = CCExpressionGetList(*Data);
                            
                            if (CCCollectionGetCount(Memory) < sizeof(Processor->memory))
                            {
                                size_t Index = 0;
                                CC_COLLECTION_FOREACH(CCExpression, Byte, Memory)
                                {
                                    if (CCExpressionGetType(Byte) == CCExpressionValueTypeInteger)
                                    {
                                        Processor->memory[Index++] = (uint8_t)CCExpressionGetInteger(Byte);
                                    }
                                    
                                    else
                                    {
                                        CC_LOG_ERROR("Expect value for argument (state:) to be a list of integers");
                                        
                                        return;
                                    }
                                }
                            }
                            
                            else CC_LOG_ERROR("Expect value for argument (state:) to be a list of up to 256 integers");
                            
                            for (CCExpression *Option; (Option = CCCollectionEnumeratorNext(&Enumerator)); )
                            {
                                if (CCExpressionGetType(*Option) == CCExpressionValueTypeList)
                                {
                                    CCOrderedCollection(CCExpression) List = CCExpressionGetList(*Option);
                                    const size_t OptionCount = CCCollectionGetCount(List);
                                    
                                    if (OptionCount >= 2)
                                    {
                                        CCExpression NameExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(List, 0);
                                        
                                        if (CCExpressionGetType(NameExpr) == CCExpressionValueTypeAtom)
                                        {
                                            CCString Name = CCExpressionGetAtom(NameExpr);
                                            
                                            if (CCStringEqual(Name, CC_STRING("pc:")))
                                            {
                                                if (OptionCount == 2)
                                                {
                                                    CCExpression ValueExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(List, 1);
                                                    
                                                    if (CCExpressionGetType(ValueExpr) == CCExpressionValueTypeInteger)
                                                    {
                                                        Processor->state.pc = (uint8_t)CCExpressionGetInteger(ValueExpr);
                                                    }
                                                    
                                                    else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("pc", "integer");
                                                }
                                                
                                                else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("pc", "integer");
                                            }
                                            
                                            else if (CCStringEqual(Name, CC_STRING("r0:")))
                                            {
                                                if (OptionCount == 2)
                                                {
                                                    CCExpression ValueExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(List, 1);
                                                    
                                                    if (CCExpressionGetType(ValueExpr) == CCExpressionValueTypeInteger)
                                                    {
                                                        Processor->state.r[0] = (uint8_t)CCExpressionGetInteger(ValueExpr);
                                                    }
                                                    
                                                    else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("r0", "integer");
                                                }
                                                
                                                else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("r0", "integer");
                                            }
                                            
                                            else if (CCStringEqual(Name, CC_STRING("r1:")))
                                            {
                                                if (OptionCount == 2)
                                                {
                                                    CCExpression ValueExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(List, 1);
                                                    
                                                    if (CCExpressionGetType(ValueExpr) == CCExpressionValueTypeInteger)
                                                    {
                                                        Processor->state.r[1] = (uint8_t)CCExpressionGetInteger(ValueExpr);
                                                    }
                                                    
                                                    else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("r1", "integer");
                                                }
                                                
                                                else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("r1", "integer");
                                            }
                                            
                                            else if (CCStringEqual(Name, CC_STRING("r2:")))
                                            {
                                                if (OptionCount == 2)
                                                {
                                                    CCExpression ValueExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(List, 1);
                                                    
                                                    if (CCExpressionGetType(ValueExpr) == CCExpressionValueTypeInteger)
                                                    {
                                                        Processor->state.r[2] = (uint8_t)CCExpressionGetInteger(ValueExpr);
                                                    }
                                                    
                                                    else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("r2", "integer");
                                                }
                                                
                                                else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("r2", "integer");
                                            }
                                            
                                            else if (CCStringEqual(Name, CC_STRING("r3:")))
                                            {
                                                if (OptionCount == 2)
                                                {
                                                    CCExpression ValueExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(List, 1);
                                                    
                                                    if (CCExpressionGetType(ValueExpr) == CCExpressionValueTypeInteger)
                                                    {
                                                        Processor->state.r[3] = (uint8_t)CCExpressionGetInteger(ValueExpr);
                                                    }
                                                    
                                                    else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("r3", "integer");
                                                }
                                                
                                                else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("r3", "integer");
                                            }
                                            
                                            else if (CCStringEqual(Name, CC_STRING("flags:")))
                                            {
                                                if (OptionCount == 2)
                                                {
                                                    CCExpression ValueExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(List, 1);
                                                    
                                                    if (CCExpressionGetType(ValueExpr) == CCExpressionValueTypeInteger)
                                                    {
                                                        Processor->state.flags = (uint8_t)CCExpressionGetInteger(ValueExpr);
                                                    }
                                                    
                                                    else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("flags", "integer");
                                                }
                                                
                                                else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("flags", "integer");
                                            }
                                            
                                            else if (CCStringEqual(Name, CC_STRING("cycles:")))
                                            {
                                                if (OptionCount == 2)
                                                {
                                                    CCExpression ValueExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(List, 1);
                                                    
                                                    if (CCExpressionGetType(ValueExpr) == CCExpressionValueTypeInteger)
                                                    {
                                                        Processor->cycles = CCExpressionGetInteger(ValueExpr);
                                                    }
                                                    
                                                    else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("cycles", "integer");
                                                }
                                                
                                                else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("cycles", "integer");
                                            }
                                            
                                            else if (CCStringEqual(Name, CC_STRING("status:")))
                                            {
                                                if (OptionCount == 2)
                                                {
                                                    CCExpression ValueExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(List, 1);
                                                    
                                                    if (CCExpressionGetType(ValueExpr) == CCExpressionValueTypeInteger)
                                                    {
                                                        Processor->status = CCExpressionGetInteger(ValueExpr);
                                                    }
                                                    
                                                    else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("status", "integer");
                                                }
                                                
                                                else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("status", "integer");
                                            }
                                            
                                            else if (CCStringEqual(Name, CC_STRING("unused-time:")))
                                            {
                                                if (OptionCount == 2)
                                                {
                                                    CCExpression ValueExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(List, 1);
                                                    
                                                    if (CCExpressionGetType(ValueExpr) == CCExpressionValueTypeInteger)
                                                    {
                                                        Processor->unusedTime = CCExpressionGetFloat(ValueExpr);
                                                    }
                                                    
                                                    else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("unused-time", "float");
                                                }
                                                
                                                else CC_EXPRESSION_EVALUATOR_LOG_OPTION_ERROR("unused-time", "float");
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        
                        else CC_LOG_ERROR("Expect value for argument (state:) to be a list");
                    }
                    
                    else CC_LOG_ERROR("Expect processor to already be initialised");
                    
                    return;
                }
                
                else if (CCStringEqual(Name, CC_STRING("jit:")))
                {
                    HKHubArchProcessor Processor = HKHubProcessorComponentGetProcessor(Component);
                    if (Processor)
                    {
                        if (ArgCount == 2)
                        {
                            CCExpression JITExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(CCExpressionGetList(Arg), 1);
                            if (CCExpressionGetType(JITExpr) == CCExpressionValueTypeInteger)
                            {
                                if (CCExpressionGetInteger(JITExpr))
                                {
                                    HKHubArchProcessorCache(Processor, 0);
                                }
                            }
                            
                            else CC_LOG_ERROR("Expect value for argument (jit:) to be a boolean");
                        }
                        
                        else CC_LOG_ERROR("Expect value for argument (jit:) to be a boolean");
                    }
                    
                    else CC_LOG_ERROR("Expect processor to already be initialised");
                    
                    return;
                }
            }
        }
    }
    
    CCComponentExpressionDeserializeArgument(Component, Arg, Arguments, sizeof(Arguments) / sizeof(typeof(*Arguments)), Deferred);
}
