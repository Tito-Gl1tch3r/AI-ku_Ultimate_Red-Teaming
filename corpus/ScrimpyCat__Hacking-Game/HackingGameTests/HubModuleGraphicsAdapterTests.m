/*
 *  Copyright (c) 2021, Stefan Johnson
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
#import "HubModuleGraphicsAdapter.h"
#import "HubArchAssembly.h"

@interface HubModuleGraphicsAdapterTests : XCTestCase

@end

@implementation HubModuleGraphicsAdapterTests

+(void) setUp
{
    [super setUp];
    
    if (HKHubArchAssemblyIncludeSearchPaths) CCCollectionDestroy(HKHubArchAssemblyIncludeSearchPaths);
    
    HKHubArchAssemblyIncludeSearchPaths = CCCollectionCreate(CC_STD_ALLOCATOR, CCCollectionHintOrdered, sizeof(FSPath), FSPathComponentDestructorForCollection);
    
    CCOrderedCollectionAppendElement(HKHubArchAssemblyIncludeSearchPaths, &(FSPath){ FSPathCreate("assets/logic/programs/") });
    CCOrderedCollectionAppendElement(HKHubArchAssemblyIncludeSearchPaths, &(FSPath){ FSPathCreate("assets/logic/procedures/") });
    
    HKHubModuleGraphicsAdapterStaticGlyphInit();
    
    HKHubModuleGraphicsAdapterStaticGlyphSet('!', 0, 0, 7, (uint8_t[]){
        0, 0, 0, 1, 0, 0, 0,
        0, 0, 1, 1, 0, 0, 0,
        0, 0, 0, 1, 0, 0, 0,
        0, 0, 0, 1, 0, 0, 0,
        0, 0, 0, 1, 0, 0, 0,
        0, 0, 0, 1, 0, 0, 0,
        0, 0, 1, 1, 1, 0, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('@', 0, 0, 7, (uint8_t[]){
        0, 0, 1, 1, 1, 0, 0,
        0, 1, 0, 0, 0, 1, 0,
        0, 0, 0, 0, 0, 1, 0,
        0, 0, 0, 0, 1, 0, 0,
        0, 0, 0, 1, 0, 0, 0,
        0, 0, 1, 0, 0, 0, 0,
        0, 1, 1, 1, 1, 1, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('#', 0, 0, 7, (uint8_t[]){
        0, 0, 1, 1, 1, 0, 0,
        0, 0, 0, 0, 0, 1, 0,
        0, 0, 0, 0, 0, 1, 0,
        0, 0, 0, 1, 1, 0, 0,
        0, 0, 0, 0, 0, 1, 0,
        0, 0, 0, 0, 0, 1, 0,
        0, 0, 1, 1, 1, 0, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('$', 0, 0, 7, (uint8_t[]){
        0, 0, 0, 0, 1, 0, 0,
        0, 0, 0, 1, 1, 0, 0,
        0, 0, 1, 0, 1, 0, 0,
        0, 1, 1, 1, 1, 0, 0,
        0, 0, 0, 0, 1, 0, 0,
        0, 0, 0, 0, 1, 0, 0,
        0, 0, 0, 0, 1, 0, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('%', 0, 0, 7, (uint8_t[]){
        0, 0, 1, 1, 1, 1, 0,
        0, 0, 1, 0, 0, 0, 0,
        0, 0, 1, 0, 0, 0, 0,
        0, 0, 1, 1, 1, 1, 0,
        0, 0, 0, 0, 0, 1, 0,
        0, 0, 0, 0, 0, 1, 0,
        0, 0, 1, 1, 1, 1, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('^', 0, 0, 7, (uint8_t[]){
        0, 0, 1, 1, 1, 1, 0,
        0, 0, 1, 0, 0, 0, 0,
        0, 0, 1, 0, 0, 0, 0,
        0, 0, 1, 1, 1, 1, 0,
        0, 0, 1, 0, 0, 1, 0,
        0, 0, 1, 0, 0, 1, 0,
        0, 0, 1, 1, 1, 1, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('&', 0, 0, 7, (uint8_t[]){
        0, 0, 1, 1, 1, 1, 0,
        0, 0, 0, 0, 0, 1, 0,
        0, 0, 0, 0, 0, 1, 0,
        0, 0, 0, 0, 0, 1, 0,
        0, 0, 0, 0, 0, 1, 0,
        0, 0, 0, 0, 0, 1, 0,
        0, 0, 0, 0, 0, 1, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('*', 0, 0, 7, (uint8_t[]){
        0, 0, 0, 1, 1, 0, 0,
        0, 0, 1, 0, 0, 1, 0,
        0, 0, 1, 0, 0, 1, 0,
        0, 0, 0, 1, 1, 0, 0,
        0, 0, 1, 0, 0, 1, 0,
        0, 0, 1, 0, 0, 1, 0,
        0, 0, 0, 1, 1, 0, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('(', 0, 0, 7, (uint8_t[]){
        0, 0, 1, 1, 1, 1, 0,
        0, 0, 1, 0, 0, 1, 0,
        0, 0, 1, 0, 0, 1, 0,
        0, 0, 1, 1, 1, 1, 0,
        0, 0, 0, 0, 0, 1, 0,
        0, 0, 0, 0, 0, 1, 0,
        0, 0, 1, 1, 1, 1, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet(')', 0, 0, 7, (uint8_t[]){
        0, 0, 1, 1, 1, 0, 0,
        0, 1, 0, 0, 1, 1, 0,
        0, 1, 0, 1, 0, 1, 0,
        0, 1, 0, 1, 0, 1, 0,
        0, 1, 0, 1, 0, 1, 0,
        0, 1, 1, 0, 0, 1, 0,
        0, 0, 1, 1, 1, 0, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('>', 0, 0, 7, (uint8_t[]){
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 1, 1, 1, 0, 0,
        0, 0, 1, 1, 1, 0, 0,
        0, 0, 1, 1, 1, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('A', 0, 0, 7, (uint8_t[]){
        0, 0, 0, 1, 0, 0, 0,
        0, 0, 1, 0, 1, 0, 0,
        0, 0, 1, 0, 1, 0, 0,
        0, 1, 1, 1, 1, 1, 0,
        0, 1, 0, 0, 0, 1, 0,
        1, 0, 0, 0, 0, 0, 1,
        1, 0, 0, 0, 0, 0, 1
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('B', 0, 0, 7, (uint8_t[]){
        0, 1, 1, 1, 0, 0, 0,
        0, 1, 0, 0, 1, 0, 0,
        0, 1, 0, 0, 1, 0, 0,
        0, 1, 1, 1, 0, 0, 0,
        0, 1, 0, 0, 1, 0, 0,
        0, 1, 0, 0, 1, 0, 0,
        0, 1, 1, 1, 0, 0, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('C', 0, 0, 7, (uint8_t[]){
        0, 0, 1, 1, 1, 1, 0,
        0, 1, 0, 0, 0, 0, 0,
        0, 1, 0, 0, 0, 0, 0,
        0, 1, 0, 0, 0, 0, 0,
        0, 1, 0, 0, 0, 0, 0,
        0, 1, 0, 0, 0, 0, 0,
        0, 0, 1, 1, 1, 1, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('D', 0, 0, 7, (uint8_t[]){
        0, 1, 1, 1, 1, 0, 0,
        0, 1, 0, 0, 0, 1, 0,
        0, 1, 0, 0, 0, 1, 0,
        0, 1, 0, 0, 0, 0, 1,
        0, 1, 0, 0, 0, 1, 0,
        0, 1, 0, 0, 0, 1, 0,
        0, 1, 1, 1, 1, 0, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('E', 0, 0, 7, (uint8_t[]){
        0, 1, 1, 1, 1, 0, 0,
        0, 1, 0, 0, 0, 0, 0,
        0, 1, 0, 0, 0, 0, 0,
        0, 1, 1, 1, 0, 0, 0,
        0, 1, 0, 0, 0, 0, 0,
        0, 1, 0, 0, 0, 0, 0,
        0, 1, 1, 1, 1, 0, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('F', 0, 0, 7, (uint8_t[]){
        0, 1, 1, 1, 1, 0, 0,
        0, 1, 0, 0, 0, 0, 0,
        0, 1, 0, 0, 0, 0, 0,
        0, 1, 1, 1, 0, 0, 0,
        0, 1, 0, 0, 0, 0, 0,
        0, 1, 0, 0, 0, 0, 0,
        0, 1, 0, 0, 0, 0, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('G', 0, 0, 7, (uint8_t[]){
        0, 1, 1, 1, 1, 0, 0,
        0, 1, 0, 0, 0, 0, 0,
        0, 1, 0, 0, 0, 0, 0,
        0, 1, 0, 1, 1, 0, 0,
        0, 1, 0, 0, 1, 0, 0,
        0, 1, 0, 0, 1, 0, 0,
        0, 1, 1, 1, 1, 0, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('H', 0, 0, 7, (uint8_t[]){
        0, 1, 0, 0, 1, 0, 0,
        0, 1, 0, 0, 1, 0, 0,
        0, 1, 0, 0, 1, 0, 0,
        0, 1, 1, 1, 1, 0, 0,
        0, 1, 0, 0, 1, 0, 0,
        0, 1, 0, 0, 1, 0, 0,
        0, 1, 0, 0, 1, 0, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('I', 0, 0, 7, (uint8_t[]){
        0, 0, 1, 1, 1, 0, 0,
        0, 0, 0, 1, 0, 0, 0,
        0, 0, 0, 1, 0, 0, 0,
        0, 0, 0, 1, 0, 0, 0,
        0, 0, 0, 1, 0, 0, 0,
        0, 0, 0, 1, 0, 0, 0,
        0, 0, 1, 1, 1, 0, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('J', 0, 0, 7, (uint8_t[]){
        0, 0, 1, 1, 1, 0, 0,
        0, 0, 0, 1, 0, 0, 0,
        0, 0, 0, 1, 0, 0, 0,
        0, 0, 0, 1, 0, 0, 0,
        0, 0, 0, 1, 0, 0, 0,
        0, 1, 0, 1, 0, 0, 0,
        0, 0, 1, 0, 0, 0, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('K', 0, 0, 7, (uint8_t[]){
        0, 0, 1, 0, 0, 0, 1,
        0, 0, 1, 0, 0, 1, 0,
        0, 0, 1, 0, 1, 0, 0,
        0, 0, 1, 1, 0, 0, 0,
        0, 0, 1, 0, 1, 0, 0,
        0, 0, 1, 0, 0, 1, 0,
        0, 0, 1, 0, 0, 0, 1
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('L', 0, 0, 7, (uint8_t[]){
        0, 0, 1, 0, 0, 0, 0,
        0, 0, 1, 0, 0, 0, 0,
        0, 0, 1, 0, 0, 0, 0,
        0, 0, 1, 0, 0, 0, 0,
        0, 0, 1, 0, 0, 0, 0,
        0, 0, 1, 0, 0, 0, 0,
        0, 0, 1, 1, 1, 1, 1
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('M', 0, 0, 7, (uint8_t[]){
        0, 1, 0, 0, 0, 1, 0,
        0, 1, 1, 0, 1, 1, 0,
        0, 1, 0, 1, 0, 1, 0,
        0, 1, 0, 0, 0, 1, 0,
        0, 1, 0, 0, 0, 1, 0,
        0, 1, 0, 0, 0, 1, 0,
        0, 1, 0, 0, 0, 1, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('N', 0, 0, 7, (uint8_t[]){
        0, 1, 0, 0, 0, 1, 0,
        0, 1, 1, 0, 0, 1, 0,
        0, 1, 1, 0, 0, 1, 0,
        0, 1, 0, 1, 0, 1, 0,
        0, 1, 0, 0, 1, 1, 0,
        0, 1, 0, 0, 1, 1, 0,
        0, 1, 0, 0, 0, 1, 0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet('+', 0, 0, 7, (uint8_t[]){
        0, 0, 1, 1, 1, 0, 0,
        0, 1, 0, 0, 0, 1, 0,
        0, 1, 0, 0, 0, 1, 0,
        0, 1, 0, 0, 0, 1, 0,
        0, 1, 0, 0, 0, 1, 0,
        0, 1, 0, 0, 0, 1, 0,
        0, 0, 1, 1, 1, 0, 0
    }, 1);
}

static const uint8_t Glyph1x1[] = {
    0xff,
    0xff,
    0x00,
    0x3c,
    0x00,
    0xf0,
    0x03,
    0xc0,
    0x0f,
    0x00,
    0x3f,
    0xff,
    0xc0
};

-(void) setProgram: (const char*)source WithID: (uint8_t)programID ForAdapter: (HKHubModule)adapter
{
    CCOrderedCollection AST = HKHubArchAssemblyParse([[NSString stringWithFormat: @".include \"../../graphics-adapter/programs/tab\"\n.include \"../../graphics-adapter/programs/newline\"\n%s\n.entrypoint\n", source] UTF8String]);
    
    CCOrderedCollection Errors = NULL;
    HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
    CCCollectionDestroy(AST);
    
    HKHubModuleGraphicsAdapterProgramSet(adapter, programID, Binary->data, Binary->entrypoint);
    
    HKHubArchBinaryDestroy(Binary);
}

-(void) drawChars: (const char*)string AtLayer: (uint8_t)layer ForAdapter: (HKHubModule)adapter
{
    unsigned char c;
    while ((c = *(string++))) HKHubModuleGraphicsAdapterDrawCharacter(adapter, layer, c);
}

-(void) clearViewport: (HKHubArchPortID)port AtLayer: (uint8_t)layer ForAdapter: (HKHubModule)adapter
{
    uint8_t OriginX, OriginY;
    HKHubModuleGraphicsAdapterGetCursorOrigin(adapter, 0, &OriginX, &OriginY);
    
    uint8_t X, Y, W, H;
    HKHubModuleGraphicsAdapterGetViewport(adapter, port, &X, &Y, &W, &H);
    
    HKHubModuleGraphicsAdapterSetCursor(adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorOrigin(adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterClear(adapter, 0, X, Y, W, H);
    HKHubModuleGraphicsAdapterSetCursorOrigin(adapter, 0, OriginX, OriginY);
}

-(NSImage*) previewViewport: (HKHubArchPortID)port ForAdapter: (HKHubModule)adapter
{
    uint8_t W, H;
    HKHubModuleGraphicsAdapterGetViewport(adapter, port, NULL, NULL, &W, &H);
    
    const size_t Width = ((size_t)W + 1) * HK_HUB_MODULE_GRAPHICS_ADAPTER_CELL, Height = ((size_t)H + 1) * HK_HUB_MODULE_GRAPHICS_ADAPTER_CELL;
    const size_t Size = Width * Height;
    uint8_t *Framebuffer;
    CC_TEMP_Malloc(Framebuffer, Size);
    memset(Framebuffer, 0, Size);
    HKHubModuleGraphicsAdapterBlit(adapter, port, Framebuffer, Size);
    
    CGColorSpaceRef ColourSpace = CGColorSpaceCreateDeviceRGB();
    CGContextRef Ctx = CGBitmapContextCreate(NULL, Width, Height, 8, Width * 4, ColourSpace, kCGImageAlphaPremultipliedLast);
    CGColorSpaceRelease(ColourSpace);
    
    CGContextSetRGBFillColor(Ctx, 0.0f, 0.0f, 0.0f, 1.0f);
    CGContextFillRect(Ctx, CGRectMake(0.0f, 0.0f, Width, Height));
    
    for (size_t Y = 0; Y < Height; Y++)
    {
        for (size_t X = 0; X < Width; X++)
        {
            if (Framebuffer[(Y * Width) + X])
            {
                switch (Framebuffer[(Y * Width) + X])
                {
                    case 1:
                        CGContextSetRGBFillColor(Ctx, 1.0f, 1.0f, 1.0f, 1.0f);
                        break;
                        
                    case 2:
                        CGContextSetRGBFillColor(Ctx, 1.0f, 0.0f, 0.0f, 1.0f);
                        break;
                        
                    case 3:
                        CGContextSetRGBFillColor(Ctx, 0.0f, 1.0f, 0.0f, 1.0f);
                        break;
                        
                    case 4:
                        CGContextSetRGBFillColor(Ctx, 0.0f, 0.0f, 1.0f, 1.0f);
                        break;
                        
                    default:
                        CGContextSetRGBFillColor(Ctx, 1.0f, 0.0f, 1.0f, 1.0f);
                        break;
                }
                CGContextFillRect(Ctx, CGRectMake(X, Height - Y - 1, 1.0f, 1.0f));
            }
        }
    }
    
    CGImageRef Image = CGBitmapContextCreateImage(Ctx);
    NSImage *Preview = [[NSImage alloc] initWithCGImage: Image size: NSMakeSize(Width, Height)];
    CGImageRelease(Image);
    
    CGContextRelease(Ctx);
    
    CC_TEMP_Free(Framebuffer);
    
    return Preview;
}

-(void) assertImage: (NSString*)name  MatchesViewport: (HKHubArchPortID)port ForAdapter: (HKHubModule)adapter
{
    NSImage *Image = [[NSImage alloc] initWithContentsOfFile: [NSString stringWithFormat: @"%@/images/HubModuleGraphicsAdapterTests/%@.png", [[NSBundle bundleForClass: [self class]] resourcePath], name]], *Preview = [self previewViewport: port ForAdapter: adapter];
    
    XCTAssertEqual(Image.size.width, Preview.size.width, @"Should have the same width");
    XCTAssertEqual(Image.size.height, Preview.size.height, @"Should have the same height");
    
    NSBitmapImageRep *ImageRep = [[NSBitmapImageRep alloc] initWithCGImage: [Image CGImageForProposedRect: NULL context: nil hints: nil]];
    NSBitmapImageRep *PreviewRep = [[NSBitmapImageRep alloc] initWithCGImage: [Preview CGImageForProposedRect: NULL context: nil hints: nil]];
    
    for (size_t Y = 0, Height = Image.size.height; Y < Height; Y++)
    {
        for (size_t X = 0, Width = Image.size.width; X < Width; X++)
        {
            XCTAssertTrue([[ImageRep colorAtX: X y: Y] isEqual: [PreviewRep colorAtX: X y: Y]], @"Should match pixel (%zu, %zu)", X, Y);
        }
    }
}

-(void) testBlit
{
    HKHubModule Adapter = HKHubModuleGraphicsAdapterCreate(CC_STD_ALLOCATOR);
    
    HKHubModuleGraphicsAdapterSetViewport(Adapter, 0, 0, 0, 39, 39);
    HKHubModuleGraphicsAdapterSetViewport(Adapter, 8, 35, 35, 7, 7);
    HKHubModuleGraphicsAdapterSetViewport(Adapter, 16, 37, 0, 0, 39);
    HKHubModuleGraphicsAdapterSetViewport(Adapter, 24, 0, 32, 7, 3);
    HKHubModuleGraphicsAdapterSetViewport(Adapter, 32, 6, 21, 14, 9);
    
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorVisibility(Adapter, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvance(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursorAdvanceSource(Adapter, 0, 1, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvanceOffset(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursorWrapSource(Adapter, 0, 0, 1);
    HKHubModuleGraphicsAdapterSetCursorWrapOffset(Adapter, 0, 0, 0);
    
    HKHubModuleGraphicsAdapterSetPalettePage(Adapter, 0, 0);
    HKHubModuleGraphicsAdapterSetPaletteOffset(Adapter, 0, 0);
    HKHubModuleGraphicsAdapterSetBold(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetItalicSlope(Adapter, 0, 3);
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 0);
    HKHubModuleGraphicsAdapterSetAnimationFilter(Adapter, 0, 0);
    
    HKHubModuleGraphicsAdapterStaticGlyphSet(1, 1, 1, 0, (uint8_t[]){
        0xff, 0x02, 0x04, 0x08, 0x10, 0x20, 0x7f, 0x02, 0x04, 0x08, 0x10, 0x20, 0x60, 0x40, 0x81, 0x02,
        0x04, 0x0f, 0xe0, 0x40, 0x81, 0x02, 0x04, 0x0f, 0xf0
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet(2, 1, 1, 1, (uint8_t[]){
        0x55, 0x55, 0x00, 0x04, 0x00, 0x10, 0x00, 0x40, 0x01, 0x00, 0x04, 0x00, 0x15, 0x55, 0xaa, 0xa6,
        0xaa, 0x9a, 0xaa, 0x6a, 0xa9, 0xaa, 0xa6, 0xaa, 0x97, 0xff, 0xdf, 0xff, 0x7f, 0xfd, 0xff, 0xf7,
        0xff, 0xdf, 0xff, 0x55, 0x54, 0x00, 0x10, 0x00, 0x40, 0x01, 0x00, 0x04, 0x00, 0x10, 0x00, 0x55,
        0x55
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet(3, 1, 1, 2, (uint8_t[]){
        0x24, 0x92, 0x49, 0x00, 0x00, 0x08, 0x00, 0x00, 0x40, 0x00, 0x02, 0x00, 0x00, 0x10, 0x00, 0x00,
        0x80, 0x00, 0x04, 0x92, 0x49, 0x49, 0x24, 0x8a, 0x49, 0x24, 0x52, 0x49, 0x22, 0x92, 0x49, 0x14,
        0x92, 0x48, 0xa4, 0x92, 0x44, 0xb6, 0xdb, 0x65, 0xb6, 0xdb, 0x2d, 0xb6, 0xd9, 0x6d, 0xb6, 0xcb,
        0x6d, 0xb6, 0x5b, 0x6d, 0xb2, 0x49, 0x24, 0xc9, 0x24, 0x86, 0x49, 0x24, 0x32, 0x49, 0x21, 0x92,
        0x49, 0x0c, 0x92, 0x48, 0x64, 0x92, 0x42, 0x49, 0x24, 0x90
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet(4, 1, 1, 3, (uint8_t[]){
        0x11, 0x11, 0x11, 0x11, 0x00, 0x00, 0x00, 0x10, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x10, 0x00,
        0x00, 0x01, 0x00, 0x00, 0x00, 0x10, 0x00, 0x00, 0x01, 0x11, 0x11, 0x11, 0x22, 0x22, 0x22, 0x12,
        0x22, 0x22, 0x21, 0x22, 0x22, 0x22, 0x12, 0x22, 0x22, 0x21, 0x22, 0x22, 0x22, 0x12, 0x22, 0x22,
        0x21, 0x13, 0x33, 0x33, 0x31, 0x33, 0x33, 0x33, 0x13, 0x33, 0x33, 0x31, 0x33, 0x33, 0x33, 0x13,
        0x33, 0x33, 0x31, 0x33, 0x33, 0x33, 0x11, 0x11, 0x11, 0x14, 0x44, 0x44, 0x41, 0x44, 0x44, 0x44,
        0x14, 0x44, 0x44, 0x41, 0x44, 0x44, 0x44, 0x14, 0x44, 0x44, 0x41, 0x44, 0x44, 0x44, 0x11, 0x11,
        0x11, 0x11
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet(5, 1, 1, 4, (uint8_t[]){
        0x08, 0x42, 0x10, 0x84, 0x21, 0x00, 0x00, 0x00, 0x00, 0x20, 0x00, 0x00, 0x00, 0x04, 0x00, 0x00,
        0x00, 0x00, 0x80, 0x00, 0x00, 0x00, 0x10, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x42,
        0x10, 0x84, 0x21, 0x10, 0x84, 0x21, 0x08, 0x22, 0x10, 0x84, 0x21, 0x04, 0x42, 0x10, 0x84, 0x20,
        0x88, 0x42, 0x10, 0x84, 0x11, 0x08, 0x42, 0x10, 0x82, 0x21, 0x08, 0x42, 0x10, 0x42, 0x31, 0x8c,
        0x63, 0x18, 0x46, 0x31, 0x8c, 0x63, 0x08, 0xc6, 0x31, 0x8c, 0x61, 0x18, 0xc6, 0x31, 0x8c, 0x23,
        0x18, 0xc6, 0x31, 0x84, 0x63, 0x18, 0xc6, 0x30, 0x84, 0x21, 0x08, 0x42, 0x42, 0x10, 0x84, 0x20,
        0x48, 0x42, 0x10, 0x84, 0x09, 0x08, 0x42, 0x10, 0x81, 0x21, 0x08, 0x42, 0x10, 0x24, 0x21, 0x08,
        0x42, 0x04, 0x84, 0x21, 0x08, 0x40, 0x84, 0x21, 0x08, 0x42, 0x10
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet(6, 1, 1, 5, (uint8_t[]){
        0x04, 0x10, 0x41, 0x04, 0x10, 0x41, 0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00, 0x00,
        0x10, 0x00, 0x00, 0x00, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x40, 0x00, 0x00, 0x00, 0x00, 0x10, 0x41, 0x04, 0x10, 0x41, 0x08, 0x20, 0x82, 0x08, 0x20, 0x42,
        0x08, 0x20, 0x82, 0x08, 0x10, 0x82, 0x08, 0x20, 0x82, 0x04, 0x20, 0x82, 0x08, 0x20, 0x81, 0x08,
        0x20, 0x82, 0x08, 0x20, 0x42, 0x08, 0x20, 0x82, 0x08, 0x10, 0x43, 0x0c, 0x30, 0xc3, 0x0c, 0x10,
        0xc3, 0x0c, 0x30, 0xc3, 0x04, 0x30, 0xc3, 0x0c, 0x30, 0xc1, 0x0c, 0x30, 0xc3, 0x0c, 0x30, 0x43,
        0x0c, 0x30, 0xc3, 0x0c, 0x10, 0xc3, 0x0c, 0x30, 0xc3, 0x04, 0x10, 0x41, 0x04, 0x10, 0x44, 0x10,
        0x41, 0x04, 0x10, 0x11, 0x04, 0x10, 0x41, 0x04, 0x04, 0x41, 0x04, 0x10, 0x41, 0x01, 0x10, 0x41,
        0x04, 0x10, 0x40, 0x44, 0x10, 0x41, 0x04, 0x10, 0x11, 0x04, 0x10, 0x41, 0x04, 0x04, 0x10, 0x41,
        0x04, 0x10, 0x41
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet(7, 1, 1, 6, (uint8_t[]){
        0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x81, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x08, 0x10, 0x20, 0x40,
        0x81, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x82, 0x04, 0x08, 0x10, 0x20, 0x40, 0x41, 0x02, 0x04,
        0x08, 0x10, 0x20, 0x20, 0x81, 0x02, 0x04, 0x08, 0x10, 0x10, 0x40, 0x81, 0x02, 0x04, 0x08, 0x08,
        0x20, 0x40, 0x81, 0x02, 0x04, 0x04, 0x08, 0x30, 0x60, 0xc1, 0x83, 0x06, 0x04, 0x18, 0x30, 0x60,
        0xc1, 0x83, 0x02, 0x0c, 0x18, 0x30, 0x60, 0xc1, 0x81, 0x06, 0x0c, 0x18, 0x30, 0x60, 0xc0, 0x83,
        0x06, 0x0c, 0x18, 0x30, 0x60, 0x41, 0x83, 0x06, 0x0c, 0x18, 0x30, 0x20, 0x40, 0x81, 0x02, 0x04,
        0x08, 0x40, 0x81, 0x02, 0x04, 0x08, 0x04, 0x20, 0x40, 0x81, 0x02, 0x04, 0x02, 0x10, 0x20, 0x40,
        0x81, 0x02, 0x01, 0x08, 0x10, 0x20, 0x40, 0x81, 0x00, 0x84, 0x08, 0x10, 0x20, 0x40, 0x80, 0x42,
        0x04, 0x08, 0x10, 0x20, 0x40, 0x20, 0x40, 0x81, 0x02, 0x04, 0x08, 0x10
    }, 1);
    HKHubModuleGraphicsAdapterStaticGlyphSet(8, 1, 1, 7, (uint8_t[]){
        1, 1, 1, 1, 1, 1, 1,
        1, 0, 0, 0, 0, 0, 0,
        1, 0, 0, 0, 0, 0, 0,
        1, 0, 0, 0, 0, 0, 0,
        1, 0, 0, 0, 0, 0, 0,
        1, 0, 0, 0, 0, 0, 0,
        1, 0, 0, 0, 0, 0, 0,
    
        1, 1, 1, 1, 1, 1, 1,
        2, 2, 2, 2, 2, 2, 1,
        2, 2, 2, 2, 2, 2, 1,
        2, 2, 2, 2, 2, 2, 1,
        2, 2, 2, 2, 2, 2, 1,
        2, 2, 2, 2, 2, 2, 1,
        2, 2, 2, 2, 2, 2, 1,
    
        1, 3, 3, 3, 3, 3, 3,
        1, 3, 3, 3, 3, 3, 3,
        1, 3, 3, 3, 3, 3, 3,
        1, 3, 3, 3, 3, 3, 3,
        1, 3, 3, 3, 3, 3, 3,
        1, 3, 3, 3, 3, 3, 3,
        1, 1, 1, 1, 1, 1, 1,
    
        4, 4, 4, 4, 4, 4, 1,
        4, 4, 4, 4, 4, 4, 1,
        4, 4, 4, 4, 4, 4, 1,
        4, 4, 4, 4, 4, 4, 1,
        4, 4, 4, 4, 4, 4, 1,
        4, 4, 4, 4, 4, 4, 1,
        1, 1, 1, 1, 1, 1, 1,
    }, 1);
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 0, 0, 19, 19);
    
    const char *Text = "\x01\x02\x03\x04\x05\x06\x07\x08";
    
#pragma mark top left
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvance(Adapter, 0, TRUE);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 2);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, TRUE);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 4);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, FALSE);
    [self drawChars: "\x02" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, TRUE);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, FALSE);
    [self drawChars: "\x02" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 0);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 9, 4);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 1, 0);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 11, 5);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 1, 1);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 12, 5);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 1);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 14, 4);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 14, 5);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 15, 4);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 1, 6, 2, 1);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 5);
    [self drawChars: "\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 5, 6, 2, 0);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 5, 6);
    [self drawChars: "\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 1, 7, 2, 1);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 6);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, TRUE);
    [self drawChars: "\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 9, 6, 2, 0);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 9, 6);
    [self drawChars: "\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 0, 8, 5, 1);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 1, 8);
    [self drawChars: "\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, TRUE);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 6, 8, 5, 1);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 7, 8);
    [self drawChars: "\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 12, 8, 5, 3);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 13, 8);
    [self drawChars: "\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 0, 12, 5, 3);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 1, 12);
    [self drawChars: "\x03\x03\x03\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 6, 12, 5, 2);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 7, 12);
    [self drawChars: "\x03\x03\x03\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 12, 12, 5, 3);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 13, 12);
    HKHubModuleGraphicsAdapterSetCursorWrapOffset(Adapter, 0, 2, 1);
    [self drawChars: "\x03\x03\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 1, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvanceSource(Adapter, 0, -1, 0);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 12, 17, 5, 3);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 17, 17);
    [self drawChars: "\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, TRUE);
    HKHubModuleGraphicsAdapterSetCursorWrapOffset(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorWrapSource(Adapter, 0, 0, 1);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 5, 17, 5, 3);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 10, 17);
    [self drawChars: "\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorWrapOffset(Adapter, 0, -1, 0);
    HKHubModuleGraphicsAdapterSetCursorWrapSource(Adapter, 0, 0, -1);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 0, 17, 3, 3);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 3, 19);
    [self drawChars: "\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    
#pragma mark bottom right
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 1, 1);
    HKHubModuleGraphicsAdapterSetCursorAdvance(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursorAdvanceSource(Adapter, 0, -1, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvanceOffset(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursorWrapSource(Adapter, 0, 0, -1);
    HKHubModuleGraphicsAdapterSetCursorWrapOffset(Adapter, 0, 0, 0);
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 20, 20, 19, 19);
    
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39, 39);
    HKHubModuleGraphicsAdapterSetCursorAdvance(Adapter, 0, TRUE);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39, 39 - 2);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, TRUE);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39, 39 - 4);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, FALSE);
    [self drawChars: "\x02" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, TRUE);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, FALSE);
    [self drawChars: "\x02" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 1, 1);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 9, 39 - 4);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 1);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 11, 39 - 5);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 0);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 12, 39 - 5);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 1, 0);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 1, 1);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 14, 39 - 4);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 14, 39 - 5);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 15, 39 - 4);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 39 - 3, 39 - 7, 2, 1);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 0, 39 - 5);
    [self drawChars: "\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];

    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 39 - 7, 39 - 6, 2, 0);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 5, 39 - 6);
    [self drawChars: "\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 39 - 3, 39 - 8, 2, 1);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 0, 39 - 6);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, TRUE);
    [self drawChars: "\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 39 - 11, 39 - 6, 2, 0);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 9, 39 - 6);
    [self drawChars: "\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 39 - 5, 39 - 9, 5, 1);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 1, 39 - 8);
    [self drawChars: "\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, TRUE);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 39 - 11, 39 - 9, 5, 1);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 7, 39 - 8);
    [self drawChars: "\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 39 - 17, 39 - 11, 5, 3);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 13, 39 - 8);
    [self drawChars: "\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 39 - 5, 39 - 15, 5, 3);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 1, 39 - 12);
    [self drawChars: "\x03\x03\x03\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 39 - 11, 39 - 14, 5, 2);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 7, 39 - 12);
    [self drawChars: "\x03\x03\x03\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 39 - 17, 39 - 15, 5, 3);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 13, 39 - 12);
    HKHubModuleGraphicsAdapterSetCursorWrapOffset(Adapter, 0, -2, -1);
    [self drawChars: "\x03\x03\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 1);
    HKHubModuleGraphicsAdapterSetCursorAdvanceSource(Adapter, 0, 1, 0);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 39 - 17, 39 - 20, 5, 3);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 17, 39 - 17);
    [self drawChars: "\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, TRUE);
    HKHubModuleGraphicsAdapterSetCursorWrapOffset(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorWrapSource(Adapter, 0, 0, -1);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 39 - 10, 39 - 20, 5, 3);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 10, 39 - 17);
    [self drawChars: "\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorWrapOffset(Adapter, 0, 1, 0);
    HKHubModuleGraphicsAdapterSetCursorWrapSource(Adapter, 0, 0, 1);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 39 - 3, 39 - 20, 3, 3);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 39 - 3, 39 - 19);
    [self drawChars: "\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
#pragma mark top right
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvance(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursorAdvanceSource(Adapter, 0, 0, 1);
    HKHubModuleGraphicsAdapterSetCursorAdvanceOffset(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursorWrapSource(Adapter, 0, 1, 0);
    HKHubModuleGraphicsAdapterSetCursorWrapOffset(Adapter, 0, 0, 0);
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 19, 0, 19, 19);
    
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 19, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvance(Adapter, 0, TRUE);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 21, 0);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, TRUE);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 23, 0);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, FALSE);
    [self drawChars: "\x02" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, TRUE);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, FALSE);
    [self drawChars: "\x02" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 0);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 23, 9);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 1);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 24, 11);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 1, 1);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 24, 12);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 1, 0);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 23, 14);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 24, 14);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 23, 15);
    [self drawChars: "\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 25, 1, 1, 2);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 24, 0);
    [self drawChars: "\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 25, 5, 0, 2);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 25, 5);
    [self drawChars: "\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 26, 1, 1, 2);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 25, 0);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, TRUE);
    [self drawChars: "\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 25, 9, 0, 2);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 25, 9);
    [self drawChars: "\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 27, 0, 1, 5);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 27, 1);
    [self drawChars: "\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, TRUE);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 27, 6, 1, 5);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 27, 7);
    [self drawChars: "\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 27, 12, 3, 5);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 27, 13);
    [self drawChars: "\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 31, 0, 3, 5);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 31, 1);
    [self drawChars: "\x03\x03\x03\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 31, 6, 2, 5);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 31, 7);
    [self drawChars: "\x03\x03\x03\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 31, 12, 3, 5);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 31, 13);
    HKHubModuleGraphicsAdapterSetCursorWrapOffset(Adapter, 0, 1, 2);
    [self drawChars: "\x03\x03\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 1);
    HKHubModuleGraphicsAdapterSetCursorAdvanceSource(Adapter, 0, 0, -1);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 36, 12, 3, 5);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 36, 17);
    [self drawChars: "\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, TRUE);
    HKHubModuleGraphicsAdapterSetCursorWrapOffset(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorWrapSource(Adapter, 0, 1, 0);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 36, 5, 3, 5);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 36, 10);
    [self drawChars: "\x03\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorWrapOffset(Adapter, 0, 0, -1);
    HKHubModuleGraphicsAdapterSetCursorWrapSource(Adapter, 0, -1, 0);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 36, 0, 3, 3);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 38, 3);
    [self drawChars: "\x03\x03\x03" AtLayer: 0 ForAdapter: Adapter];
    
#pragma mark bottom left
    HKHubModuleGraphicsAdapterStaticGlyphSet(255, 2, 2, 7, (uint8_t[]){
        1, 1, 1, 1, 1, 1, 1,
        1, 0, 0, 0, 0, 0, 0,
        1, 0, 0, 0, 0, 0, 0,
        1, 0, 0, 0, 0, 0, 0,
        1, 0, 0, 0, 0, 0, 0,
        1, 0, 0, 0, 0, 0, 0,
        1, 0, 0, 0, 0, 0, 0,
        
        1, 1, 1, 1, 1, 1, 1,
        2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2,
        2, 2, 2, 2, 2, 2, 2,
        
        1, 1, 1, 1, 1, 1, 1,
        3, 3, 3, 3, 3, 3, 1,
        3, 3, 3, 3, 3, 3, 1,
        3, 3, 3, 3, 3, 3, 1,
        3, 3, 3, 3, 3, 3, 1,
        3, 3, 3, 3, 3, 3, 1,
        3, 3, 3, 3, 3, 3, 1,
        
        1, 3, 3, 3, 3, 3, 3,
        1, 3, 3, 3, 3, 3, 3,
        1, 3, 3, 3, 3, 3, 3,
        1, 3, 3, 3, 3, 3, 3,
        1, 3, 3, 3, 3, 3, 3,
        1, 3, 3, 3, 3, 3, 3,
        1, 3, 3, 3, 3, 3, 3,
        
        1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1,
        1, 1, 1, 1, 1, 1, 1,
        
        4, 4, 4, 4, 4, 4, 1,
        4, 4, 4, 4, 4, 4, 1,
        4, 4, 4, 4, 4, 4, 1,
        4, 4, 4, 4, 4, 4, 1,
        4, 4, 4, 4, 4, 4, 1,
        4, 4, 4, 4, 4, 4, 1,
        4, 4, 4, 4, 4, 4, 1,
        
        1, 2, 2, 2, 2, 2, 2,
        1, 2, 2, 2, 2, 2, 2,
        1, 2, 2, 2, 2, 2, 2,
        1, 2, 2, 2, 2, 2, 2,
        1, 2, 2, 2, 2, 2, 2,
        1, 2, 2, 2, 2, 2, 2,
        1, 1, 1, 1, 1, 1, 1,
        
        4, 4, 4, 4, 4, 4, 4,
        4, 4, 4, 4, 4, 4, 4,
        4, 4, 4, 4, 4, 4, 4,
        4, 4, 4, 4, 4, 4, 4,
        4, 4, 4, 4, 4, 4, 4,
        4, 4, 4, 4, 4, 4, 4,
        1, 1, 1, 1, 1, 1, 1,
        
        0, 0, 0, 0, 0, 0, 1,
        0, 0, 0, 0, 0, 0, 1,
        0, 0, 0, 0, 0, 0, 1,
        0, 0, 0, 0, 0, 0, 1,
        0, 0, 0, 0, 0, 0, 1,
        0, 0, 0, 0, 0, 0, 1,
        1, 1, 1, 1, 1, 1, 1,
    }, 1);
    
    HKHubModuleGraphicsAdapterSetCursorAdvance(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, FALSE);
    
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 1, 22, 0, 0);
    
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 21);
    [self drawChars: "\xff" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorAdvance(Adapter, 0, TRUE);
    HKHubModuleGraphicsAdapterSetCursorAdvanceSource(Adapter, 0, 1, 0);
    HKHubModuleGraphicsAdapterSetBold(Adapter, 0, TRUE);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 0, 24, 5, 7);
    
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 24);
    [self drawChars: "\x02" "ab\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 26);
    [self drawChars: "ab" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetBold(Adapter, 0, FALSE);
    [self drawChars: "c" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetBold(Adapter, 0, TRUE);
    [self drawChars: "de\x03" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 28);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, TRUE);
    [self drawChars: "abcdef" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 30);
    HKHubModuleGraphicsAdapterSetBold(Adapter, 0, FALSE);
    [self drawChars: "abcdef" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 0, 32, 17, 4);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 32);
    HKHubModuleGraphicsAdapterSetBold(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 0);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 1);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 2);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 3);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 4);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 5);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 6);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 7);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 8);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 0);
    [self drawChars: "y" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 1);
    [self drawChars: "y" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 2);
    [self drawChars: "y" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 3);
    [self drawChars: "y" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 4);
    [self drawChars: "y" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 5);
    [self drawChars: "y" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 6);
    [self drawChars: "y" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 7);
    [self drawChars: "y" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 8);
    [self drawChars: "y" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 33);
    HKHubModuleGraphicsAdapterSetAnimationFilter(Adapter, 0, 1);
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 0);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 1);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 2);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 3);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 4);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 5);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 6);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 7);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 34);
    HKHubModuleGraphicsAdapterSetAnimationFilter(Adapter, 0, 2);
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 0);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 1);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 2);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 3);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 4);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 5);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 6);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 7);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 35);
    HKHubModuleGraphicsAdapterSetAnimationFilter(Adapter, 0, 3);
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 0);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 1);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 2);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 3);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 4);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 5);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 6);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 7);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 36);
    HKHubModuleGraphicsAdapterSetAnimationFilter(Adapter, 0, 4);
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 0);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 1);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 2);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 3);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 4);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 5);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 6);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 7);
    [self drawChars: "x" AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetGlyphBitmap(Adapter, 'y', 0, 0, 7, (uint8_t[]){
        0x81,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 4, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        
        0x42,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 4, 4, 4, 0, 0,
        0, 0, 4, 4, 4, 0, 0,
        0, 0, 4, 4, 4, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0
    }, 2);
    
    HKHubModuleGraphicsAdapterSetGlyphBitmap(Adapter, 'x', 0, 0, 7, (uint8_t[]){
        0x81,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 1, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        
        0x42,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 1, 1, 1, 0, 0,
        0, 0, 1, 2, 1, 0, 0,
        0, 0, 1, 1, 1, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0,
        
        0x24,
        0, 0, 0, 0, 0, 0, 0,
        0, 1, 1, 1, 1, 1, 0,
        0, 1, 2, 2, 2, 1, 0,
        0, 1, 2, 3, 2, 1, 0,
        0, 1, 2, 2, 2, 1, 0,
        0, 1, 1, 1, 1, 1, 0,
        0, 0, 0, 0, 0, 0, 0,
        
        0x18,
        1, 1, 1, 1, 1, 1, 1,
        1, 2, 2, 2, 2, 2, 1,
        1, 2, 3, 3, 3, 2, 1,
        1, 2, 3, 4, 3, 2, 1,
        1, 2, 3, 3, 3, 2, 1,
        1, 2, 2, 2, 2, 2, 1,
        1, 1, 1, 1, 1, 1, 1
    }, 4);
    
    HKHubModuleGraphicsAdapterSetAttributeModifier(Adapter, 0, 0);
    HKHubModuleGraphicsAdapterSetAttributeModifier(Adapter, 1, 0);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 7, 22, 12, 10);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 7, 22);
    
    HKHubModuleGraphicsAdapterDrawRef(Adapter, 0, 0, 0, 2, 1, 1);
    HKHubModuleGraphicsAdapterDrawRef(Adapter, 0, 0, 0, 2, 1, 2);
    
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 7, 24);
    HKHubModuleGraphicsAdapterDrawRef(Adapter, 0, 0, 0, 5, 1, 1);
    
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 1, 0);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 12, 26);
    HKHubModuleGraphicsAdapterDrawRef(Adapter, 0, 0, 0, 5, 1, 1);
    
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 9, 28);
    HKHubModuleGraphicsAdapterDrawRef(Adapter, 0, 0, 0, 5, 1, 1);
    
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, TRUE);
    HKHubModuleGraphicsAdapterSetBold(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetPaletteOffset(Adapter, 0, 2);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 14, 22);
    HKHubModuleGraphicsAdapterDrawRef(Adapter, 0, 0, 0, 5, 1, 1);
    
    HKHubModuleGraphicsAdapterSetAttributeModifier(Adapter, 0, 1);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 14, 24);
    HKHubModuleGraphicsAdapterDrawRef(Adapter, 0, 0, 0, 5, 1, 1);
    
    HKHubModuleGraphicsAdapterSetAttributeModifier(Adapter, 0, 2);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 14, 26);
    HKHubModuleGraphicsAdapterDrawRef(Adapter, 0, 0, 0, 5, 1, 1);
    
    HKHubModuleGraphicsAdapterSetAttributeModifier(Adapter, 0, 3);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 14, 28);
    HKHubModuleGraphicsAdapterDrawRef(Adapter, 0, 0, 0, 5, 1, 1);
    
    [self drawChars: "abc" AtLayer: 1 ForAdapter: Adapter];
    [self drawChars: "def" AtLayer: 2 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterDrawRef(Adapter, 1, 2, 0, 0, 1, 2);
    HKHubModuleGraphicsAdapterSetBold(Adapter, 1, TRUE);
    HKHubModuleGraphicsAdapterDrawRef(Adapter, 1, 1, 0, 0, 1, 2);
    HKHubModuleGraphicsAdapterSetPaletteOffset(Adapter, 1, 1);
    HKHubModuleGraphicsAdapterDrawRef(Adapter, 1, 0, 0, 0, 1, 2);
    
    [self assertImage: @"blit-0" MatchesViewport: 0 ForAdapter: Adapter];
    [self assertImage: @"blit-8" MatchesViewport: 8 ForAdapter: Adapter];
    [self assertImage: @"blit-16" MatchesViewport: 16 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterNextFrame(Adapter);
    [self assertImage: @"blit-24-frame-1" MatchesViewport: 24 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterNextFrame(Adapter);
    [self assertImage: @"blit-24-frame-2" MatchesViewport: 24 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterNextFrame(Adapter);
    [self assertImage: @"blit-24-frame-3" MatchesViewport: 24 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterNextFrame(Adapter);
    [self assertImage: @"blit-24-frame-4" MatchesViewport: 24 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterNextFrame(Adapter);
    [self assertImage: @"blit-24-frame-5" MatchesViewport: 24 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterNextFrame(Adapter);
    [self assertImage: @"blit-24-frame-6" MatchesViewport: 24 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterNextFrame(Adapter);
    [self assertImage: @"blit-24-frame-7" MatchesViewport: 24 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterNextFrame(Adapter);
    [self assertImage: @"blit-24-frame-8" MatchesViewport: 24 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorVisibility(Adapter, 0, 0xff);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 7, 22);
    [self assertImage: @"blit-32-cursor-7-22" MatchesViewport: 32 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 14, 22);
    [self assertImage: @"blit-32-cursor-14-22" MatchesViewport: 32 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorVisibility(Adapter, 0, 0xff | HKHubModuleGraphicsAdapterCursorGlyphItalicFlag);
    [self assertImage: @"blit-32-cursor-14-22-italic" MatchesViewport: 32 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorVisibility(Adapter, 0, 0xff | (1ULL << HKHubModuleGraphicsAdapterCursorGlyphPaletteOffsetIndex));
    [self assertImage: @"blit-32-cursor-14-22-colour-offset" MatchesViewport: 32 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterCharacter Characters[3][12];
    HKHubModuleGraphicsAdapterRead(Adapter, 0, 3, 24, 11, 2, (HKHubModuleGraphicsAdapterCharacter*)Characters);
    
    XCTAssertEqual(Characters[0][0], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'b'));
    XCTAssertEqual(Characters[1][0], ((1 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'b'));
    
    XCTAssertEqual(Characters[0][1], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 3));
    XCTAssertEqual(Characters[1][1], ((1 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 3));
    XCTAssertEqual(Characters[0][2], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (1 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 3));
    XCTAssertEqual(Characters[1][2], ((1 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (1 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 3));
    
    XCTAssertEqual(Characters[0][3], 0);
    XCTAssertEqual(Characters[1][3], 0);
    
    XCTAssertEqual(Characters[0][4], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'a'));
    XCTAssertEqual(Characters[1][4], ((1 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'a'));
    
    XCTAssertEqual(Characters[0][5], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'b'));
    XCTAssertEqual(Characters[1][5], ((1 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'b'));
    
    XCTAssertEqual(Characters[0][6], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'c'));
    XCTAssertEqual(Characters[1][6], ((1 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'c'));
    
    XCTAssertEqual(Characters[0][7], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'f'));
    XCTAssertEqual(Characters[1][7], ((1 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'f'));
    
    XCTAssertEqual(Characters[0][8], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'e'));
    XCTAssertEqual(Characters[1][8], ((1 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'e'));
    
    XCTAssertEqual(Characters[0][9], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'd'));
    XCTAssertEqual(Characters[1][9], ((1 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'd'));
    
    XCTAssertEqual(Characters[0][10], 0);
    XCTAssertEqual(Characters[1][10], 0);
    
    XCTAssertEqual(Characters[0][11], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'a'));
    XCTAssertEqual(Characters[1][11], ((1 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'a'));
    
    XCTAssertEqual(Characters[2][0], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'd'));
    
    XCTAssertEqual(Characters[2][1], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'e'));
    
    XCTAssertEqual(Characters[2][2], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 3));
    
    XCTAssertEqual(Characters[2][3], 0);
    
    XCTAssertEqual(Characters[2][4], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'a'));
    
    XCTAssertEqual(Characters[2][5], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'b'));
    
    XCTAssertEqual(Characters[2][6], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'c'));
    
    XCTAssertEqual(Characters[2][7], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'f'));
    
    XCTAssertEqual(Characters[2][8], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'e'));
    
    XCTAssertEqual(Characters[2][9], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'd'));
    
    XCTAssertEqual(Characters[2][10], 0);
    
    XCTAssertEqual(Characters[2][11], ((0 << HKHubModuleGraphicsAdapterCharacterPositionTIndex) | (0 << HKHubModuleGraphicsAdapterCharacterPositionSIndex) | 'a'));
    
    HKHubModuleDestroy(Adapter);
}

-(void) testTabProgram
{
    HKHubModule Adapter = HKHubModuleGraphicsAdapterCreate(CC_STD_ALLOCATOR);
    
    HKHubModuleGraphicsAdapterSetViewport(Adapter, 0, 0, 0, 39, 39);
    
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorVisibility(Adapter, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvance(Adapter, 0, TRUE);
    HKHubModuleGraphicsAdapterSetCursorAdvanceSource(Adapter, 0, 1, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvanceOffset(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursorWrapSource(Adapter, 0, 0, 1);
    HKHubModuleGraphicsAdapterSetCursorWrapOffset(Adapter, 0, 0, 0);
    
    HKHubModuleGraphicsAdapterSetPalettePage(Adapter, 0, 0);
    HKHubModuleGraphicsAdapterSetPaletteOffset(Adapter, 0, 0);
    HKHubModuleGraphicsAdapterSetBold(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetItalicSlope(Adapter, 0, 3);
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 0);
    HKHubModuleGraphicsAdapterSetAnimationFilter(Adapter, 0, 0);
    
    HKHubModuleGraphicsAdapterSetCursorControl(Adapter, 0, 0, '\t', 10);
    HKHubModuleGraphicsAdapterStaticGlyphSet('\t', 0, 0, 1, Glyph1x1, 1);
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 0, 0, 19, 19);
    
    const char *Text = "\t1\t12\t123\t1234\t.\t\t.";
    
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 0);
    [self drawChars: "0123456789abcdefghijklmnopqrstuvwxyz" AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_x, cursor_bounds_x, 1" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 2);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_x, cursor_bounds_x, 2" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 4);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_x, cursor_bounds_x, 3" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 6);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_x, cursor_bounds_x, 4" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 8);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_x, cursor_bounds_x, 4, 1, 2, 0x30" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 10);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_x, cursor_bounds_x, 4, 2, 2, 0, 0, 0xff, 0x10" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 12);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "ldi 0x20\nldi 2\nldi 1\nldi 0\nldi 0\ntab_program cursor_x, cursor_bounds_x, 4, 1, 2, 0x20" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 14);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, TRUE);
    [self setProgram: "tab_program cursor_x, cursor_bounds_x, 3" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 16);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 0, 20, 19, 19);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 1, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvanceSource(Adapter, 0, -1, 0);
    
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 19, 20);
    [self drawChars: "0123456789abcdefghijklmnopqrstuvwxyz" AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_x, cursor_bounds_width, 1" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 19, 22);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_x, cursor_bounds_width, 2" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 19, 24);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_x, cursor_bounds_width, 3" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 19, 26);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_x, cursor_bounds_width, 4" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 19, 28);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_x, cursor_bounds_width, 4, 1, 2, 0x30" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 19, 30);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_x, cursor_bounds_width, 4, 2, 2, 0, 0, 0xff, 0x10" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 19, 32);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "ldi 0x20\nldi 2\nldi 1\nldi 0\nldi 0\ntab_program cursor_x, cursor_bounds_width, 4, 1, 2, 0x20" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 19, 34);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, TRUE);
    [self setProgram: "tab_program cursor_x, cursor_bounds_width, 3" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 19, 36);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    
    Text = "\t!\t!@\t!@#\t!@#$\t>\t\t>";
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 20, 0, 19, 19);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 1);
    HKHubModuleGraphicsAdapterSetCursorAdvanceSource(Adapter, 0, 0, -1);
    HKHubModuleGraphicsAdapterSetCursorWrapSource(Adapter, 0, 1, 0);
    
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 20, 19);
    [self drawChars: ")!@#$%^&*(ABCDEFGHIJKLMNOPQRSTUVWXYZ" AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_y, cursor_bounds_height, 1" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 22, 19);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_y, cursor_bounds_height, 2" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 24, 19);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_y, cursor_bounds_height, 3" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 26, 19);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_y, cursor_bounds_height, 4" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 28, 19);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_y, cursor_bounds_height, 4, 1, 1, 0x29" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 30, 19);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_y, cursor_bounds_height, 4, 1, 2, 0x4f" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 32, 19);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "ldi 0x20\nldi 2\nldi 1\nldi 0\nldi 0\ntab_program cursor_y, cursor_bounds_height, 4, 1, 2, 0x20" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 34, 19);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, TRUE);
    [self setProgram: "tab_program cursor_y, cursor_bounds_height, 3" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 36, 19);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 20, 20, 19, 19);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvanceSource(Adapter, 0, 0, 1);
    
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 20, 20);
    [self drawChars: ")!@#$%^&*(ABCDEFGHIJKLMNOPQRSTUVWXYZ" AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_y, cursor_bounds_y, 1" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 22, 20);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_y, cursor_bounds_y, 2" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 24, 20);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_y, cursor_bounds_y, 3" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 26, 20);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_y, cursor_bounds_y, 4" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 28, 20);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_y, cursor_bounds_y, 4, 1, 1, 0x29" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 30, 20);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "tab_program cursor_y, cursor_bounds_y, 4, 1, 2, 0x4f" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 32, 20);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "ldi 0x20\nldi 2\nldi 1\nldi 0\nldi 0\ntab_program cursor_y, cursor_bounds_y, 4, 1, 2, 0x20" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 34, 20);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, TRUE);
    [self setProgram: "tab_program cursor_y, cursor_bounds_y, 3" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 36, 20);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    
    [self assertImage: @"tab-0" MatchesViewport: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetViewport(Adapter, 1, 250, 240, 5, 9);
    
    HKHubModuleGraphicsAdapterSetCursorVisibility(Adapter, 1, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvance(Adapter, 1, TRUE);
    HKHubModuleGraphicsAdapterSetCursorAdvanceSource(Adapter, 1, 1, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvanceOffset(Adapter, 1, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, TRUE);
    HKHubModuleGraphicsAdapterSetCursorWrapSource(Adapter, 0, 0, 1);
    HKHubModuleGraphicsAdapterSetCursorWrapOffset(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetPalettePage(Adapter, 1, 0);
    HKHubModuleGraphicsAdapterSetPaletteOffset(Adapter, 1, 0);
    HKHubModuleGraphicsAdapterSetBold(Adapter, 1, FALSE);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 1, FALSE);
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 1, 0);
    HKHubModuleGraphicsAdapterSetAnimationFilter(Adapter, 1, 0);
    HKHubModuleGraphicsAdapterSetCursorControl(Adapter, 1, 0, '\t', 10);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 1, 250, 240, 5, 14);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 1, 250, 240);
    [self setProgram: "tab_program cursor_x, cursor_bounds_x, 2, 1, 2, 0x30" WithID: 10 ForAdapter: Adapter];
    [self drawChars: "\t1\t12\t123\t1234\t123456\t1" AtLayer: 1 ForAdapter: Adapter];
    
    [self assertImage: @"tab-1" MatchesViewport: 1 ForAdapter: Adapter];
    
    HKHubModuleDestroy(Adapter);
}

-(void) testNewlineProgram
{
    HKHubModule Adapter = HKHubModuleGraphicsAdapterCreate(CC_STD_ALLOCATOR);
    
    HKHubModuleGraphicsAdapterSetViewport(Adapter, 0, 0, 0, 40, 42);
    
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorVisibility(Adapter, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvance(Adapter, 0, TRUE);
    HKHubModuleGraphicsAdapterSetCursorAdvanceSource(Adapter, 0, 1, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvanceOffset(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 0, FALSE);
    
    HKHubModuleGraphicsAdapterSetPalettePage(Adapter, 0, 0);
    HKHubModuleGraphicsAdapterSetPaletteOffset(Adapter, 0, 0);
    HKHubModuleGraphicsAdapterSetBold(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 0, FALSE);
    HKHubModuleGraphicsAdapterSetItalicSlope(Adapter, 0, 3);
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 0, 0);
    HKHubModuleGraphicsAdapterSetAnimationFilter(Adapter, 0, 0);
    
    HKHubModuleGraphicsAdapterSetCursorControl(Adapter, 0, 0, '\n', 10);
    HKHubModuleGraphicsAdapterStaticGlyphSet('\n', 0, 0, 1, Glyph1x1, 1);
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 0, 0, 24, 24);
    
    const char *Text = "\n1\n12\n123\n1234\n.\n\n.";
    
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 0);
    [self drawChars: "0123456789abcdefghijklmnopqrstuvwxyz" AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "newline_program cursor_x, cursor_bounds_width, cursor_y, 1" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 0, 2, 4, 24);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 2);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "newline_program cursor_x, cursor_bounds_width, cursor_y, 2" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 5, 2, 4, 24);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 5, 2);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "newline_program cursor_x, cursor_bounds_width, cursor_y, 2, 1, 2, 0x30" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 10, 2, 4, 24);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 10, 2);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "newline_program cursor_x, cursor_bounds_width, cursor_y, 2, 2, 2, 0, 0, 0xff, 0x10" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 15, 2, 4, 24);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 15, 2);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "ldi 0x20\nldi 2\nldi 1\nldi 0\nldi 0\nnewline_program cursor_x, cursor_bounds_width, cursor_y, 2, 1, 2, 0x39" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 20, 2, 4, 24);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 20, 2);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 16, 25, 24, 24);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 1, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvanceSource(Adapter, 0, -1, 0);
    
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 40, 25);
    [self drawChars: "0123456789abcdefghijklmnopqrstuvwxyz" AtLayer: 0 ForAdapter: Adapter];
    
    [self setProgram: "newline_program cursor_x, cursor_bounds_x, cursor_y, 1" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 36, 27, 4, 24);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 40, 27);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "newline_program cursor_x, cursor_bounds_x, cursor_y, 2" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 31, 27, 4, 24);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 35, 27);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "newline_program cursor_x, cursor_bounds_x, cursor_y, 2, 1, 2, 0x30" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 26, 27, 4, 24);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 30, 27);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "newline_program cursor_x, cursor_bounds_x, cursor_y, 2, 2, 2, 0, 0, 0xff, 0x10" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 21, 27, 4, 24);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 25, 27);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "ldi 0x20\nldi 2\nldi 1\nldi 0\nldi 0\nnewline_program cursor_x, cursor_bounds_x, cursor_y, 2, 1, 2, 0x39" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 16, 27, 4, 24);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 20, 27);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    
    Text = "\n!\n!@\n!@#\n!@#$\n>\n\n>";
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 25, 0, 24, 24);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 1);
    HKHubModuleGraphicsAdapterSetCursorAdvanceSource(Adapter, 0, 0, -1);
    
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 25, 24);
    [self drawChars: ")!@#$%^&*(ABCDEFGHIJKLMN+PQRSTUVWXYZ" AtLayer: 0 ForAdapter: Adapter];
    
    [self setProgram: "newline_program cursor_y, cursor_bounds_y, cursor_x, 1" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 26, 20, 24, 4);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 26, 24);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "newline_program cursor_y, cursor_bounds_y, cursor_x, 2" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 26, 15, 24, 4);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 26, 19);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "newline_program cursor_y, cursor_bounds_y, cursor_x, 2, 1, 1, 0x29" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 26, 10, 24, 4);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 26, 14);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "newline_program cursor_y, cursor_bounds_y, cursor_x, 2, 1, 2, 0x4f" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 26, 5, 24, 4);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 26, 9);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "ldi 0x20\nldi 2\nldi 1\nldi 0\nldi 0\nnewline_program cursor_y, cursor_bounds_y, cursor_x, 2, 1, 2, 0x39" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 26, 0, 24, 4);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 26, 4);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 0, 18, 24, 24);
    HKHubModuleGraphicsAdapterSetCursorOrigin(Adapter, 0, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvanceSource(Adapter, 0, 0, 1);
    
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 0, 18);
    [self drawChars: ")!@#$%^&*(ABCDEFGHIJKLMN+PQRSTUVWXYZ" AtLayer: 0 ForAdapter: Adapter];
    
    [self setProgram: "newline_program cursor_y, cursor_bounds_height, cursor_x, 1" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 1, 18, 24, 4);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 1, 18);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "newline_program cursor_y, cursor_bounds_height, cursor_x, 2" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 1, 23, 24, 4);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 1, 23);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "newline_program cursor_y, cursor_bounds_height, cursor_x, 2, 1, 1, 0x29" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 1, 28, 24, 4);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 1, 28);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "newline_program cursor_y, cursor_bounds_height, cursor_x, 2, 1, 2, 0x4f" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 1, 33, 24, 4);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 1, 33);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    [self setProgram: "ldi 0x20\nldi 2\nldi 1\nldi 0\nldi 0\nnewline_program cursor_y, cursor_bounds_height, cursor_x, 2, 1, 2, 0x39" WithID: 10 ForAdapter: Adapter];
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 0, 1, 38, 24, 4);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 0, 1, 38);
    [self drawChars: Text AtLayer: 0 ForAdapter: Adapter];
    
    [self assertImage: @"newline-0" MatchesViewport: 0 ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterSetViewport(Adapter, 1, 250, 240, 5, 14);
    
    HKHubModuleGraphicsAdapterSetCursorVisibility(Adapter, 1, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvance(Adapter, 1, TRUE);
    HKHubModuleGraphicsAdapterSetCursorAdvanceSource(Adapter, 1, 1, 0);
    HKHubModuleGraphicsAdapterSetCursorAdvanceOffset(Adapter, 1, 0, 0);
    HKHubModuleGraphicsAdapterSetCursorWrap(Adapter, 1, FALSE);
    HKHubModuleGraphicsAdapterSetPalettePage(Adapter, 1, 0);
    HKHubModuleGraphicsAdapterSetPaletteOffset(Adapter, 1, 0);
    HKHubModuleGraphicsAdapterSetBold(Adapter, 1, FALSE);
    HKHubModuleGraphicsAdapterSetItalic(Adapter, 1, FALSE);
    HKHubModuleGraphicsAdapterSetAnimationOffset(Adapter, 1, 0);
    HKHubModuleGraphicsAdapterSetAnimationFilter(Adapter, 1, 0);
    HKHubModuleGraphicsAdapterSetCursorControl(Adapter, 1, 0, '\n', 10);
    HKHubModuleGraphicsAdapterSetCursorBounds(Adapter, 1, 250, 240, 5, 14);
    HKHubModuleGraphicsAdapterSetCursor(Adapter, 1, 250, 240);
    [self setProgram: "newline_program cursor_x, cursor_bounds_width, cursor_y, 2, 1, 2, 0x30" WithID: 10 ForAdapter: Adapter];
    [self drawChars: "\n1\n12\n123\n1234\n12345\n1" AtLayer: 1 ForAdapter: Adapter];
    
    [self assertImage: @"newline-1" MatchesViewport: 1 ForAdapter: Adapter];
    
    HKHubModuleDestroy(Adapter);
}

-(void) testProgramCycleLimit
{
    HKHubModule Adapter = HKHubModuleGraphicsAdapterCreate(CC_STD_ALLOCATOR);
    
    [self setProgram: "ldi 0\n"
                      "ldi 0xf, 0xff, 0xff, 0xff\n"
                      "rep 2\n"
                      "ldi 0xf, 0xff, 0xff, 0xff\n"
                      "rep 2\n"
                      "ldi 0xf, 0xff, 0xff, 0xff\n"
                      "rep 2\n"
                      "ldi 1\n"
                      "add\n"
                      "dup\n"
                      "ldi 0xff\n"
                      "and\n"
                      "ldi 0\n"
                      "str viewport_height\n"
                      "dup\n"
                      "ldi 8\n"
                      "swap\n"
                      "sar\n"
                      "ldi 0xff\n"
                      "and\n"
                      "ldi 0\n"
                      "str viewport_width\n"
                      "dup\n"
                      "ldi 16\n"
                      "swap\n"
                      "sar\n"
                      "ldi 0xff\n"
                      "and\n"
                      "ldi 0\n"
                      "str viewport_y\n"
                      "dup\n"
                      "ldi 24\n"
                      "swap\n"
                      "sar\n"
                      "ldi 0xff\n"
                      "and\n"
                      "ldi 0\n"
                      "str viewport_x\n"
              WithID: 0
          ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterProgramRun(Adapter, 0, 0, 0, 0, 0, 0, 0);
    
    uint8_t x0, x8, x16, x24;
    HKHubModuleGraphicsAdapterGetViewport(Adapter, 0, &x24, &x16, &x8, &x0);
    
    uint32_t x = ((uint32_t)x24 << 24) | ((uint32_t)x16 << 16) | ((uint32_t)x8 << 8) | x0;
    
    XCTAssertEqual(x, 0, @"Should have exceeded cycles before setting");
    
    
    [self setProgram: "ldi 0\n"
                      "ldi 0, 0, 0, 10\n"
                      "rep 2\n"
                      "ldi 0, 0, 0, 10\n"
                      "rep 2\n"
                      "ldi 0, 0, 0, 3\n"
                      "rep 2\n"
                      "ldi 1\n"
                      "add\n"
                      "dup\n"
                      "ldi 0xff\n"
                      "and\n"
                      "ldi 0\n"
                      "str viewport_height\n"
                      "dup\n"
                      "ldi 8\n"
                      "swap\n"
                      "sar\n"
                      "ldi 0xff\n"
                      "and\n"
                      "ldi 0\n"
                      "str viewport_width\n"
                      "dup\n"
                      "ldi 16\n"
                      "swap\n"
                      "sar\n"
                      "ldi 0xff\n"
                      "and\n"
                      "ldi 0\n"
                      "str viewport_y\n"
                      "dup\n"
                      "ldi 24\n"
                      "swap\n"
                      "sar\n"
                      "ldi 0xff\n"
                      "and\n"
                      "ldi 0\n"
                      "str viewport_x\n"
              WithID: 0
          ForAdapter: Adapter];
    
    HKHubModuleGraphicsAdapterProgramRun(Adapter, 0, 0, 0, 0, 0, 0, 0);
    
    HKHubModuleGraphicsAdapterGetViewport(Adapter, 0, &x24, &x16, &x8, &x0);
    
    x = ((uint32_t)x24 << 24) | ((uint32_t)x16 << 16) | ((uint32_t)x8 << 8) | x0;
    
    XCTAssertEqual(x, 300, @"Should have completed the program within the cycle limit");
    
    HKHubModuleDestroy(Adapter);
}

@end
