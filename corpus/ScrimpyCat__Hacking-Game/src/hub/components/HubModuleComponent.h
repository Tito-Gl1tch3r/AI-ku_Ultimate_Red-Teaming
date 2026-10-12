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

#ifndef HackingGame_HubModuleComponent_h
#define HackingGame_HubModuleComponent_h

#include "Base.h"
#include "HubSystem.h"
#include "HubModule.h"

#define HK_HUB_MODULE_COMPONENT_ID (HKHubTypeModule | HK_HUB_COMPONENT_FLAG)

typedef struct {
    CC_COMPONENT_INHERIT(CCComponentClass);
    CCString name;
    HKHubModule module;
} HKHubModuleComponentClass, *HKHubModuleComponentPrivate;


void HKHubModuleComponentRegister(void);
void HKHubModuleComponentDeregister(void);

/*!
 * @brief Initialize the module component.
 * @param Component The component to be initialized.
 * @param id The component ID.
 */
static inline void HKHubModuleComponentInitialize(CCComponent Component, CCComponentID id);

/*!
 * @brief Deallocate the module component.
 * @param Component The component to be deallocated.
 */
static inline void HKHubModuleComponentDeallocate(CCComponent Component);

/*!
 * @brief Get the name of the module.
 * @param Component The module component.
 * @return The module name.
 */
static inline CCString HKHubModuleComponentGetName(CCComponent Component);

/*!
 * @brief Set the name of the module.
 * @param Component The module component.
 * @param Name The module name. Ownership is transferred to the component.
 */
static inline void HKHubModuleComponentSetName(CCComponent Component, CCString CC_OWN(Name));

/*!
 * @brief Get the module.
 * @param Component The module component.
 * @return The hub module.
 */
static inline HKHubModule HKHubModuleComponentGetModule(CCComponent Component);

/*!
 * @brief Set the module.
 * @param Component The module component.
 * @param Module The module. Ownership is transferred to the component.
 */
static inline void HKHubModuleComponentSetModule(CCComponent Component, HKHubModule CC_OWN(Module));


#pragma mark -

static inline void HKHubModuleComponentInitialize(CCComponent Component, CCComponentID id)
{
    CCComponentInitialize(Component, id);
    ((HKHubModuleComponentPrivate)Component)->name = 0;
    ((HKHubModuleComponentPrivate)Component)->module = NULL;
}

static inline void HKHubModuleComponentDeallocate(CCComponent Component)
{
    if (((HKHubModuleComponentPrivate)Component)->name) CCStringDestroy(((HKHubModuleComponentPrivate)Component)->name);
    if (((HKHubModuleComponentPrivate)Component)->module) HKHubModuleDestroy(((HKHubModuleComponentPrivate)Component)->module);
    CCComponentDeallocate(Component);
}

static inline CCString HKHubModuleComponentGetName(CCComponent Component)
{
    return ((HKHubModuleComponentPrivate)Component)->name;
}

static inline void HKHubModuleComponentSetName(CCComponent Component, CCString Name)
{
    if (((HKHubModuleComponentPrivate)Component)->name) CCStringDestroy(((HKHubModuleComponentPrivate)Component)->name);
    
    ((HKHubModuleComponentPrivate)Component)->name = Name;
}

static inline HKHubModule HKHubModuleComponentGetModule(CCComponent Component)
{
    return ((HKHubModuleComponentPrivate)Component)->module;
}

static inline void HKHubModuleComponentSetModule(CCComponent Component, HKHubModule Module)
{
    if (((HKHubModuleComponentPrivate)Component)->module) HKHubModuleDestroy(((HKHubModuleComponentPrivate)Component)->module);
    
    ((HKHubModuleComponentPrivate)Component)->module = Module;
}

#endif
