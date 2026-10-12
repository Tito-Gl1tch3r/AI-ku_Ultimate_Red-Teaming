/*
 *  Copyright (c) 2020, Stefan Johnson
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

#ifndef HackingGame_HubModuleDebugController_h
#define HackingGame_HubModuleDebugController_h

#include "HubModule.h"
#include "HubArchProcessor.h"

#define HK_HUB_MODULE_DEBUG_CONTROLLER_QUERY_PORT 0x80

#if DEBUG
extern size_t HKHubModuleDebugControllerEventBufferMax;
#endif

/*!
 * @brief Create a debug controller module.
 * @param Allocator The allocator to be used.
 * @return The debug controller module. Must be destroyed to free memory.
 */
CC_NEW HKHubModule HKHubModuleDebugControllerCreate(CCAllocatorType Allocator);

/*!
 * @brief Connect the debug controller to the processor.
 * @param Controller The debug controller.
 * @param Processor The processor to be connected to.
 * @param Name The name of the processor. May be null.
 */
void HKHubModuleDebugControllerConnectProcessor(HKHubModule Controller, HKHubArchProcessor Processor, CCString CC_COPY(Name));

/*!
 * @brief Disconnect the debug controller from the processor.
 * @param Controller The debug controller.
 * @param Processor The processor to be disconnected from.
 */
void HKHubModuleDebugControllerDisconnectProcessor(HKHubModule Controller, HKHubArchProcessor Processor);

/*!
 * @brief Connect the debug controller to the module.
 * @param Controller The debug controller.
 * @param Module The module to be connected to.
 * @param Name The name of the module. May be null.
 */
void HKHubModuleDebugControllerConnectModule(HKHubModule Controller, HKHubModule Module, CCString CC_COPY(Name));

/*!
 * @brief Disconnect the debug controller from the processor.
 * @param Controller The debug controller.
 * @param Module The module to be disconnected from.
 */
void HKHubModuleDebugControllerDisconnectModule(HKHubModule Controller, HKHubModule Module);

#endif
