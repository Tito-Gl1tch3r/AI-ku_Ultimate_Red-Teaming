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

#import <XCTest/XCTest.h>
#import "ProgramHTPDecoderTests.h"

@interface ProgramHTP4DecoderTests : ProgramHTPDecoderTests

@end

@implementation ProgramHTP4DecoderTests

-(const char*) program
{
    return "assets/logic/programs/htp4_decoder.chasm";
}

-(void) testDecodingPacket
{
    uint8_t Data[] = {
        224, 163, 144, 98, 80, 49, 47, 31 // 4 bit htp
    };
    
    self.encodedPackets = Data;
    self.encodedPacketCount = sizeof(Data) / sizeof(typeof(*Data));
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(self.encodedPacketIndex, self.encodedPacketCount, @"Should consume all incoming packets");
    
    CCQueueNode *Node = CCQueuePop(self.decodedPackets);
    XCTAssertNotEqual(Node, NULL, @"Should have a decoded packet");
    if (Node)
    {
        Packet *P = CCQueueGetNodeData(Node);
        XCTAssertEqual(P->size, 3, @"Should have the correct size");
        XCTAssertEqual(P->data[0], 2, @"Should have the correct data");
        XCTAssertEqual(P->data[1], 1, @"Should have the correct data");
        XCTAssertEqual(P->data[2], 0xff, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(self.decodedPackets);
    XCTAssertEqual(Node, NULL, @"Should not have anymore decoded packets");
}

-(void) testDecodingPacketSeries
{
    uint8_t Data[] = {
        224, 163, 144, 98, 80, 49, 47, 31,
        224, 163, 144, 98, 80, 49, 47, 31,
        224, 163, 144, 98, 80, 49, 47, 31,
        224, 163, 144, 98, 80, 49, 47, 31,
        224, 163, 144, 98, 80, 49, 47, 31,
        224, 163, 144, 98, 80, 49, 47, 31,
        224, 163, 144, 98, 80, 49, 47, 31,
        224, 163, 144, 98, 80, 49, 47, 31,
    };
    
    self.encodedPackets = Data;
    self.encodedPacketCount = sizeof(Data) / sizeof(typeof(*Data));
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(self.encodedPacketIndex, self.encodedPacketCount, @"Should consume all incoming packets");
    
    CCQueueNode *Node;
    for (size_t Loop = 0; Loop < 8; Loop++)
    {
        Node = CCQueuePop(self.decodedPackets);
        XCTAssertNotEqual(Node, NULL, @"Should have a decoded packet");
        if (Node)
        {
            Packet *P = CCQueueGetNodeData(Node);
            XCTAssertEqual(P->size, 3, @"Should have the correct size");
            XCTAssertEqual(P->data[0], 2, @"Should have the correct data");
            XCTAssertEqual(P->data[1], 1, @"Should have the correct data");
            XCTAssertEqual(P->data[2], 0xff, @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    Node = CCQueuePop(self.decodedPackets);
    XCTAssertEqual(Node, NULL, @"Should not have anymore decoded packets");
}

-(void) testDecodingInterleavedPackets
{
    uint8_t Data[] = {
        224, 163, 224, 163, 144, 144, 98, 80, 49, 47, 98, 80, 49, 31, 47, 31
    };
    
    self.encodedPackets = Data;
    self.encodedPacketCount = sizeof(Data) / sizeof(typeof(*Data));
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(self.encodedPacketIndex, self.encodedPacketCount, @"Should consume all incoming packets");
    
    CCQueueNode *Node;
    for (size_t Loop = 0; Loop < 2; Loop++)
    {
        Node = CCQueuePop(self.decodedPackets);
        XCTAssertNotEqual(Node, NULL, @"Should have a decoded packet");
        if (Node)
        {
            Packet *P = CCQueueGetNodeData(Node);
            XCTAssertEqual(P->size, 3, @"Should have the correct size");
            XCTAssertEqual(P->data[0], 2, @"Should have the correct data");
            XCTAssertEqual(P->data[1], 1, @"Should have the correct data");
            XCTAssertEqual(P->data[2], 0xff, @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    Node = CCQueuePop(self.decodedPackets);
    XCTAssertEqual(Node, NULL, @"Should not have anymore decoded packets");
}

-(void) testDecodingPacketsMixed
{
    uint8_t Data[] = {
        96, 65, 48, 17,
        112, 81, 64, 18,
        128, 97, 80, 19
    };
    
    self.encodedPackets = Data;
    self.encodedPacketCount = sizeof(Data) / sizeof(typeof(*Data));
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(self.encodedPacketIndex, self.encodedPacketCount, @"Should consume all incoming packets");
    
    CCQueueNode *Node;
    for (size_t Loop = 0; Loop < 3; Loop++)
    {
        Node = CCQueuePop(self.decodedPackets);
        XCTAssertNotEqual(Node, NULL, @"Should have a decoded packet");
        if (Node)
        {
            Packet *P = CCQueueGetNodeData(Node);
            XCTAssertEqual(P->size, 1, @"Should have the correct size");
            XCTAssertEqual(P->data[0], Loop + 1, @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    Node = CCQueuePop(self.decodedPackets);
    XCTAssertEqual(Node, NULL, @"Should not have anymore decoded packets");
}

-(void) testPacketDecay
{
    uint8_t Data[] = {
        96, 65,
        112, 81, 64, 18,
        112, 81, 64, 18,
        112, 81, 64, 18,
        48, 17,
    };
    
    self.encodedPackets = Data;
    self.encodedPacketCount = sizeof(Data) / sizeof(typeof(*Data));
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(self.encodedPacketIndex, self.encodedPacketCount, @"Should consume all incoming packets");
    
    CCQueueNode *Node;
    for (size_t Loop = 0; Loop < 3; Loop++)
    {
        Node = CCQueuePop(self.decodedPackets);
        XCTAssertNotEqual(Node, NULL, @"Should have a decoded packet");
        if (Node)
        {
            Packet *P = CCQueueGetNodeData(Node);
            XCTAssertEqual(P->size, 1, @"Should have the correct size");
            XCTAssertEqual(P->data[0], 2, @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    Node = CCQueuePop(self.decodedPackets);
    XCTAssertEqual(Node, NULL, @"Should not have anymore decoded packets");
}

-(void) testPacketMixedInterleaved
{
    uint8_t Data[] = {
        112, 81, 64, //p3
        112, 81, //p2
        96, 65, //p1
        64, //p2
        48, 17, //p1
        18, //p2
        18, //p3
    };
    
    self.encodedPackets = Data;
    self.encodedPacketCount = sizeof(Data) / sizeof(typeof(*Data));
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(self.encodedPacketIndex, self.encodedPacketCount, @"Should consume all incoming packets");
    
    CCQueueNode *Node = CCQueuePop(self.decodedPackets);
    XCTAssertNotEqual(Node, NULL, @"Should have a decoded packet");
    if (Node)
    {
        Packet *P = CCQueueGetNodeData(Node);
        XCTAssertEqual(P->size, 1, @"Should have the correct size");
        XCTAssertEqual(P->data[0], 1, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    for (size_t Loop = 0; Loop < 2; Loop++)
    {
        Node = CCQueuePop(self.decodedPackets);
        XCTAssertNotEqual(Node, NULL, @"Should have a decoded packet");
        if (Node)
        {
            Packet *P = CCQueueGetNodeData(Node);
            XCTAssertEqual(P->size, 1, @"Should have the correct size");
            XCTAssertEqual(P->data[0], 2, @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    Node = CCQueuePop(self.decodedPackets);
    XCTAssertEqual(Node, NULL, @"Should not have anymore decoded packets");
}

-(void) testPacketHashCollision
{
    uint8_t Data[] = {
        96, 65, //p1
        76,
        48, 17, //p1
    };
    
    self.encodedPackets = Data;
    self.encodedPacketCount = sizeof(Data) / sizeof(typeof(*Data));
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(self.encodedPacketIndex, self.encodedPacketCount, @"Should consume all incoming packets");
    
    CCQueueNode *Node = CCQueuePop(self.decodedPackets);
    XCTAssertEqual(Node, NULL, @"Should not have anymore decoded packets");
}

-(void) testPacketHashSeeding
{
    uint8_t Data[] = {
        128, 97, //p1
        76,
        80, 49, //p1
    };
    
    self.encodedPackets = Data;
    self.encodedPacketCount = sizeof(Data) / sizeof(typeof(*Data));
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(self.encodedPacketIndex, self.encodedPacketCount, @"Should consume all incoming packets");
    
    CCQueueNode *Node = CCQueuePop(self.decodedPackets);
    XCTAssertNotEqual(Node, NULL, @"Should have a decoded packet");
    if (Node)
    {
        Packet *P = CCQueueGetNodeData(Node);
        XCTAssertEqual(P->size, 1, @"Should have the correct size");
        XCTAssertEqual(P->data[0], 1, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(self.decodedPackets);
    XCTAssertEqual(Node, NULL, @"Should not have anymore decoded packets");
}

-(void) testMaxConcurrentPackets
{
    uint8_t Data[] = {
        96, //p1
        96, //p2
        96, //p3
        96, //p4
        96, //p5
        96, //p6
        65, //p1
        65, //p2
        65, //p3
        65, //p4
        65, //p5
        65, //p6
        48, //p1
        48, //p2
        48, //p3
        48, //p4
        48, //p5
        48, //p6
        17, //p1
        17, //p2
        17, //p3
        17, //p4
        17, //p5
        17, //p6
    };
    
    self.encodedPackets = Data;
    self.encodedPacketCount = sizeof(Data) / sizeof(typeof(*Data));
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(self.encodedPacketIndex, self.encodedPacketCount, @"Should consume all incoming packets");
    
    CCQueueNode *Node;
    for (size_t Loop = 5; Loop > 0; Loop--)
    {
        Node = CCQueuePop(self.decodedPackets);
        XCTAssertNotEqual(Node, NULL, @"Should have a decoded packet");
        if (Node)
        {
            Packet *P = CCQueueGetNodeData(Node);
            XCTAssertEqual(P->size, 1, @"Should have the correct size");
            XCTAssertEqual(P->data[0], 1, @"Should have the correct data");
            CCQueueDestroyNode(Node);
        }
    }
    
    Node = CCQueuePop(self.decodedPackets);
    XCTAssertEqual(Node, NULL, @"Should not have anymore decoded packets");
}

-(void) testDecodingIncompletePacket
{
    uint8_t Data[] = {
        96, 65, 48 // 1 bit htp
    };
    
    self.encodedPackets = Data;
    self.encodedPacketCount = sizeof(Data) / sizeof(typeof(*Data));
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(self.encodedPacketIndex, self.encodedPacketCount, @"Should consume all incoming packets");
    
    CCQueueNode *Node = CCQueuePop(self.decodedPackets);
    XCTAssertEqual(Node, NULL, @"Should not have anymore decoded packets");
}

-(void) testDecodingPacketLengthUnusedData
{
    uint8_t Data[] = {
        239, 73, 48, 17
    };
    
    self.encodedPackets = Data;
    self.encodedPacketCount = sizeof(Data) / sizeof(typeof(*Data));
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(self.encodedPacketIndex, self.encodedPacketCount, @"Should consume all incoming packets");
    
    CCQueueNode *Node = CCQueuePop(self.decodedPackets);
    XCTAssertNotEqual(Node, NULL, @"Should have a decoded packet");
    if (Node)
    {
        Packet *P = CCQueueGetNodeData(Node);
        XCTAssertEqual(P->size, 0xf8 | 1, @"Should have the correct size");
        XCTAssertEqual(P->data[0], 1, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(self.decodedPackets);
    XCTAssertEqual(Node, NULL, @"Should not have anymore decoded packets");
}

-(void) testDecodingPacketMaxLength
{
    uint8_t Data[] = {
        96, 215, 192, 161, 144, 98, 80, 19, 240, 164, 144, 53, 32, 166, 144, 23
    };
    
    self.encodedPackets = Data;
    self.encodedPacketCount = sizeof(Data) / sizeof(typeof(*Data));
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(self.encodedPacketIndex, self.encodedPacketCount, @"Should consume all incoming packets");
    
    CCQueueNode *Node = CCQueuePop(self.decodedPackets);
    XCTAssertNotEqual(Node, NULL, @"Should have a decoded packet");
    if (Node)
    {
        Packet *P = CCQueueGetNodeData(Node);
        XCTAssertEqual(P->size, 7, @"Should have the correct size");
        XCTAssertEqual(P->data[0], 1, @"Should have the correct data");
        XCTAssertEqual(P->data[1], 2, @"Should have the correct data");
        XCTAssertEqual(P->data[2], 3, @"Should have the correct data");
        XCTAssertEqual(P->data[3], 4, @"Should have the correct data");
        XCTAssertEqual(P->data[4], 5, @"Should have the correct data");
        XCTAssertEqual(P->data[5], 6, @"Should have the correct data");
        XCTAssertEqual(P->data[6], 7, @"Should have the correct data");
        CCQueueDestroyNode(Node);
    }
    
    Node = CCQueuePop(self.decodedPackets);
    XCTAssertEqual(Node, NULL, @"Should not have anymore decoded packets");
}

-(void) testDecodingPacketZeroLength
{
    uint8_t Data[] = {
        32, 16
    };
    
    self.encodedPackets = Data;
    self.encodedPacketCount = sizeof(Data) / sizeof(typeof(*Data));
    HKHubArchProcessorSetCycles(self.processor, 100000);
    HKHubArchSchedulerRun(self.scheduler, 0.0);
    
    XCTAssertEqual(self.encodedPacketIndex, self.encodedPacketCount, @"Should consume all incoming packets");
    
    CCQueueNode *Node = CCQueuePop(self.decodedPackets);
    XCTAssertEqual(Node, NULL, @"Should not have anymore decoded packets");
}

@end
