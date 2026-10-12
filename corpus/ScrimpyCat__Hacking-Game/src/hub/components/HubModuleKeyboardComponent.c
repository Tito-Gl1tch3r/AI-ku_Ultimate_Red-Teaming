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

#include "HubModuleKeyboardComponent.h"
#include "HubModuleComponent.h"
#include "HubModuleKeyboard.h"


const CCString HKHubModuleKeyboardComponentName = CC_STRING("keyboard_module");

const CCComponentExpressionDescriptor HKHubModuleKeyboardComponentDescriptor = {
    .id = HK_HUB_MODULE_KEYBOARD_COMPONENT_ID,
    .initialize = NULL,
    .deserialize = HKHubModuleKeyboardComponenDeserializer,
    .serialize = NULL
};

void HKHubModuleKeyboardComponentKeyboardCallback(CCComponent Component, CCKeyboardMap State)
{
    if (State.state.down) CCMessagePost(CC_STD_ALLOCATOR, HK_HUB_MODULE_KEYBOARD_COMPONENT_KEY_IN_MESSAGE_ID, CCMessageDeliverToComponentBelongingToEntity(HK_HUB_MODULE_KEYBOARD_COMPONENT_ID, CCComponentGetEntity(Component)), sizeof(uint8_t), &(uint8_t){ State.character }, NULL);
}

static void HKHubModuleKeyboardComponentMessageHandler(CCComponent Component, CCMessage *Message)
{
    switch (Message->id)
    {
        case HK_HUB_MODULE_KEYBOARD_COMPONENT_KEY_IN_MESSAGE_ID:
            HKHubModuleKeyboardEnterKey(HKHubModuleComponentGetModule(Component), *(uint8_t*)CCMessageGetData(Message));
            break;
    }
}

void HKHubModuleKeyboardComponentRegister(void)
{
    CCComponentRegister(HK_HUB_MODULE_KEYBOARD_COMPONENT_ID, HKHubModuleKeyboardComponentName, CC_STD_ALLOCATOR, sizeof(HKHubModuleKeyboardComponentClass), HKHubModuleKeyboardComponentInitialize, HKHubModuleKeyboardComponentMessageHandler, HKHubModuleKeyboardComponentDeallocate);
    
    CCComponentExpressionRegister(CC_STRING("keyboard-module"), &HKHubModuleKeyboardComponentDescriptor, TRUE);
    
    CCInputMapComponentRegisterCallback(CC_STRING(":keyboard-module"), CCInputMapTypeKeyboard, HKHubModuleKeyboardComponentKeyboardCallback);
}

void HKHubModuleKeyboardComponentDeregister(void)
{
    CCComponentDeregister(HK_HUB_MODULE_KEYBOARD_COMPONENT_ID);
}

void HKHubModuleKeyboardComponenDeserializer(CCComponent Component, CCExpression Arg, _Bool Deferred)
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
                if (CCStringEqual(Name, CC_STRING("buffer:")))
                {
                    if (ArgCount == 2)
                    {
                        CCExpression BufferExpr = *(CCExpression*)CCOrderedCollectionGetElementAtIndex(CCExpressionGetList(Arg), 1);
                        if (CCExpressionGetType(BufferExpr) == CCExpressionValueTypeList)
                        {
                            HKHubModule Module = HKHubModuleComponentGetModule(Component);
                            CCOrderedCollection(CCExpression) Buffer = CCExpressionGetList(BufferExpr);
                            
                            CC_COLLECTION_FOREACH(CCExpression, Key, Buffer)
                            {
                                if (CCExpressionGetType(Key) == CCExpressionValueTypeInteger)
                                {
                                    HKHubModuleKeyboardEnterKey(Module, (uint8_t)CCExpressionGetInteger(Key));
                                }
                                
                                else
                                {
                                    CC_LOG_ERROR("Expect value for argument (buffer:) to be a list of integers");
                                    
                                    return;
                                }
                            }

                        }
                        
                        else CC_LOG_ERROR("Expect value for argument (buffer:) to be a list");
                    }
                    
                    else CC_LOG_ERROR("Expect value for argument (buffer:) to be a list");
                    
                    return;
                }
            }
        }
    }
}
