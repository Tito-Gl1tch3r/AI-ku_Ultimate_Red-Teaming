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

#ifndef HackingGame_HubModuleDisplayComponent_h
#define HackingGame_HubModuleDisplayComponent_h

#include "Base.h"
#include "HubModuleComponent.h"
#include "HubModuleDisplay.h"

#define HK_HUB_MODULE_DISPLAY_COMPONENT_ID (HK_HUB_MODULE_COMPONENT_ID | HKHubTypeModuleDisplay)

typedef struct {
    CC_COMPONENT_INHERIT(HKHubModuleComponentClass);
    CCVector2Di resolution;
    HKHubModuleDisplayBufferConverter encoder;
} HKHubModuleDisplayComponentClass, *HKHubModuleDisplayComponentPrivate;

extern const CCComponentExpressionDescriptor HKHubModuleDisplayComponentDescriptor;

void HKHubModuleDisplayComponentRegister(void);
void HKHubModuleDisplayComponentDeregister(void);
void HKHubModuleDisplayComponenDeserializer(CCComponent Component, CCExpression Arg, _Bool Deferred);

/*!
 * @brief Initialize the display module component.
 * @param Component The component to be initialized.
 * @param id The component ID.
 */
static inline void HKHubModuleDisplayComponentInitialize(CCComponent Component, CCComponentID id);

/*!
 * @brief Deallocate the display module component.
 * @param Component The component to be deallocated.
 */
static inline void HKHubModuleDisplayComponentDeallocate(CCComponent Component);

/*!
 * @brief Get the resolution of the display module.
 * @param Component The display module component.
 * @return The display module resolution.
 */
static inline CCVector2Di HKHubModuleDisplayComponentGetResolution(CCComponent Component);

/*!
 * @brief Set the resolution of the display module.
 * @param Component The display module component.
 * @param Resolution The display module resolution.
 */
static inline void HKHubModuleDisplayComponentSetResolution(CCComponent Component, CCVector2Di Resolution);

/*!
 * @brief Get the buffer encoder for the display module.
 * @param Component The display module component.
 * @return The display module buffer encoder.
 */
static inline HKHubModuleDisplayBufferConverter HKHubModuleDisplayComponentGetEncoder(CCComponent Component);

/*!
 * @brief Set the buffer encoder of the display module.
 * @param Component The display module component.
 * @param Encoder The display module buffer encoder.
 */
static inline void HKHubModuleDisplayComponentSetEncoder(CCComponent Component, HKHubModuleDisplayBufferConverter Encoder);

#pragma mark -

static inline void HKHubModuleDisplayComponentInitialize(CCComponent Component, CCComponentID id)
{
    HKHubModuleComponentInitialize(Component, id);
    
    HKHubModuleComponentSetName(Component, CCStringCopy(CC_STRING("display")));
    HKHubModuleComponentSetModule(Component, HKHubModuleDisplayCreate(CC_STD_ALLOCATOR));
    HKHubModuleDisplayComponentSetResolution(Component, (CCVector2Di){ 16, 16 });
    HKHubModuleDisplayComponentSetEncoder(Component, HKHubModuleDisplayBuffer_UniformColourRGB888);
}

static inline void HKHubModuleDisplayComponentDeallocate(CCComponent Component)
{
    HKHubModuleComponentDeallocate(Component);
}

static inline CCVector2Di HKHubModuleDisplayComponentGetResolution(CCComponent Component)
{
    return ((HKHubModuleDisplayComponentPrivate)Component)->resolution;
}

static inline void HKHubModuleDisplayComponentSetResolution(CCComponent Component, CCVector2Di Resolution)
{
    CCAssertLog(Resolution.x * Resolution.y == 256, "Resolution must cover 256 pixels");
    
    ((HKHubModuleDisplayComponentPrivate)Component)->resolution = Resolution;
}

static inline HKHubModuleDisplayBufferConverter HKHubModuleDisplayComponentGetEncoder(CCComponent Component)
{
    return ((HKHubModuleDisplayComponentPrivate)Component)->encoder;
}

static inline void HKHubModuleDisplayComponentSetEncoder(CCComponent Component, HKHubModuleDisplayBufferConverter Encoder)
{
    ((HKHubModuleDisplayComponentPrivate)Component)->encoder = Encoder;
}

#endif
