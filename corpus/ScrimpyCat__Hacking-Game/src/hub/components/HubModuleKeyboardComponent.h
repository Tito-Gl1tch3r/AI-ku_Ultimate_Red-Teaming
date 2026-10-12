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

#ifndef HackingGame_HubModuleKeyboardComponent_h
#define HackingGame_HubModuleKeyboardComponent_h

#include "Base.h"
#include "HubModuleComponent.h"
#include "HubModuleKeyboard.h"

#define HK_HUB_MODULE_KEYBOARD_COMPONENT_ID (HK_HUB_MODULE_COMPONENT_ID | HKHubTypeModuleKeyboard)

typedef struct {
    CC_COMPONENT_INHERIT(HKHubModuleComponentClass);
} HKHubModuleKeyboardComponentClass, *HKHubModuleKeyboardComponentPrivate;

#define HK_HUB_MODULE_KEYBOARD_COMPONENT_KEY_IN_MESSAGE_ID 'keys'

extern const CCComponentExpressionDescriptor HKHubModuleKeyboardComponentDescriptor;

void HKHubModuleKeyboardComponentRegister(void);
void HKHubModuleKeyboardComponentDeregister(void);
void HKHubModuleKeyboardComponenDeserializer(CCComponent Component, CCExpression Arg, _Bool Deferred);
void HKHubModuleKeyboardComponentKeyboardCallback(CCComponent Component, CCKeyboardMap State);

/*!
 * @brief Initialize the keyboard module component.
 * @param Component The component to be initialized.
 * @param id The component ID.
 */
static inline void HKHubModuleKeyboardComponentInitialize(CCComponent Component, CCComponentID id);

/*!
 * @brief Deallocate the keyboard module component.
 * @param Component The component to be deallocated.
 */
static inline void HKHubModuleKeyboardComponentDeallocate(CCComponent Component);


#pragma mark -

static inline void HKHubModuleKeyboardComponentInitialize(CCComponent Component, CCComponentID id)
{
    HKHubModuleComponentInitialize(Component, id);
    
    HKHubModuleComponentSetName(Component, CCStringCopy(CC_STRING("keyboard")));
    HKHubModuleComponentSetModule(Component, HKHubModuleKeyboardCreate(CC_STD_ALLOCATOR));
}

static inline void HKHubModuleKeyboardComponentDeallocate(CCComponent Component)
{
    HKHubModuleComponentDeallocate(Component);
}

#endif
