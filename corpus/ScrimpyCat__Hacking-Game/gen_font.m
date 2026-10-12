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

/*
 Setup (with homebrew):
 brew install icu4c
 clang gen_font.m -o gen_font -fmodules -L/usr/local/opt/icu4c/lib -I/usr/local/opt/icu4c/include -licuuc
 
 Usage:
 cat glyphs.map | ./gen_font
 */

@import Foundation;
@import CoreText;
@import CoreGraphics;
@import AppKit;
#import <unicode/uchar.h> // install icu4c

#define BUFFER_PAD 14

static const size_t ScaleFactor = 1;
static const size_t Cell = 7 * ScaleFactor;
static const size_t Width = Cell * 2 + BUFFER_PAD, Height = Cell * 2 + BUFFER_PAD;
static uint8_t Data[Width * 4 * Height];

#define MISSING_GLYPH_INDEX (1 << 24)
#define NON_RENDERABLE_GLYPH_INDEX 0

#define MISSING_GLYPH_BITMAP_BORDER 0
#define MISSING_GLYPH_BITMAP_BORDER_INSET_1 1
#define MISSING_GLYPH_BITMAP_QUESTION_MARK 2
#define MISSING_GLYPH_BITMAP_INVERTED_QUESTION_MARK 3

#define MISSING_GLYPH_BITMAP MISSING_GLYPH_BITMAP_BORDER_INSET_1

static const uint8_t MissingGlyphBitmapData[(((2 * Cell) * (1 * Cell)) + 7) / 8] = {
#if MISSING_GLYPH_BITMAP == MISSING_GLYPH_BITMAP_BORDER
    0xff,
    0x06,
    0x0c,
    0x18,
    0x30,
    0x60,
    0xc1,
    0x83,
    0x06,
    0x0c,
    0x18,
    0x3f,
    0xc0
#elif MISSING_GLYPH_BITMAP == MISSING_GLYPH_BITMAP_BORDER_INSET_1
    0x00,
    0xf9,
    0x12,
    0x24,
    0x48,
    0x91,
    0x22,
    0x44,
    0x89,
    0x12,
    0x27,
    0xc0,
    0x00
#elif MISSING_GLYPH_BITMAP == MISSING_GLYPH_BITMAP_QUESTION_MARK
    0x00,
    0x01,
    0x84,
    0x81,
    0x04,
    0x10,
    0x00,
    0x40,
    0x80,
    0x00,
    0x00,
    0x00
#elif MISSING_GLYPH_BITMAP == MISSING_GLYPH_BITMAP_INVERTED_QUESTION_MARK
    0xff,
    0xff,
    0xff,
    0xfe,
    0x7b,
    0x7e,
    0xfb,
    0xef,
    0xff,
    0xbf,
    0x7f,
    0xe0
#endif
};

static __strong NSMutableArray *DefaultFonts = nil;

static void InitDefaults(void)
{
    DefaultFonts = [NSMutableArray array];
    
    const float FontSize = 12.0f;
    const CFStringRef FontNames[] = {
        CFSTR("Andale Mono"),
        CFSTR("Arial Unicode MS"),
        CFSTR("GB18030 Bitmap"),
        CFSTR("Monaco"),
        CFSTR("LucidaGrande"),
        CFSTR("CourierNewPSMT"),
        CFSTR("GeezaPro"),
        CFSTR("NotoNastaliqUrdu"),
        CFSTR("Ayuthaya"),
        CFSTR("Kailasa"),
        CFSTR("PingFangSC-Regular"),
        CFSTR("PingFangTC-Regular"),
        CFSTR("PingFangTC-Regular"),
        CFSTR("PingFangSC-Regular"),
        CFSTR("PingFangHK-Regular"),
        CFSTR("PingFangSC-Regular"),
        CFSTR("HiraginoSans-W3"),
        CFSTR("HiraginoSansGB-W3"),
        CFSTR("AppleSDGothicNeo-Regular"),
        CFSTR("KohinoorBangla-Regular"),
        CFSTR("KohinoorDevanagari-Regular"),
        CFSTR("GujaratiSangamMN"),
        CFSTR("GurmukhiMN"),
        CFSTR("KannadaSangamMN"),
        CFSTR("KhmerSangamMN"),
        CFSTR("LaoSangamMN"),
        CFSTR("MalayalamSangamMN"),
        CFSTR("MyanmarSangamMN"),
        CFSTR("OriyaSangamMN"),
        CFSTR("SinhalaSangamMN"),
        CFSTR("TamilSangamMN"),
        CFSTR("KohinoorTelugu-Regular"),
        CFSTR("Mshtakan"),
        CFSTR("EuphemiaUCAS"),
        CFSTR("PlantagenetCherokee"),
        CFSTR("Kefa-Regular")
    };
    
    for (size_t Loop = 0; Loop < sizeof(FontNames) / sizeof(typeof(*FontNames)); Loop++)
    {
        CGFontRef Font = CGFontCreateWithFontName(FontNames[Loop]);
        if (Font)
        {
            [DefaultFonts addObject: @[(id)CTFontCreateWithGraphicsFont(Font, FontSize, NULL, NULL), @0.0f]];
            CGFontRelease(Font);
        }
    }
}

static NSArray *ParseFonts(FILE *Input, _Bool Verbose)
{
    NSMutableArray *Fonts = [NSMutableArray array];
    
    char FontName[256] = {0};
    for (float FontSize = 12.0f, BaselineOffset = 0.0f; fscanf(Input, "\"%255[^\"\n]\":%f,%f", FontName, &FontSize, &BaselineOffset); FontSize = 12.0f, BaselineOffset = 0.0f, fscanf(Input, "%*[ \t]"))
    {
        CGFontRef Font = CGFontCreateWithFontName((CFStringRef)[NSString stringWithUTF8String: FontName]);
        if (Font)
        {
            [Fonts addObject: @[(id)CTFontCreateWithGraphicsFont(Font, FontSize, NULL, NULL), @(BaselineOffset)]];
            CGFontRelease(Font);
        }
        
        else if (Verbose) fprintf(stderr, "No font for name: %s\n", FontName);
    }
    
    return Fonts;
}

typedef struct {
    _Bool control;
    _Bool verbose;
    _Bool image;
} Options;

static Options ParseOptions(FILE *Input, _Bool Verbose, _Bool SaveImage)
{
    Options Opts = {
        .control = FALSE,
        .verbose = Verbose,
        .image = SaveImage
    };
    
    struct {
        const char *name;
        _Bool *option;
    } Tags[] = {
        { "control", &Opts.control },
        { "verbose", &Opts.verbose },
        { "debug", &Opts.image }
    };
    
    char OptionName[256] = {0};
Scan:
    fscanf(Input, "%255[a-z]%*[ \t]", OptionName);
    
    for (size_t Loop = 0; Loop < sizeof(Tags) / sizeof(typeof(*Tags)); Loop++)
    {
        if (!strcmp(OptionName, Tags[Loop].name))
        {
            *Tags[Loop].option = TRUE;
            OptionName[0] = 0;
            goto Scan;
        }
    }
    
    return Opts;
}

typedef struct {
    FILE *file;
    size_t count;
} Resource;

static void WriteIndex(uint32_t Index, Resource *Indexes, uint32_t Char, _Bool Verbose)
{
    if (Indexes[0].count > Char)
    {
        if (Verbose) fprintf(stderr, "Invalid character range (must be ascending): U+%.4x\n", Char);
        
        return;
    }
    
    _Static_assert(sizeof(unsigned int) == sizeof(uint32_t), "NSSwapInt is the wrong size");
    
    while (Indexes[0].count < Char)
    {
        fwrite(&(uint32_t){ NSSwapHostIntToLittle(MISSING_GLYPH_INDEX) }, sizeof(uint32_t), 1, Indexes[0].file);
        fwrite(&(uint32_t){ NSSwapHostIntToBig(MISSING_GLYPH_INDEX) }, sizeof(uint32_t), 1, Indexes[1].file);
        
        Indexes[0].count++;
        Indexes[1].count++;
    }
    
    fwrite(&(uint32_t){ NSSwapHostIntToLittle(Index) }, sizeof(Index), 1, Indexes[0].file);
    fwrite(&(uint32_t){ NSSwapHostIntToBig(Index) }, sizeof(Index), 1, Indexes[1].file);
    
    Indexes[0].count++;
    Indexes[1].count++;
}

static void ParseMap(CGContextRef Ctx, CGRect Rect, FILE *Input, Resource *Indexes, Resource *Bitmaps, _Bool Verbose, _Bool SaveImage)
{
    uint32_t Start = 0, Stop = 0;
    switch (fscanf(Input, "U+%x-%x", &Start, &Stop))
    {
        case 1:
            Stop = Start;
            break;
            
        case -1:
            return;
            
        default:
            if (Start > Stop)
            {
                if (Verbose) fprintf(stderr, "Invalid character range (must be ascending): U+%.4x-%.4x\n", Start, Stop);
                
                fscanf(Input, "%*[^\n]");
                
                return;
            }
            break;
    }
    
    fscanf(Input, "%*[ \t]");
    
    const Options Opts = ParseOptions(Input, Verbose, SaveImage);
    Verbose = Opts.verbose;
    SaveImage = Opts.image;
    
    NSArray *Fonts = ParseFonts(Input, Verbose);
    if (!Fonts.count) Fonts = DefaultFonts;
    
    fscanf(Input, "%*[ \t]");
    fscanf(Input, "#%*[^\n]");
    
    for ( ; Start; Start++)
    {
        if (Opts.control)
        {
            WriteIndex(NON_RENDERABLE_GLYPH_INDEX, Indexes, Start, Verbose);
        }
        
        else
        {
            NSString *String = [[NSString alloc] initWithBytes: &(uint32_t){ NSSwapHostIntToLittle(Start) } length: sizeof(Start) encoding: NSUTF32LittleEndianStringEncoding];
            
            if (String.length)
            {
                CGContextSetRGBFillColor(Ctx, 0.0f, 0.0f, 0.0f, 1.0f);
                CGContextFillRect(Ctx, Rect);
                
                CFMutableAttributedStringRef AttributedString = CFAttributedStringCreateMutable(kCFAllocatorDefault, 0);
                
                CFAttributedStringReplaceString(AttributedString, (CFRange){ 0, 0 }, (CFStringRef)String);
                NSUInteger Location = 0;
                CFRange CurrentRange = { Location, 1 };
                Location += CurrentRange.length;
                
                CGColorRef Colour = CGColorCreateGenericRGB(1.0f, 0.0f, 0.0f, 1.0f);
                CFAttributedStringSetAttribute(AttributedString, CurrentRange, kCTForegroundColorAttributeName, Colour);
                CGColorRelease(Colour);
                
                Colour = CGColorCreateGenericRGB(0.0f, 0.0f, 1.0f, 1.0f);
                CFAttributedStringSetAttribute(AttributedString, CurrentRange, kCTBackgroundColorAttributeName, Colour);
                CGColorRelease(Colour);
                
                for (id Font in Fonts)
                {
                    CFAttributedStringSetAttribute(AttributedString, CurrentRange, kCTFontAttributeName, Font[0]);
                    CFAttributedStringSetAttribute(AttributedString, CurrentRange, kCTBaselineOffsetAttributeName, Font[1]);
                    
                    CGMutablePathRef Path = CGPathCreateMutable();
                    CGPathAddRect(Path, NULL, Rect);
                    
                    CTFramesetterRef Framesetter = CTFramesetterCreateWithAttributedString(AttributedString);
                    CTFrameRef Frame = CTFramesetterCreateFrame(Framesetter, CurrentRange, Path, NULL);
                    CTFrameDraw(Frame, Ctx);
                    
                    CFRelease(Path);
                    CFRelease(Framesetter);
                    CFRelease(Frame);
                    
                    for (size_t Loop = 0; Loop < sizeof(Data) / 4; Loop++)
                    {
                        if (Data[(Loop * 4) + 2] != 0)
                        {
                            size_t MaxWidth = 0, MaxHeight = 2;
                            switch (u_getIntPropertyValue(Start, UCHAR_EAST_ASIAN_WIDTH))
                            {
                                case U_EA_NEUTRAL:
                                case U_EA_AMBIGUOUS:
                                {
                                    size_t Y = Loop / Width;
                                    size_t X = Loop - (Y * Width);
                                    size_t MaxX = X, MaxY = Y;
                                    
                                    for ( ; Loop < sizeof(Data) / 4; Loop++)
                                    {
                                        if (Data[(Loop * 4) + 2] != 0)
                                        {
                                            Y = Loop / Width;
                                            X = Loop - (Y * Width);
                                            
                                            if (X > MaxX) MaxX = X;
                                            if (Y > MaxY) MaxY = Y;
                                        }
                                    }
                                    
                                    MaxWidth = ((MaxX - 1) / Cell) + 1;
                                    if (MaxWidth > 2) MaxWidth = 2;
                                    
                                    break;
                                }
                                    
                                case U_EA_HALFWIDTH:
                                case U_EA_NARROW:
                                    MaxWidth = 1;
                                    break;
                                    
                                case U_EA_FULLWIDTH:
                                case U_EA_WIDE:
                                    MaxWidth = 2;
                                    break;
                            }
                            
                            if (SaveImage)
                            {
                                for (size_t LoopY = 0; LoopY < 14; LoopY++)
                                {
                                    for (size_t LoopX = 0; LoopX < 7; LoopX++)
                                    {
                                        const size_t Pixel = (LoopY * Width) + LoopX;
                                        if (Data[Pixel * 4] != 255) Data[(Pixel * 4) + 1] = 150;
                                    }
                                    
                                    if (MaxWidth == 2)
                                    {
                                        for (size_t LoopX = 7; LoopX < 14; LoopX++)
                                        {
                                            const size_t Pixel = (LoopY * Width) + LoopX;
                                            if (Data[Pixel * 4] != 255) Data[(Pixel * 4) + 1] = 200;
                                        }
                                    }
                                }
                                
                                CGImageRef Image = CGBitmapContextCreateImage(Ctx);
                                [((NSImage*)[[NSImage alloc] initWithCGImage: Image size: NSZeroSize]).TIFFRepresentation writeToFile: [NSString stringWithFormat: @"U+%.4x.tiff", Start] atomically: NO];
                                CGImageRelease(Image);
                            }
                            
                            Resource *Bitmap = &Bitmaps[MaxWidth - 1];
                            uint32_t Index = ((MaxWidth - 1) << 28) | ((MaxHeight - 1) << 24) | (uint32_t)Bitmap->count;
                            
                            WriteIndex(Index, Indexes, Start, Verbose);
                            
                            uint8_t BitmapData[(16 * 16) / 8]; //32
                            memset(BitmapData, 0, sizeof(BitmapData));
                            
                            for (size_t LoopY = 0; LoopY < (MaxHeight * Cell); LoopY++)
                            {
                                for (size_t LoopX = 0; LoopX < (MaxWidth * Cell); LoopX++)
                                {
                                    const size_t Pixel = (LoopY * Width) + LoopX;
                                    if (Data[Pixel * 4] == 255)
                                    {
                                        const size_t BitPixel = (((LoopY / Cell) * Cell * Cell * MaxWidth) + ((LoopY % Cell) * Cell)) + ((LoopX / Cell) * Cell * Cell) + (LoopX % Cell);
                                        BitmapData[BitPixel / 8] |= 0x80 >> (BitPixel % 8);
                                    }
                                }
                            }
                            
                            fwrite(BitmapData, sizeof(uint8_t), (((MaxHeight * Cell) * (MaxWidth * Cell)) + 7) / 8, Bitmap->file);
                            
                            Bitmap->count++;
                            
                            goto Rendered;
                        }
                    }
                }
                
                if (Verbose) fprintf(stderr, "No font with glyph for character: U+%.4x\n", Start);
                
            Rendered:
                
                CFRelease(AttributedString);
            }
        }
        
        if (Start == Stop) break;
    }
}

int main(int argc, const char * argv[])
{
    @autoreleasepool {
        InitDefaults();
        
        _Bool Verbose = TRUE, SaveImage = FALSE;
        
        CGColorSpaceRef ColourSpace = CGColorSpaceCreateDeviceRGB();
        
        CGContextRef Ctx = CGBitmapContextCreate(Data, Width, Height, 8, Width * 4, ColourSpace, kCGImageAlphaPremultipliedLast);
        CGColorSpaceRelease(ColourSpace);
        
        CGContextSetAllowsFontSmoothing(Ctx, FALSE);
        CGContextSetShouldAntialias(Ctx, FALSE);
        CGContextSetAllowsAntialiasing(Ctx, FALSE);
        
        const CGRect Rect = CGRectMake(0.0f, 0.0f, Width, Height);
        
        Resource Indexes[2] = {
            { .file = fopen("glyphset.little.index", "wb"), .count = 0 },
            { .file = fopen("glyphset.big.index", "wb"), .count = 0 }
        };
        Resource Bitmaps[2] = {
            { .file = fopen("unicode.1.2.1.glyphset", "wb"), .count = 1 },
            { .file = fopen("unicode.2.2.1.glyphset", "wb"), .count = 0 }
        };
        
        WriteIndex(NON_RENDERABLE_GLYPH_INDEX, Indexes, 0, Verbose);
        
        fwrite(MissingGlyphBitmapData, sizeof(uint8_t), sizeof(MissingGlyphBitmapData), Bitmaps[0].file);
        
        do {
            ParseMap(Ctx, Rect, stdin, Indexes, Bitmaps, Verbose, SaveImage);
        } while (fgetc(stdin) != EOF);
        
        fclose(Indexes[0].file);
        fclose(Indexes[1].file);
        fclose(Bitmaps[0].file);
        fclose(Bitmaps[1].file);
    }
    
    return 0;
}
