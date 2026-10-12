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

#ifndef HackingGame_HubModule_h
#define HackingGame_HubModule_h

#include "HubArchPort.h"

/*!
 * @brief The module.
 * @description Allows @b CCRetain.
 */
typedef struct HKHubModuleInfo *HKHubModule;

/*!
 * @brief Callback to hook any port connection changes.
 * @param Module The module whose port changed.
 * @param Port The port of the module that was changed.
 */
typedef void (*HKHubModuleDebugPortConnectionChangeCallback)(HKHubModule Module, HKHubArchPortID Port);

/*!
 * @brief Callback to destroy the internal data.
 */
typedef void (*HKHubModuleDataDestructor)(void *Internal);

typedef struct HKHubModuleInfo {
    void *internal;
    CCDictionary(HKHubArchPortID, HKHubArchPortConnection) ports;
    HKHubArchPortTransmit send;
    HKHubArchPortTransmit receive;
    HKHubModuleDataDestructor destructor;
    CCData memory;
    struct {
        void *context;
        uintptr_t extra;
        HKHubModuleDebugPortConnectionChangeCallback portConnectionChange;
    } debug;
} HKHubModuleInfo;


/*!
 * @brief Create a module.
 * @param Allocator The allocator to be used.
 * @param Send The sender.
 * @param Receive The receiver.
 * @param Internal The internal data.
 * @param Destructor The destructor for the internal data.
 * @param Memory The addressable memory of the module. Ownership is passed to the module.
 * @return The module. Must be destroyed to free memory.
 */
CC_NEW HKHubModule HKHubModuleCreate(CCAllocatorType Allocator, HKHubArchPortTransmit Send, HKHubArchPortTransmit Receive, void *Internal, HKHubModuleDataDestructor Destructor, CCData CC_OWN(Memory));

/*!
 * @brief Destroy a module.
 * @param Module The module to be destroyed.
 */
void HKHubModuleDestroy(HKHubModule CC_DESTROY(Module));

/*!
 * @brief Add a connection to the module.
 * @param Module The module to add the connection to.
 * @param Port The port of the module the connection belongs to.
 * @param Connection The connection to add to the module. A reference to the connection is
 *        retained.
 */
void HKHubModuleConnect(HKHubModule Module, HKHubArchPortID Port, HKHubArchPortConnection CC_RETAIN(Connection));

/*!
 * @brief Disconnect a connection from the module.
 * @description Causes the connection to be disconnected completely from either interface.
 * @param Module The module to remove the connection from.
 * @param Port The port of the module the connection belongs to.
 */
void HKHubModuleDisconnect(HKHubModule Module, HKHubArchPortID Port);

/*!
 * @brief Get an interfaceable port reference from the module.
 * @param Module The module to get the port of.
 * @param Port The port of the module.
 * @return The port interface.
 */
HKHubArchPort HKHubModuleGetPort(HKHubModule Module, HKHubArchPortID Port);

/*!
 * @brief Get the current connection for the specified port of the module.
 * @param Module The module to get the connection of.
 * @param Port The port of the module.
 * @return The connection if one exists, otherwise NULL.
 */
HKHubArchPortConnection HKHubModuleGetPortConnection(HKHubModule Module, HKHubArchPortID Port);

/*!
 * @brief Get the memory for the module.
 * @param Module The module to get the memory of.
 * @return The memory if any exists, otherwise NULL.
 */
static CC_FORCE_INLINE CCData HKHubModuleGetMemory(HKHubModule Module);

#pragma mark -

static CC_FORCE_INLINE CCData HKHubModuleGetMemory(HKHubModule Module)
{
    CCAssertLog(Module, "Module must not be null");
    
    return Module->memory;
}

#endif
