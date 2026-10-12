/*
 *  Copyright (c) 2019, Stefan Johnson
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

#ifndef HackingGame_HubPortConnectionComponent_h
#define HackingGame_HubPortConnectionComponent_h

#include "Base.h"
#include "HubArchPort.h"
#include "HubSystem.h"

#define HK_HUB_PORT_CONNECTION_COMPONENT_ID (HKHubTypePortConnection | HK_HUB_COMPONENT_FLAG)

typedef struct {
    CCEntity entity;
    HKHubArchPortID port;
} HKHubPortConnectionEntityMapping;

typedef struct {
    CC_COMPONENT_INHERIT(CCComponentClass);
    HKHubArchPortConnection connection;
    HKHubPortConnectionEntityMapping mapping[2];
    _Bool disconnectable;
} HKHubPortConnectionComponentClass, *HKHubPortConnectionComponentPrivate;


void HKHubPortConnectionComponentRegister(void);
void HKHubPortConnectionComponentDeregister(void);
void HKHubPortConnectionComponentDeserializer(CCComponent Component, CCExpression Arg, _Bool Deferred);

/*!
 * @brief Initialize the port connection component.
 * @param Component The component to be initialized.
 * @param id The component ID.
 */
static inline void HKHubPortConnectionComponentInitialize(CCComponent Component, CCComponentID id);

/*!
 * @brief Deallocate the port connection component.
 * @param Component The component to be deallocated.
 */
static inline void HKHubPortConnectionComponentDeallocate(CCComponent Component);

/*!
 * @brief Get the connection of the port connection.
 * @param Component The port connection component.
 * @return The connection.
 */
static inline HKHubArchPortConnection HKHubPortConnectionComponentGetConnection(CCComponent Component);

/*!
 * @brief Set the connection of the port connection.
 * @param Component The port connection component.
 * @param Connection The connection. Ownership is transferred to the component.
 */
static inline void HKHubPortConnectionComponentSetConnection(CCComponent Component, HKHubArchPortConnection CC_OWN(Connection));

/*!
 * @brief Get the entity mapping of the port connection.
 * @param Component The port connection component.
 * @return The two entity mappings.
 */
static inline const HKHubPortConnectionEntityMapping *HKHubPortConnectionComponentGetEntityMapping(CCComponent Component);

/*!
 * @brief Set the entity mapping of the port connection.
 * @param Component The port connection component.
 * @param Device1 The entity mapping for the first device. Ownership is transferred to the component.
 * @param Device2 The entity mapping for the second device. Ownership is transferred to the component.
 */
static inline void HKHubPortConnectionComponentSetEntityMapping(CCComponent Component, HKHubPortConnectionEntityMapping CC_OWN(Device1), HKHubPortConnectionEntityMapping CC_OWN(Device2));

/*!
 * @brief Get whether the connection can be disconnected.
 * @param Component The port connection component.
 * @return Whether the connection can be disconnected.
 */
static inline _Bool HKHubPortConnectionComponentGetDisconnectable(CCComponent Component);

/*!
 * @brief Set whether the connection can be disconnected.
 * @param Component The port connection component.
 * @param Disconnectable Whether the connection can be disconnected (TRUE) or not (FALSE).
 */
static inline void HKHubPortConnectionComponentSetDisconnectable(CCComponent Component, _Bool Disconnectable);


#pragma mark -

static inline void HKHubPortConnectionComponentInitialize(CCComponent Component, CCComponentID id)
{
    CCComponentInitialize(Component, id);
    ((HKHubPortConnectionComponentPrivate)Component)->connection = NULL;
    ((HKHubPortConnectionComponentPrivate)Component)->mapping[0] = (HKHubPortConnectionEntityMapping){ .entity = NULL };
    ((HKHubPortConnectionComponentPrivate)Component)->mapping[1] = (HKHubPortConnectionEntityMapping){ .entity = NULL };
    ((HKHubPortConnectionComponentPrivate)Component)->disconnectable = FALSE;
}

static inline void HKHubPortConnectionComponentDeallocate(CCComponent Component)
{
    if (((HKHubPortConnectionComponentPrivate)Component)->connection)
    {
        HKHubArchPortConnectionDisconnect(((HKHubPortConnectionComponentPrivate)Component)->connection);
        HKHubArchPortConnectionDestroy(((HKHubPortConnectionComponentPrivate)Component)->connection);
    }
    
    if (((HKHubPortConnectionComponentPrivate)Component)->mapping[0].entity) CCEntityDestroy(((HKHubPortConnectionComponentPrivate)Component)->mapping[0].entity);
    if (((HKHubPortConnectionComponentPrivate)Component)->mapping[1].entity) CCEntityDestroy(((HKHubPortConnectionComponentPrivate)Component)->mapping[1].entity);
    
    CCComponentDeallocate(Component);
}

static inline HKHubArchPortConnection HKHubPortConnectionComponentGetConnection(CCComponent Component)
{
    return ((HKHubPortConnectionComponentPrivate)Component)->connection;
}

static inline void HKHubPortConnectionComponentSetConnection(CCComponent Component, HKHubArchPortConnection Connection)
{
    CCAssertLog(!((HKHubPortConnectionComponentPrivate)Component)->connection, "Port connection components cannot be re-set");
    
    ((HKHubPortConnectionComponentPrivate)Component)->connection = Connection;
}

static inline const HKHubPortConnectionEntityMapping *HKHubPortConnectionComponentGetEntityMapping(CCComponent Component)
{
    return ((HKHubPortConnectionComponentPrivate)Component)->mapping;
}

static inline void HKHubPortConnectionComponentSetEntityMapping(CCComponent Component, HKHubPortConnectionEntityMapping Device1, HKHubPortConnectionEntityMapping Device2)
{
    CCAssertLog(!((HKHubPortConnectionComponentPrivate)Component)->mapping[0].entity, "Port connection components cannot be re-set");
    CCAssertLog(!((HKHubPortConnectionComponentPrivate)Component)->mapping[1].entity, "Port connection components cannot be re-set");
    CCAssertLog(Device1.entity && Device2.entity, "Device entities must not be null");
    
    ((HKHubPortConnectionComponentPrivate)Component)->mapping[0] = Device1;
    ((HKHubPortConnectionComponentPrivate)Component)->mapping[1] = Device2;
}

static inline _Bool HKHubPortConnectionComponentGetDisconnectable(CCComponent Component)
{
    return ((HKHubPortConnectionComponentPrivate)Component)->disconnectable;
}

static inline void HKHubPortConnectionComponentSetDisconnectable(CCComponent Component, _Bool Disconnectable)
{
    ((HKHubPortConnectionComponentPrivate)Component)->disconnectable = Disconnectable;
}

#endif
