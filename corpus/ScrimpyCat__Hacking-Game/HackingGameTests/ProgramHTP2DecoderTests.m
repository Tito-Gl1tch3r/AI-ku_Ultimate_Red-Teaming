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

@interface ProgramHTP2DecoderTests : ProgramHTPDecoderTests

@end

@implementation ProgramHTP2DecoderTests

-(const char*) program
{
    return "assets/logic/programs/htp2_decoder.chasm";
}

-(void) testDecodingPacket
{
    uint8_t Data[] = {
        76, 144, 224, 55, 12, 128, 220, 54, 12, 128, 220, 117, 91, 147, 35, 7 // 2 bit htp
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
        76, 144, 224, 55, 12, 128, 220, 54, 12, 128, 220, 117, 91, 147, 35, 7,
        76, 144, 224, 55, 12, 128, 220, 54, 12, 128, 220, 117, 91, 147, 35, 7,
        76, 144, 224, 55, 12, 128, 220, 54, 12, 128, 220, 117, 91, 147, 35, 7,
        76, 144, 224, 55, 12, 128, 220, 54, 12, 128, 220, 117, 91, 147, 35, 7,
        76, 144, 224, 55, 12, 128, 220, 54, 12, 128, 220, 117, 91, 147, 35, 7,
        76, 144, 224, 55, 12, 128, 220, 54, 12, 128, 220, 117, 91, 147, 35, 7,
        76, 144, 224, 55, 12, 128, 220, 54, 12, 128, 220, 117, 91, 147, 35, 7,
        76, 144, 224, 55, 12, 128, 220, 54, 12, 128, 220, 117, 91, 147, 35, 7,
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
        76, 144, 76, 224, 144, 224, 55, 12, 128, 55, 12, 128, 220, 220, 54, 12, 54, 12, 128, 220, 117, 128, 220, 117, 91, 91, 147, 147, 35, 7, 35, 7
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
        4, 252, 188, 109, 152, 100, 24, 5,
        8, 64, 204, 113, 216, 116, 28, 6,
        12, 128, 220, 117, 28, 132, 32, 7
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
        4, 252, 188, 109,
        8, 64, 204, 113, 216, 116, 28, 6,
        8, 64, 204, 113, 216, 116, 28, 6,
        152, 100, 24, 5
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
        8, 64, //p2
        8, //p3
        4, 252, 188, 109, 152, //p1
        204, 113, 216, //p2
        100, //p1
        64, 204, //p3
        24, 5, //p1
        116, 28, 6, //p2
        113, 216, 116, 28, 6, //p3
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
        4, 252, 188, 109, //p1
        26,
        152, 100, 24, 5, //p1
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
        56, 76, 144, 161, //p1
        26,
        228, 56, 76, 81, //p1
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
        4, //p1
        4, //p2
        4, //p3
        4, //p4
        4, //p5
        4, //p6
        252, //p1
        252, //p2
        252, //p3
        252, //p4
        252, //p5
        252, //p6
        188, //p1
        188, //p2
        188, //p3
        188, //p4
        188, //p5
        188, //p6
        109, //p1
        109, //p2
        109, //p3
        109, //p4
        109, //p5
        109, //p6
        152, //p1
        152, //p2
        152, //p3
        152, //p4
        152, //p5
        152, //p6
        100, //p1
        100, //p2
        100, //p3
        100, //p4
        100, //p5
        100, //p6
        24, //p1
        24, //p2
        24, //p3
        24, //p4
        24, //p5
        24, //p6
        5, //p1
        5, //p2
        5, //p3
        5, //p4
        5, //p5
        5, //p6
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
        4, 252, 188, 109, 152, 100, 24 // 1 bit htp
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
        51, 11, 190, 109, 152, 100, 24, 5
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
        88, 84, 209, 51, 200, 112, 216, 53, 12, 128, 220, 54, 12, 128, 220, 243, 248,
        124, 93, 148, 36, 8, 253, 125, 156, 164, 229, 182, 44, 136, 33, 7
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
        88, 84, 20, 4
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
