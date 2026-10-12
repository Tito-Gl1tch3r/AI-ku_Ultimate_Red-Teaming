/*
 *  Copyright (c) 2018, Stefan Johnson
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

#ifndef HackingGame_ItemManualComponent_h
#define HackingGame_ItemManualComponent_h

#include "Base.h"
#include "SystemID.h"

#define HK_ITEM_MANUAL_COMPONENT_ID (0 | HK_ITEM_COMPONENT_FLAG) //TODO: Change ID

typedef struct {
    CC_COMPONENT_INHERIT(CCComponentClass);
    CCOrderedCollection(CCTextAttribute) name;
    CCOrderedCollection(CCTextAttribute) brief;
    CCOrderedCollection(CCTextAttribute) description;
} HKItemManualComponentClass, *HKItemManualComponentPrivate;

void HKItemManualComponentRegister(void);
void HKItemManualComponentDeregister(void);
void HKItemManualComponentDeserializer(CCComponent Component, CCExpression Arg, _Bool Deferred);

/*!
 * @brief Initialize the hub component.
 * @param Component The component to be initialized.
 * @param id The component ID.
 */
static inline void HKItemManualComponentInitialize(CCComponent Component, CCComponentID id);

/*!
 * @brief Deallocate the hub component.
 * @param Component The component to be deallocated.
 */
static inline void HKItemManualComponentDeallocate(CCComponent Component);

/*!
 * @brief Get the text attributes for the name of the item.
 * @param Component The item manual component.
 * @return The name text attributes.
 */
static inline CCOrderedCollection(CCTextAttribute) HKItemManualComponentGetName(CCComponent Component);

/*!
 * @brief Set the text attributes for name of the item.
 * @param Component The item manual component.
 * @param Name The text attributes for the item name. Ownership is transferred to the component.
 */
static inline void HKItemManualComponentSetName(CCComponent Component, CCOrderedCollection(CCTextAttribute) CC_OWN(Name));

/*!
 * @brief Get the text attributes for the brief of the item.
 * @param Component The item manual component.
 * @return The brief text attributes.
 */
static inline CCOrderedCollection(CCTextAttribute) HKItemManualComponentGetBrief(CCComponent Component);

/*!
 * @brief Set the text attributes for brief of the item.
 * @param Component The item manual component.
 * @param Brief The text attributes for the item brief. Ownership is transferred to the component.
 */
static inline void HKItemManualComponentSetBrief(CCComponent Component, CCOrderedCollection(CCTextAttribute) CC_OWN(Brief));

/*!
 * @brief Get the text attributes for the description of the item.
 * @param Component The item manual component.
 * @return The description text attributes.
 */
static inline CCOrderedCollection(CCTextAttribute) HKItemManualComponentGetDescription(CCComponent Component);

/*!
 * @brief Set the text attributes for description of the item.
 * @param Component The item manual component.
 * @param Description The text attributes for the item description. Ownership is transferred to the component.
 */
static inline void HKItemManualComponentSetDescription(CCComponent Component, CCOrderedCollection(CCTextAttribute) CC_OWN(Description));


#pragma mark -

static inline void HKItemManualComponentInitialize(CCComponent Component, CCComponentID id)
{
    CCComponentInitialize(Component, id);
    ((HKItemManualComponentPrivate)Component)->name = NULL;
    ((HKItemManualComponentPrivate)Component)->brief = NULL;
    ((HKItemManualComponentPrivate)Component)->description = NULL;
}

static inline void HKItemManualComponentDeallocate(CCComponent Component)
{
    if (((HKItemManualComponentPrivate)Component)->name) CCCollectionDestroy(((HKItemManualComponentPrivate)Component)->name);
    if (((HKItemManualComponentPrivate)Component)->brief) CCCollectionDestroy(((HKItemManualComponentPrivate)Component)->brief);
    if (((HKItemManualComponentPrivate)Component)->description) CCCollectionDestroy(((HKItemManualComponentPrivate)Component)->description);
    CCComponentDeallocate(Component);
}

static inline CCOrderedCollection(CCTextAttribute) HKItemManualComponentGetName(CCComponent Component)
{
    return ((HKItemManualComponentPrivate)Component)->name;
}

static inline void HKItemManualComponentSetName(CCComponent Component, CCOrderedCollection(CCTextAttribute) Name)
{
    if (((HKItemManualComponentPrivate)Component)->name) CCCollectionDestroy(((HKItemManualComponentPrivate)Component)->name);

    ((HKItemManualComponentPrivate)Component)->name = Name;
}

static inline CCOrderedCollection(CCTextAttribute) HKItemManualComponentGetBrief(CCComponent Component)
{
    return ((HKItemManualComponentPrivate)Component)->brief;
}

static inline void HKItemManualComponentSetBrief(CCComponent Component, CCOrderedCollection(CCTextAttribute) Brief)
{
    if (((HKItemManualComponentPrivate)Component)->brief) CCCollectionDestroy(((HKItemManualComponentPrivate)Component)->brief);
    
    ((HKItemManualComponentPrivate)Component)->brief = Brief;
}

static inline CCOrderedCollection(CCTextAttribute) HKItemManualComponentGetDescription(CCComponent Component)
{
    return ((HKItemManualComponentPrivate)Component)->description;
}

static inline void HKItemManualComponentSetDescription(CCComponent Component, CCOrderedCollection(CCTextAttribute) Description)
{
    if (((HKItemManualComponentPrivate)Component)->description) CCCollectionDestroy(((HKItemManualComponentPrivate)Component)->description);
    
    ((HKItemManualComponentPrivate)Component)->description = Description;
}

#endif
