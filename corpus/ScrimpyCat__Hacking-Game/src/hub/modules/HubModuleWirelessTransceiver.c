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

#include "HubModuleWirelessTransceiver.h"

#define HK_HUB_MODULE_WIRELESS_TRANSCEIVER_RECEIVE_WAIT 8
#define HK_HUB_MODULE_WIRELESS_TRANSCEIVER_PACKET_LIFETIME 4

#if DEBUG
size_t HKHubModuleWirelessTransceiverReceiveWait = HK_HUB_MODULE_WIRELESS_TRANSCEIVER_RECEIVE_WAIT;
size_t HKHubModuleWirelessTransceiverPacketLifetime = HK_HUB_MODULE_WIRELESS_TRANSCEIVER_PACKET_LIFETIME;
#undef HK_HUB_MODULE_WIRELESS_TRANSCEIVER_RECEIVE_WAIT
#undef HK_HUB_MODULE_WIRELESS_TRANSCEIVER_PACKET_LIFETIME
#define HK_HUB_MODULE_WIRELESS_TRANSCEIVER_RECEIVE_WAIT HKHubModuleWirelessTransceiverReceiveWait
#define HK_HUB_MODULE_WIRELESS_TRANSCEIVER_PACKET_LIFETIME HKHubModuleWirelessTransceiverPacketLifetime
#endif

typedef struct {
    CCDictionary(HKHubModuleWirelessTransceiverPacketSignature, uint8_t) packets;
    size_t prevGlobalTimestamp;
} HKHubModuleWirelessTransceiverState;


HKHubModuleWirelessTransceiverBroadcastCallback HKHubModuleWirelessTransceiverBroadcast = NULL;
HKHubModuleWirelessTransceiverGetSchedulerCallback HKHubModuleWirelessTransceiverGetScheduler = NULL;

static HKHubArchPortResponse HKHubModuleWirelessTransceiverTransmit(HKHubArchPortConnection Connection, HKHubModule Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    const HKHubArchPort *OppositePort = HKHubArchPortConnectionGetOppositePort(Connection, Device, Port);
    
    if (HKHubArchPortIsReady(OppositePort))
    {
        if (Message->size >= 1)
        {
            HKHubModuleWirelessTransceiverBroadcast(Device, (HKHubModuleWirelessTransceiverPacket){
                .sig = { .channel = Port, .timestamp = Timestamp - ((Message->size * HKHubArchProcessorSpeedMemoryRead) + (Message->size * HKHubArchProcessorSpeedPortTransmission)) },
                .data = Message->memory[Message->offset]
            });
        }
    }
    
    return HKHubArchPortResponseSuccess;
}

static HKHubArchPortResponse HKHubModuleWirelessTransceiverReceive(HKHubArchPortConnection Connection, HKHubModule Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchProcessor ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    /*
     Timestamp is compared against global timestamp to make sure receive will only occur once all transmits have been performed. The
     8 is due to the smallest recv requiring 8 cycles, while the smallest send (send r, r, [r]) that can successfully transmit is 9
     cycles.
     */
    const size_t GlobalTimestamp = HKHubArchSchedulerGetTimestamp(HKHubModuleWirelessTransceiverGetScheduler(Device));
    if ((Timestamp + 8) < GlobalTimestamp)
    {
        if (((HKHubModuleWirelessTransceiverState*)Device->internal)->prevGlobalTimestamp == GlobalTimestamp) return  HKHubArchPortResponseDefer;
        
        ((HKHubModuleWirelessTransceiverState*)Device->internal)->prevGlobalTimestamp = GlobalTimestamp;
        return HKHubArchPortResponseRetry;
    }
    
    CCDictionary(HKHubModuleWirelessTransceiverPacketSignature, uint8_t) Packets = ((HKHubModuleWirelessTransceiverState*)Device->internal)->packets;
    for (size_t Loop = 0; Loop < HK_HUB_MODULE_WIRELESS_TRANSCEIVER_RECEIVE_WAIT; Loop++)
    {
        uint8_t *Data = CCDictionaryGetValue(Packets, &(HKHubModuleWirelessTransceiverPacketSignature){ .timestamp = Timestamp - Loop, .channel = Port });
        
        if (Data)
        {
            *Message = (HKHubArchPortMessage){
                .memory = Data,
                .offset = 0,
                .size = 1
            };
            
            if (!HKHubArchPortIsReady(HKHubArchPortConnectionGetOppositePort(Connection, Device, Port))) return HKHubArchPortResponseDefer;
            
            return HKHubArchPortResponseSuccess;
        }
    }
    
    return HKHubArchPortResponseTimeout;
}

static CC_FORCE_INLINE CC_CONSTANT_FUNCTION size_t HKHubModuleWirelessTransceiverPacketSignatureTimestampLifetime(size_t Timestamp)
{
    return Timestamp / HK_HUB_MODULE_WIRELESS_TRANSCEIVER_PACKET_LIFETIME;
}

static uintmax_t HKHubModuleWirelessTransceiverPacketSignatureHasher(const HKHubModuleWirelessTransceiverPacketSignature *Sig)
{
    return HKHubModuleWirelessTransceiverPacketSignatureTimestampLifetime(Sig->timestamp) ^ ((uintmax_t)Sig->channel << ((sizeof(uintmax_t) * 8) - 8));
}

static CCComparisonResult HKHubModuleWirelessTransceiverPacketSignatureComparator(const HKHubModuleWirelessTransceiverPacketSignature *left, const HKHubModuleWirelessTransceiverPacketSignature *right)
{
    return (left->channel == right->channel) && (HKHubModuleWirelessTransceiverPacketSignatureTimestampLifetime(left->timestamp) == HKHubModuleWirelessTransceiverPacketSignatureTimestampLifetime(right->timestamp)) ? CCComparisonResultEqual : CCComparisonResultInvalid;
}

static void HKHubModuleWirelessTransceiverStateDestructor(HKHubModuleWirelessTransceiverState *State)
{
    CCDictionaryDestroy(State->packets);
    CCFree(State);
}

HKHubModule HKHubModuleWirelessTransceiverCreate(CCAllocatorType Allocator)
{
    HKHubModuleWirelessTransceiverState *State = CCMalloc(Allocator, sizeof(HKHubModuleWirelessTransceiverState), NULL, CC_DEFAULT_ERROR_CALLBACK);
    if (State)
    {
        *State = (HKHubModuleWirelessTransceiverState){
            .packets = CCDictionaryCreate(Allocator, CCDictionaryHintHeavyFinding | CCDictionaryHintHeavyInserting | CCDictionaryHintHeavyDeleting, sizeof(HKHubModuleWirelessTransceiverPacketSignature), sizeof(uint8_t), &(CCDictionaryCallbacks){
                .getHash = (CCDictionaryKeyHasher)HKHubModuleWirelessTransceiverPacketSignatureHasher,
                .compareKeys = (CCComparator)HKHubModuleWirelessTransceiverPacketSignatureComparator
            }),
            .prevGlobalTimestamp = 0
        };
        
        return HKHubModuleCreate(Allocator, (HKHubArchPortTransmit)HKHubModuleWirelessTransceiverReceive, (HKHubArchPortTransmit)HKHubModuleWirelessTransceiverTransmit, State, (HKHubModuleDataDestructor)HKHubModuleWirelessTransceiverStateDestructor, CCDataContainerCreate(Allocator, CCDataHintReadWrite, sizeof(uint8_t), (CCDataContainerCount)CCDictionaryGetCount, (CCDataContainerEnumerable)CCDictionaryGetValueEnumerable, State->packets, NULL, NULL));
    }
    
    else CC_LOG_ERROR("Failed to create wireless transceiver module due to allocation failure: allocation of size (%zu)", sizeof(HKHubModuleWirelessTransceiverState));
    
    return NULL;
}

void HKHubModuleWirelessTransceiverReceivePacket(HKHubModule Module, HKHubModuleWirelessTransceiverPacket Packet)
{
    CCAssertLog(Module, "Module must not be null");
    
    CCDictionary(HKHubModuleWirelessTransceiverPacketSignature, uint8_t) Packets = ((HKHubModuleWirelessTransceiverState*)Module->internal)->packets;
    CCDictionaryEntry Entry = CCDictionaryEntryForKey(Packets, &Packet.sig);
    
    if (CCDictionaryEntryIsInitialized(Packets, Entry))
    {
        Packet.data ^= *(uint8_t*)CCDictionaryGetEntry(Packets, Entry);
    }
    
    CCDictionarySetEntry(Packets, Entry, &Packet.data);
}

_Bool HKHubModuleWirelessTransceiverInspectPacket(HKHubModule Module, HKHubModuleWirelessTransceiverPacketSignature Sig, uint8_t *Data)
{
    CCAssertLog(Module, "Module must not be null");
    
    CCDictionary(HKHubModuleWirelessTransceiverPacketSignature, uint8_t) Packets = ((HKHubModuleWirelessTransceiverState*)Module->internal)->packets;
    CCDictionaryEntry Entry = CCDictionaryFindKey(Packets, &Sig);
    
    if ((Entry) && (Data)) *Data = *(uint8_t*)CCDictionaryGetEntry(Packets, Entry);
    
    return Entry;
}

void HKHubModuleWirelessTransceiverPacketPurge(HKHubModule Module, size_t Timestamp)
{
    CCAssertLog(Module, "Module must not be null");
    
    ((HKHubModuleWirelessTransceiverState*)Module->internal)->prevGlobalTimestamp = 0;
    
    CCDictionary(HKHubModuleWirelessTransceiverPacketSignature, uint8_t) Packets = ((HKHubModuleWirelessTransceiverState*)Module->internal)->packets;
    CCOrderedCollection(HKHubModuleWirelessTransceiverPacketSignature) Keys = CCDictionaryGetKeys(Packets);
    
    CC_COLLECTION_FOREACH_PTR(HKHubModuleWirelessTransceiverPacketSignature, Sig, Keys)
    {
        if (HKHubModuleWirelessTransceiverPacketSignatureTimestampLifetime(Sig->timestamp) >= HKHubModuleWirelessTransceiverPacketSignatureTimestampLifetime(Timestamp)) CCDictionaryRemoveValue(Packets, Sig);
    }
    
    CCCollectionDestroy(Keys);
}

void HKHubModuleWirelessTransceiverShiftTimestamps(HKHubModule Module, size_t Shift)
{
    CCAssertLog(Module, "Module must not be null");
    
    CCDictionary(HKHubModuleWirelessTransceiverPacketSignature, uint8_t) Packets = ((HKHubModuleWirelessTransceiverState*)Module->internal)->packets;
    CCDictionary(HKHubModuleWirelessTransceiverPacketSignature, uint8_t) ShiftedPackets = CCDictionaryCreate(Packets->allocator, CCDictionaryHintHeavyFinding | CCDictionaryHintHeavyInserting | CCDictionaryHintHeavyDeleting, Packets->keySize, Packets->valueSize, &Packets->callbacks);
    
    CCOrderedCollection(HKHubModuleWirelessTransceiverPacketSignature) Keys = CCDictionaryGetKeys(Packets);
    
    CC_COLLECTION_FOREACH(HKHubModuleWirelessTransceiverPacketSignature, Sig, Keys)
    {
        uint8_t *Value = CCDictionaryGetValue(Packets, &Sig);
        Sig.timestamp += Shift;
        CCDictionarySetValue(ShiftedPackets, &Sig, Value);
    }
    
    CCCollectionDestroy(Keys);
    
    CCDictionaryDestroy(Packets);
    
    ((HKHubModuleWirelessTransceiverState*)Module->internal)->packets = ShiftedPackets;
    
    CCData Memory = HKHubModuleGetMemory(Module);
    Module->memory = CCDataContainerCreate(Memory->allocator, CCDataGetHints(Memory), sizeof(uint8_t), (CCDataContainerCount)CCDictionaryGetCount, (CCDataContainerEnumerable)CCDictionaryGetValueEnumerable, ShiftedPackets, NULL, NULL);
    CCDataDestroy(Memory);
}
