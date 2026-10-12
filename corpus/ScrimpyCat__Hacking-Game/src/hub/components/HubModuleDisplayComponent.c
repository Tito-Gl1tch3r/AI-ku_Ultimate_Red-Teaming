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

#include "HubModuleDisplayComponent.h"
#include "HubModuleComponent.h"
#include "HubModuleDisplay.h"


const CCString HKHubModuleDisplayComponentName = CC_STRING("display_module");

const CCComponentExpressionDescriptor HKHubModuleDisplayComponentDescriptor = {
    .id = HK_HUB_MODULE_DISPLAY_COMPONENT_ID,
    .initialize = NULL,
    .deserialize = HKHubModuleDisplayComponenDeserializer,
    .serialize = NULL
};

static CCDictionary(CCString, HKHubModuleDisplayBufferConverter) Encoders = NULL;

void HKHubModuleDisplayComponentRegister(void)
{
    CCComponentRegister(HK_HUB_MODULE_DISPLAY_COMPONENT_ID, HKHubModuleDisplayComponentName, CC_STD_ALLOCATOR, sizeof(HKHubModuleDisplayComponentClass), HKHubModuleDisplayComponentInitialize, NULL, HKHubModuleDisplayComponentDeallocate);
    
    CCComponentExpressionRegister(CC_STRING("display-module"), &HKHubModuleDisplayComponentDescriptor, TRUE);
    
    Encoders = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintHeavyFinding | CCDictionaryHintConstantLength | CCDictionaryHintConstantElements, sizeof(CCString), sizeof(HKHubModuleDisplayBufferConverter), &(CCDictionaryCallbacks){
        .getHash = CCStringHasherForDictionary,
        .compareKeys = CCStringComparatorForDictionary,
        .keyDestructor = CCStringDestructorForDictionary
    });
    
    CCDictionarySetValue(Encoders, &(CCString){ CCStringCopy(CC_STRING(":uniform")) }, &HKHubModuleDisplayBuffer_UniformColourRGB888);
    CCDictionarySetValue(Encoders, &(CCString){ CCStringCopy(CC_STRING(":direct")) }, &HKHubModuleDisplayBuffer_DirectColourRGB888);
    CCDictionarySetValue(Encoders, &(CCString){ CCStringCopy(CC_STRING(":gradient")) }, &HKHubModuleDisplayBuffer_GradientColourRGB888);
    CCDictionarySetValue(Encoders, &(CCString){ CCStringCopy(CC_STRING(":yuv")) }, &HKHubModuleDisplayBuffer_YUVColourRGB888);
}

void HKHubModuleDisplayComponentDeregister(void)
{
    CCComponentDeregister(HK_HUB_MODULE_DISPLAY_COMPONENT_ID);
}

static CCComponentExpressionArgumentDeserializer Arguments[] = {
    { .name = CC_STRING("resolution:"), .serializedType = CCExpressionValueTypeUnspecified, .setterType = CCComponentExpressionArgumentTypeVector2i, .setter = HKHubModuleDisplayComponentSetResolution }
};

void HKHubModuleDisplayComponenDeserializer(CCComponent Component, CCExpression Arg, _Bool Deferred)
{
    if (CCExpressionGetType(Arg) == CCExpressionValueTypeList)
    {
        const size_t ArgCount = CCCollectionGetCount(CCExpressionGetList(Arg));
        if (CCCollectionGetCount(CCExpressionGetList(Arg)) >= 2)
        {
            CCExpression NameExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(CCExpressionGetList(Arg), 0);
            if (CCExpressionGetType(NameExpr) == CCExpressionValueTypeAtom)
            {
                CCString Name = CCExpressionGetAtom(NameExpr);
                if (CCStringEqual(Name, CC_STRING("encoding:")))
                {
                    if (ArgCount == 2)
                    {
                        CCExpression EncodingExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(CCExpressionGetList(Arg), 1);
                        if (CCExpressionGetType(EncodingExpr) == CCExpressionValueTypeAtom)
                        {
                            CCString Encoding = CCExpressionGetAtom(EncodingExpr);
                            
                            HKHubModuleDisplayBufferConverter *Value = CCDictionaryGetValue(Encoders, &Encoding);
                            if (Value)
                            {
                                HKHubModuleDisplayComponentSetEncoder(Component, *Value);
                            }
                            
                            else CC_LOG_ERROR_CUSTOM("Value (:%S) for argument (encoding:) is not a valid atom", Encoding);
                            
                        }
                        
                        else CC_LOG_ERROR("Expect value for argument (encoding:) to be an atom");
                    }
                    
                    else CC_LOG_ERROR("Expect value for argument (encoding:) to be an atom");
                    
                    return;
                }
                
                else if (CCStringEqual(Name, CC_STRING("framebuffer:")))
                {
                    if (ArgCount == 2)
                    {
                        CCExpression FramebufferExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(CCExpressionGetList(Arg), 1);
                        if (CCExpressionGetType(FramebufferExpr) == CCExpressionValueTypeList)
                        {
                            CCOrderedCollection(CCExpression) Framebuffer = CCExpressionGetList(FramebufferExpr);
                            HKHubModule Module = HKHubModuleComponentGetModule(Component);
                            CCData Data = HKHubModuleGetMemory(Module);
                            const size_t Size = CCDataGetSize(Data);
                            
                            if (CCCollectionGetCount(Framebuffer) < Size)
                            {
                                CCBufferMap Map = CCDataMapBuffer(Data, 0, Size, CCDataHintReadWrite);
                                
                                size_t Index = 0;
                                CC_COLLECTION_FOREACH(CCExpression, Pixel, Framebuffer)
                                {
                                    if (CCExpressionGetType(Pixel) == CCExpressionValueTypeInteger)
                                    {
                                        ((uint8_t*)Map.ptr)[Index] = (uint8_t)CCExpressionGetInteger(Pixel);
                                    }
                                    
                                    else
                                    {
                                        CC_LOG_ERROR("Expect value for argument (framebuffer:) to be a list of integers");
                                        break;
                                    }
                                }
                                
                                CCDataUnmapBuffer(Data, Map);
                            }
                            
                            else CC_LOG_ERROR("Expect value for argument (framebuffer:) to be a list of up to %zu integers", Size);
                        }
                        
                        else CC_LOG_ERROR("Expect value for argument (framebuffer:) to be a list");
                    }
                    
                    else CC_LOG_ERROR("Expect value for argument (framebuffer:) to be a list");
                    
                    return;
                }
            }
        }
    }
    
    CCComponentExpressionDeserializeArgument(Component, Arg, Arguments, sizeof(Arguments) / sizeof(typeof(*Arguments)), Deferred);
}
