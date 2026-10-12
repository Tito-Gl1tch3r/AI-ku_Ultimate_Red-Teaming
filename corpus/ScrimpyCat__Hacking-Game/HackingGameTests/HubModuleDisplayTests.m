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

#import <XCTest/XCTest.h>
#import "HubArchProcessor.h"
#import "HubArchAssembly.h"
#import "HubModuleDisplay.h"

#define HKHubArchAssemblyPrintError(err) if (Errors) { HKHubArchAssemblyPrintError(err); CCCollectionDestroy(err); err = NULL; }

@interface HubModuleDisplayTests : XCTestCase

@end

@implementation HubModuleDisplayTests

-(void) testDrawingInput
{
    const char *Source =
        ".define display, 0\n"
        "msg: .byte 0, 0, 0\n"
        ".entrypoint\n"
        "send display, 2, [msg]\n"
        "mov [msg], 1\n"
        "mov [msg+1], 0xe0\n" //r = 7, g = 0, b = 0
        "mov [msg+2], 3\n" //r = 0, g = 0, b = 3
        "send display, 3, [msg]\n"
        "hlt\n"
    ;
    
    CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubArchProcessor Processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
    HKHubArchBinaryDestroy(Binary);
    
    
    HKHubModule Display = HKHubModuleDisplayCreate(CC_STD_ALLOCATOR);
    
    HKHubArchPortConnection Conn = HKHubArchPortConnectionCreate(CC_STD_ALLOCATOR, HKHubArchProcessorGetPort(Processor, 0), HKHubModuleGetPort(Display, 0));
    
    HKHubArchProcessorConnect(Processor, 0, Conn);
    HKHubModuleConnect(Display, 0, Conn);
    HKHubArchPortConnectionDestroy(Conn);
    
    
    HKHubArchProcessorSetCycles(Processor, 500);
    HKHubArchProcessorRun(Processor);
    
    
    CCData Buffer = HKHubModuleDisplayConvertBuffer(CC_STD_ALLOCATOR, Display, HKHubModuleDisplayBuffer_DirectColourRGB888);
    CCPixelData Pixels = CCPixelDataStaticCreate(CC_STD_ALLOCATOR, Buffer, CCColourFormatRGB8Uint, 16, 16, 1);
    
    
    CCColour Colour = CCPixelDataGetColour(Pixels, 0, 0, 0);
    
    CCColourComponent Component = CCColourGetComponent(Colour, CCColourFormatChannelRed);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelGreen);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelBlue);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    
    Colour = CCPixelDataGetColour(Pixels, 1, 0, 0);
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelRed);
    XCTAssertEqual(Component.u8, 255, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelGreen);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelBlue);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    
    Colour = CCPixelDataGetColour(Pixels, 2, 0, 0);
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelRed);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelGreen);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelBlue);
    XCTAssertEqual(Component.u8, 255, @"Should contain the correct colour");
    
    
    CCPixelDataDestroy(Pixels);
    
    
    
    Buffer = HKHubModuleDisplayConvertBuffer(CC_STD_ALLOCATOR, Display, HKHubModuleDisplayBuffer_UniformColourRGB888);
    Pixels = CCPixelDataStaticCreate(CC_STD_ALLOCATOR, Buffer, CCColourFormatRGB8Uint, 16, 16, 1);
    
    
    Colour = CCPixelDataGetColour(Pixels, 0, 0, 0);
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelRed);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelGreen);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelBlue);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    
    Colour = CCPixelDataGetColour(Pixels, 1, 0, 0);
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelRed);
    XCTAssertEqual(Component.u8, (3 * 17) + (2 * 68), @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelGreen);
    XCTAssertEqual(Component.u8, (3 * 17), @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelBlue);
    XCTAssertEqual(Component.u8, (3 * 17), @"Should contain the correct colour");
    
    
    Colour = CCPixelDataGetColour(Pixels, 2, 0, 0);
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelRed);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelGreen);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelBlue);
    XCTAssertEqual(Component.u8, (3 * 68), @"Should contain the correct colour");
    
    
    CCPixelDataDestroy(Pixels);
    
    
    
    Buffer = HKHubModuleDisplayConvertBuffer(CC_STD_ALLOCATOR, Display, HKHubModuleDisplayBuffer_GradientColourRGB888);
    Pixels = CCPixelDataStaticCreate(CC_STD_ALLOCATOR, Buffer, CCColourFormatRGB8Uint, 16, 16, 1);
    
    
    Colour = CCPixelDataGetColour(Pixels, 0, 0, 0);
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelRed);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelGreen);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelBlue);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    
    Colour = CCPixelDataGetColour(Pixels, 1, 0, 0);
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelRed);
    XCTAssertEqual(Component.u8, 8, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelGreen);
    XCTAssertEqual(Component.u8, 8, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelBlue);
    XCTAssertEqual(Component.u8, 8, @"Should contain the correct colour");
    
    
    Colour = CCPixelDataGetColour(Pixels, 2, 0, 0);
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelRed);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelGreen);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelBlue);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    
    CCPixelDataDestroy(Pixels);
    
    
    
    Buffer = HKHubModuleDisplayConvertBuffer(CC_STD_ALLOCATOR, Display, HKHubModuleDisplayBuffer_YUVColourRGB888);
    Pixels = CCPixelDataStaticCreate(CC_STD_ALLOCATOR, Buffer, CCColourFormatRGB8Uint, 16, 16, 1);
    
    
    Colour = CCPixelDataGetColour(Pixels, 0, 0, 0);
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelRed);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelGreen);
    XCTAssertEqual(Component.u8, 151, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelBlue);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    
    Colour = CCPixelDataGetColour(Pixels, 1, 0, 0);
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelRed);
    XCTAssertEqual(Component.u8, 255, "Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelGreen);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelBlue);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    
    Colour = CCPixelDataGetColour(Pixels, 2, 0, 0);
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelRed);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelGreen);
    XCTAssertEqual(Component.u8, 255, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelBlue);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    
    CCPixelDataDestroy(Pixels);
    
    
    
    CCData Memory = HKHubModuleGetMemory(Display);
    XCTAssertEqual(CCDataGetSize(Memory), 256, @"Should be the correct size");
    
    uint8_t RawPixels[256];
    CCDataReadBuffer(Memory, 0, sizeof(RawPixels), RawPixels);
    XCTAssertEqual(RawPixels[0], 0, @"Should be the correct raw pixel");
    XCTAssertEqual(RawPixels[1], 0xe0, @"Should be the correct raw pixel");
    XCTAssertEqual(RawPixels[2], 3, @"Should be the correct raw pixel");
    for (size_t Loop = 3; Loop < sizeof(RawPixels); Loop++)
    {
        XCTAssertEqual(RawPixels[Loop], 0, @"Should be the correct raw pixel");
    }
    
    CCDataWriteBuffer(Memory, 0, 1, &(uint8_t){ 0x0a }); //r = 0, g = 2, b = 2
    
    Buffer = HKHubModuleDisplayConvertBuffer(CC_STD_ALLOCATOR, Display, HKHubModuleDisplayBuffer_DirectColourRGB888);
    Pixels = CCPixelDataStaticCreate(CC_STD_ALLOCATOR, Buffer, CCColourFormatRGB8Uint, 16, 16, 1);
    
    
    Colour = CCPixelDataGetColour(Pixels, 0, 0, 0);
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelRed);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelGreen);
    XCTAssertEqual(Component.u8, 73, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelBlue);
    XCTAssertEqual(Component.u8, 170, @"Should contain the correct colour");
    
    
    Colour = CCPixelDataGetColour(Pixels, 1, 0, 0);
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelRed);
    XCTAssertEqual(Component.u8, 255, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelGreen);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelBlue);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    
    Colour = CCPixelDataGetColour(Pixels, 2, 0, 0);
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelRed);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelGreen);
    XCTAssertEqual(Component.u8, 0, @"Should contain the correct colour");
    
    Component = CCColourGetComponent(Colour, CCColourFormatChannelBlue);
    XCTAssertEqual(Component.u8, 255, @"Should contain the correct colour");
    
    
    CCPixelDataDestroy(Pixels);
    
    HKHubModuleDestroy(Display);
}

@end
