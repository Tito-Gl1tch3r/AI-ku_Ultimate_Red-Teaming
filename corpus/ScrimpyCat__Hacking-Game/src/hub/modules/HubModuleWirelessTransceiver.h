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

#ifndef HackingGame_HubModuleWirelessTransceiver_h
#define HackingGame_HubModuleWirelessTransceiver_h

#include "HubModule.h"
#include "HubArchScheduler.h"

typedef struct {
    size_t timestamp;
    uint8_t channel;
} HKHubModuleWirelessTransceiverPacketSignature;

typedef struct {
    HKHubModuleWirelessTransceiverPacketSignature sig;
    uint8_t data;
} HKHubModuleWirelessTransceiverPacket;

/*!
 * @brief Callback to handle broadcasting of packets.
 * @description Handle the sharing of trasmitted packet to other transceivers.
 * @param Transmitter The wireless transceiver module that the transmission is originating from.
 * @param Packet The packet being transmitted.
 */
typedef void (*HKHubModuleWirelessTransceiverBroadcastCallback)(HKHubModule Transmitter, HKHubModuleWirelessTransceiverPacket Packet);

/*!
 * @brief Callback to get the scheduler managing these devices.
 * @param Module The wireless transceiver module to get the scheduler of.
 * @return The hub scheduler.
 */
typedef HKHubArchScheduler (*HKHubModuleWirelessTransceiverGetSchedulerCallback)(HKHubModule Module);

/*!
 * @brief Set the broadcaster for when a module transmits a packet.
 */
extern HKHubModuleWirelessTransceiverBroadcastCallback HKHubModuleWirelessTransceiverBroadcast;

/*!
 * @brief Set the scheduler for when a module is querying its scheduler.
 */
extern HKHubModuleWirelessTransceiverGetSchedulerCallback HKHubModuleWirelessTransceiverGetScheduler;

#if DEBUG
extern size_t HKHubModuleWirelessTransceiverReceiveWait;
extern size_t HKHubModuleWirelessTransceiverPacketLifetime;
#endif

/*!
 * @brief Create a wireless transceiver module.
 * @param Allocator The allocator to be used.
 * @return The wireless transceiver module. Must be destroyed to free memory.
 */
CC_NEW HKHubModule HKHubModuleWirelessTransceiverCreate(CCAllocatorType Allocator);

/*!
 * @brief Add a packet to the transceiver.
 * @param Module The wireless transceiver.
 * @param Packet The packet that should be received by the transceiver.
 */
void HKHubModuleWirelessTransceiverReceivePacket(HKHubModule Module, HKHubModuleWirelessTransceiverPacket Packet);

/*!
 * @brief Inspect the given packet timestamp.
 * @param Module The wireless transceiver.
 * @param Sig The packet signature.
 * @param Data The current data of that packet. Only written to if the packet exists. May be null.
 * @return TRUE if there is currently a packet for the given signature, otherwise FALSE.
 */
_Bool HKHubModuleWirelessTransceiverInspectPacket(HKHubModule Module, HKHubModuleWirelessTransceiverPacketSignature Sig, uint8_t *Data);

/*!
 * @brief Purge the received packets at the timestamp and older.
 * @param Module The wireless transceiver.
 * @param Timestamp The timestamp to purge up to (and including). To purge every packet, 0 can be
 *        used to guarantee that.
 */
void HKHubModuleWirelessTransceiverPacketPurge(HKHubModule Module, size_t Timestamp);

/*!
 * @brief Shift the current timestamps of the received packets by a certain amount.
 * @param Module The wireless transceiver.
 * @param Shift The amount to shift the timestamps by.
 */
void HKHubModuleWirelessTransceiverShiftTimestamps(HKHubModule Module, size_t Shift);

#endif
