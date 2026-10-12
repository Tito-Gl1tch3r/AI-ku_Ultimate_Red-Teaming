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

#ifndef HackingGame_HubProcessorComponent_h
#define HackingGame_HubProcessorComponent_h

#include "Base.h"
#include "HubArchProcessor.h"
#include "HubSystem.h"

#define HK_HUB_PROCESSOR_COMPONENT_ID (HKHubTypeProcessor | HK_HUB_COMPONENT_FLAG)

typedef struct {
    CC_COMPONENT_INHERIT(CCComponentClass);
    CCString name;
    HKHubArchProcessor processor;
} HKHubProcessorComponentClass, *HKHubProcessorComponentPrivate;


void HKHubProcessorComponentRegister(void);
void HKHubProcessorComponentDeregister(void);
void HKHubProcessorComponentDeserializer(CCComponent Component, CCExpression Arg, _Bool Deferred);

/*!
 * @brief Initialize the hub component.
 * @param Component The component to be initialized.
 * @param id The component ID.
 */
static inline void HKHubProcessorComponentInitialize(CCComponent Component, CCComponentID id);

/*!
 * @brief Deallocate the hub component.
 * @param Component The component to be deallocated.
 */
static inline void HKHubProcessorComponentDeallocate(CCComponent Component);

/*!
 * @brief Get the name of the hub.
 * @param Component The hub component.
 * @return The hub name.
 */
static inline CCString HKHubProcessorComponentGetName(CCComponent Component);

/*!
 * @brief Set the name of the hub.
 * @param Component The hub component.
 * @param Name The hub name. Ownership is transferred to the component.
 */
static inline void HKHubProcessorComponentSetName(CCComponent Component, CCString CC_OWN(Name));

/*!
 * @brief Get the processor of the hub.
 * @param Component The hub component.
 * @return The hub processor.
 */
static inline HKHubArchProcessor HKHubProcessorComponentGetProcessor(CCComponent Component);

/*!
 * @brief Set the processor of the hub.
 * @param Component The hub component.
 * @param Processor The hub processor. Ownership is transferred to the component.
 */
static inline void HKHubProcessorComponentSetProcessor(CCComponent Component, HKHubArchProcessor CC_OWN(Processor));


#pragma mark -

static inline void HKHubProcessorComponentInitialize(CCComponent Component, CCComponentID id)
{
    CCComponentInitialize(Component, id);
    ((HKHubProcessorComponentPrivate)Component)->name = 0;
    ((HKHubProcessorComponentPrivate)Component)->processor = NULL;
}

static inline void HKHubProcessorComponentDeallocate(CCComponent Component)
{
    if (((HKHubProcessorComponentPrivate)Component)->name) CCStringDestroy(((HKHubProcessorComponentPrivate)Component)->name);
    if (((HKHubProcessorComponentPrivate)Component)->processor) HKHubArchProcessorDestroy(((HKHubProcessorComponentPrivate)Component)->processor);
    CCComponentDeallocate(Component);
}

static inline CCString HKHubProcessorComponentGetName(CCComponent Component)
{
    return ((HKHubProcessorComponentPrivate)Component)->name;
}

static inline void HKHubProcessorComponentSetName(CCComponent Component, CCString Name)
{
    if (((HKHubProcessorComponentPrivate)Component)->name) CCStringDestroy(((HKHubProcessorComponentPrivate)Component)->name);
    
    ((HKHubProcessorComponentPrivate)Component)->name = Name;
}

static inline HKHubArchProcessor HKHubProcessorComponentGetProcessor(CCComponent Component)
{
    return ((HKHubProcessorComponentPrivate)Component)->processor;
}

static inline void HKHubProcessorComponentSetProcessor(CCComponent Component, HKHubArchProcessor Processor)
{
    if (((HKHubProcessorComponentPrivate)Component)->processor) HKHubArchProcessorDestroy(((HKHubProcessorComponentPrivate)Component)->processor);
    
    ((HKHubProcessorComponentPrivate)Component)->processor = Processor;
}

#endif
