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

#ifndef HackingGame_HubModuleWirelessTransceiverComponent_h
#define HackingGame_HubModuleWirelessTransceiverComponent_h

#include "Base.h"
#include "HubModuleComponent.h"
#include "HubModuleWirelessTransceiver.h"

#define HK_HUB_MODULE_WIRELESS_TRANSCEIVER_COMPONENT_ID (HK_HUB_MODULE_COMPONENT_ID | HKHubTypeModuleWirelessTransceiver)

typedef struct {
    CC_COMPONENT_INHERIT(HKHubModuleComponentClass);
    float range;
} HKHubModuleWirelessTransceiverComponentClass, *HKHubModuleWirelessTransceiverComponentPrivate;

extern const CCComponentExpressionDescriptor HKHubModuleWirelessTransceiverComponentDescriptor;

void HKHubModuleWirelessTransceiverComponentRegister(void);
void HKHubModuleWirelessTransceiverComponentDeregister(void);
void HKHubModuleWirelessTransceiverComponenDeserializer(CCComponent Component, CCExpression Arg, _Bool Deferred);

/*!
 * @brief Initialize the wireless transceiver module component.
 * @param Component The component to be initialized.
 * @param id The component ID.
 */
static inline void HKHubModuleWirelessTransceiverComponentInitialize(CCComponent Component, CCComponentID id);

/*!
 * @brief Deallocate the wireless transceiver module component.
 * @param Component The component to be deallocated.
 */
static inline void HKHubModuleWirelessTransceiverComponentDeallocate(CCComponent Component);

/*!
 * @brief Get the range of the wireless transceiver module.
 * @param Component The wireless transceiver module component.
 * @return The wireless transceiver module range.
 */
static inline float HKHubModuleWirelessTransceiverComponentGetRange(CCComponent Component);

/*!
 * @brief Set the range of the wireless transceiver module.
 * @param Component The wireless transceiver module component.
 * @param Range The wireless transceiver module range.
 */
static inline void HKHubModuleWirelessTransceiverComponentSetRange(CCComponent Component, float Range);

#pragma mark -

static inline void HKHubModuleWirelessTransceiverComponentInitialize(CCComponent Component, CCComponentID id)
{
    HKHubModuleComponentInitialize(Component, id);
    ((HKHubModuleWirelessTransceiverComponentPrivate)Component)->range = 0.0f;
    
    HKHubModuleComponentSetName(Component, CCStringCopy(CC_STRING("wireless transceiver")));
    HKHubModuleComponentSetModule(Component, HKHubModuleWirelessTransceiverCreate(CC_STD_ALLOCATOR));
}

static inline void HKHubModuleWirelessTransceiverComponentDeallocate(CCComponent Component)
{
    HKHubModuleComponentDeallocate(Component);
}

static inline float HKHubModuleWirelessTransceiverComponentGetRange(CCComponent Component)
{
    return ((HKHubModuleWirelessTransceiverComponentPrivate)Component)->range;
}

static inline void HKHubModuleWirelessTransceiverComponentSetRange(CCComponent Component, float Range)
{
    ((HKHubModuleWirelessTransceiverComponentPrivate)Component)->range = Range;
}

#endif
