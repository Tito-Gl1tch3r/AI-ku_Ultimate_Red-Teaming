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

#ifndef HackingGame_HubModuleGraphicsAdapter_h
#define HackingGame_HubModuleGraphicsAdapter_h

#include "HubModule.h"
#include "HubArchProcessor.h"

#define HK_HUB_MODULE_GRAPHICS_ADAPTER_CELL 7

#define HK_HUB_MODULE_GRAPHICS_ADAPTER_GLYPH_BITMAP_SIZE(width, height, palette) (((((width) * HK_HUB_MODULE_GRAPHICS_ADAPTER_CELL) * ((height) * HK_HUB_MODULE_GRAPHICS_ADAPTER_CELL) * (palette)) + 7) / 8)

#define HK_HUB_MODULE_GRAPHICS_ADAPTER_GLYPH_BUFFER 1024

#define HK_HUB_MODULE_GRAPHICS_ADAPTER_PALETTE_PAGE_COUNT 8

#define HK_HUB_MODULE_GRAPHICS_ADAPTER_LAYER_WIDTH 256
#define HK_HUB_MODULE_GRAPHICS_ADAPTER_LAYER_HEIGHT 256

#define HK_HUB_MODULE_GRAPHICS_ADAPTER_LAYER_COUNT 8

#define HK_HUB_MODULE_GRAPHICS_ADAPTER_PROGRAM_SIZE 256
#define HK_HUB_MODULE_GRAPHICS_ADAPTER_PROGRAM_COUNT 16

typedef CC_FLAG_ENUM(HKHubModuleGraphicsAdapterCursorGlyph, uint64_t) {
    //cccccccc 0pppbaaa iffggggg gggggggg gggggggg
    //c = palette index offset
    HKHubModuleGraphicsAdapterCursorGlyphPaletteOffsetIndex = 32,
    HKHubModuleGraphicsAdapterCursorGlyphPaletteOffsetMask = (0xffULL << HKHubModuleGraphicsAdapterCursorGlyphPaletteOffsetIndex),
        
    //p = palette page
    HKHubModuleGraphicsAdapterCursorGlyphPalettePageIndex = 28,
    HKHubModuleGraphicsAdapterCursorGlyphPalettePageMask = (7 << HKHubModuleGraphicsAdapterCursorGlyphPalettePageIndex),
    
    //b = bold
    HKHubModuleGraphicsAdapterCursorGlyphBoldIndex = 27,
    HKHubModuleGraphicsAdapterCursorGlyphBoldFlag = (1 << HKHubModuleGraphicsAdapterCursorGlyphBoldIndex),
    
    //i = italic
    HKHubModuleGraphicsAdapterCursorGlyphItalicIndex = 23,
    HKHubModuleGraphicsAdapterCursorGlyphItalicFlag = (1 << HKHubModuleGraphicsAdapterCursorGlyphItalicIndex),
    
    //f = animation filter (0 = rrrr rrrr, 1 = rxrx rxrx, 2 = rrxx rrxx, 3 = rrrr xxxx)
    HKHubModuleGraphicsAdapterCursorGlyphAnimationFilterIndex = 21,
    HKHubModuleGraphicsAdapterCursorGlyphAnimationFilterMask = (3 << HKHubModuleGraphicsAdapterCursorGlyphAnimationFilterIndex),
    
    //a = animation offset (current frame + anim offset = anim index)
    HKHubModuleGraphicsAdapterCursorGlyphAnimationOffsetIndex = 24,
    HKHubModuleGraphicsAdapterCursorGlyphAnimationOffsetMask = (7 << HKHubModuleGraphicsAdapterCursorGlyphAnimationOffsetIndex),
    
    //g = glyph index
    HKHubModuleGraphicsAdapterCursorGlyphIndexMask = 0x1fffff,
    
    CC_RESERVED_BITS(HKHubModuleGraphicsAdapterCursorGlyph, 0, 40)
};

typedef CC_FLAG_ENUM(HKHubModuleGraphicsAdapterCharacter, uint32_t) {
    //ttttssss 000ggggg gggggggg gggggggg
    
    //t = y-relative position of glyph
    HKHubModuleGraphicsAdapterCharacterPositionTIndex = 28,
    HKHubModuleGraphicsAdapterCharacterPositionTMask = (0xf << HKHubModuleGraphicsAdapterCharacterPositionTIndex),
    
    //s = x-relative position of glyph
    HKHubModuleGraphicsAdapterCharacterPositionSIndex = 24,
    HKHubModuleGraphicsAdapterCharacterPositionSMask = (0xf << HKHubModuleGraphicsAdapterCharacterPositionSIndex),
    
    //g = glyph index
    HKHubModuleGraphicsAdapterCharacterhGlyphIndexMask = 0x1fffff,
    
    CC_RESERVED_BITS(HKHubModuleGraphicsAdapterCharacter, 0, 32)
};

/*!
 * @brief Create a graphics adapter module.
 * @param Allocator The allocator to be used.
 * @return The graphics adapter module. Must be destroyed to free memory.
 */
HKHubModule HKHubModuleGraphicsAdapterCreate(CCAllocatorType Allocator);

/*!
 * @brief Increment the frame tick.
 * @param Adapter The graphics adapter to tick.
 */
void HKHubModuleGraphicsAdapterNextFrame(HKHubModule Adapter);

/*!
 * @brief Get a glyph.
 * @description First looks up if there's a dynamic glyph for the character otherwise it looks up whether there is a static glyph.
 * @param Adapter The graphics adapter to get the glyph from.
 * @param Character The character to lookup the glyph data for.
 * @param AnimationOffset The amount to offset the animation by.
 * @param AnimationFilter How the animation should be filtered.
 * @param Width A pointer to where the width of the glyph should be stored. May be NULL.
 * @param Height A pointer to where the height of the glyph should be stored. May be NULL.
 * @param PaletteSize A pointer to where the palette bit size of the glyph should be stored. May be NULL.
 * @return The bitmap data for the glyph or NULL if there was no glyph for the given character and animation for the adjusted frame.
 */
const uint8_t *HKHubModuleGraphicsAdapterGetGlyphBitmap(HKHubModule Adapter, CCChar Character, uint8_t AnimationOffset, uint8_t AnimationFilter, uint8_t *Width, uint8_t *Height, uint8_t *PaletteSize);

/*!
 * @brief Modify a dynamic glyph.
 * @description Dynamic glyphs are stored in the memory of the graphics adapter.
 * @param Adapter The graphics adapter to set the glyph for.
 * @param Character The character to modify.
 * @param Width The number of cells wide of the new glyph. In range 0 to 15 (where there's an implicit +1 width).
 * @param Height The number of cells high of the new glyph. In range 0 to 15 (where there's an implicit +1 height).
 * @param PaletteSize The bit size of the palette used by the glyph. In range 0 to 7 (where there's an implicit +1 palette size).
 * @param Bitmap The bitmap data of the glyph.
 * @param Frames The number of frames in the bitmap data.
 * @return Whether the glyph was successfully set or not.
 */
_Bool HKHubModuleGraphicsAdapterSetGlyphBitmap(HKHubModule Adapter, CCChar Character, uint8_t Width, uint8_t Height, uint8_t PaletteSize, const uint8_t *Bitmap, size_t Frames);

/*!
 * @brief Copy the contents of the viewport to the target framebuffer.
 * @param Adapter The graphics adapter to copy from.
 * @param Port The viewport to copy.
 * @param Framebuffer The framebuffer to copy the viewport to.
 * @param Size The size of the framebuffer.
 */
void HKHubModuleGraphicsAdapterBlit(HKHubModule Adapter, HKHubArchPortID Port, uint8_t *Framebuffer, size_t Size);

/*!
 * @brief Get the characters for the cells in the specified region.
 * @param Adapter The graphics adapter to read from.
 * @param Layer The layer to read.
 * @param X The x position of the region.
 * @param Y The y position of the region.
 * @param Width The width of the region.
 * @param Height The height of the region.
 * @param Characters The characters in the region. Must be of size @b Width @b * @b Height @b * @b HKHubModuleGraphicsAdapterCharacter.
 */
void HKHubModuleGraphicsAdapterRead(HKHubModule Adapter, uint8_t Layer, uint8_t X, uint8_t Y, uint8_t Width, uint8_t Height, HKHubModuleGraphicsAdapterCharacter *Characters);

/*!
 * @brief Get the viewport.
 * @param Adapter The graphics adapter to inspect.
 * @param Port The port to get the viewport for.
 * @param X A pointer to where to store the x position of the viewport. May be NULL.
 * @param Y A pointer to where to store the y position of the viewport. May be NULL.
 * @param Width A pointer to where to store the width of the viewport. May be NULL.
 * @param Height A pointer to where to store the height of the viewport. May be NULL.
 */
void HKHubModuleGraphicsAdapterGetViewport(HKHubModule Adapter, HKHubArchPortID Port, uint8_t *X, uint8_t *Y, uint8_t *Width, uint8_t *Height);

/*!
 * @brief Set the viewport.
 * @param Adapter The graphics adapter to set.
 * @param Port The port to set the viewport of.
 * @param X The x position of the viewport.
 * @param Y The y position of the viewport.
 * @param Width The width of the viewport.
 * @param Height The height of the viewport.
 */
void HKHubModuleGraphicsAdapterSetViewport(HKHubModule Adapter, HKHubArchPortID Port, uint8_t X, uint8_t Y, uint8_t Width, uint8_t Height);

/*!
 * @brief Set the cursor position.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param X The x position of the cursor.
 * @param Y The y position of the cursor.
 */
void HKHubModuleGraphicsAdapterSetCursor(HKHubModule Adapter, uint8_t Layer, uint8_t X, uint8_t Y);

/*!
 * @brief Set the cursor visibility.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param Visibility The glyph the cursor should appear as. Set to @b 0 to make the cursor invisible.
 */
void HKHubModuleGraphicsAdapterSetCursorVisibility(HKHubModule Adapter, uint8_t Layer, HKHubModuleGraphicsAdapterCursorGlyph Visibility);

/*!
 * @brief Get the cursor origin.
 * @description The starting origin of the cursor. @b 0,0 = top left, @b 1,0 = top right, @b 0,1 = bottom left, @b 1,1 = bottom right.
 * @param Adapter The graphics adapter to inspect.
 * @param Layer The layer context to be inspect.
 * @param OriginX A pointer to where the x origin should be stored. May be NULL.
 * @param OriginY A pointer to where the y origin should be stored. May be NULL.
 */
void HKHubModuleGraphicsAdapterGetCursorOrigin(HKHubModule Adapter, uint8_t Layer, uint8_t *OriginX, uint8_t *OriginY);

/*!
 * @brief Set the cursor origin.
 * @description The starting origin of the cursor. @b 0,0 = top left, @b 1,0 = top right, @b 0,1 = bottom left, @b 1,1 = bottom right.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param OriginX The x origin. Set it to @b 0 to set the starting x position to be from the left, or @b 1 to set the starting x position to be from the
 *          right.
 * @param OriginY The y origin. Set it to @b 0 to set the starting y position to be from the top, or @b 1 to set the starting y position to be from the
 *          bottom.
 */
void HKHubModuleGraphicsAdapterSetCursorOrigin(HKHubModule Adapter, uint8_t Layer, uint8_t OriginX, uint8_t OriginY);

/*!
 * @brief Enabled/disable cursor advancement.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param Enable Whether to enable cursor advancement or not. When drawing a glyph the cursor will advance to a new position if enabled, otherwise
 *               the cursor position is left alone.
 */
void HKHubModuleGraphicsAdapterSetCursorAdvance(HKHubModule Adapter, uint8_t Layer, _Bool Enable);

/*!
 * @brief Set the cursor advance source.
 * @description The multiples of the last drawn glyph to advance the cursor position by.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param Width The amount to multiply the last glyph's width by.
 * @param Height The amount to multiply the last glyph's height by.
 */
void HKHubModuleGraphicsAdapterSetCursorAdvanceSource(HKHubModule Adapter, uint8_t Layer, int8_t Width, int8_t Height);

/*!
 * @brief Set the cursor advance offset.
 * @description The amount to offset the cursor position when it has drawn a glyph.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param X The x offset.
 * @param Y The y offset.
 */
void HKHubModuleGraphicsAdapterSetCursorAdvanceOffset(HKHubModule Adapter, uint8_t Layer, int8_t X, int8_t Y);

/*!
 * @brief Enabled/disable cursor wrapping.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param Enable Whether to enable cursor wrapping or not. When drawing a glyph causes the cursor to advance outside of the current cursor bounds
 *               the cursor will wrap to a new position if wrapping is enabled, otherwise the cursor position is left alone.
 */
void HKHubModuleGraphicsAdapterSetCursorWrap(HKHubModule Adapter, uint8_t Layer, _Bool Enable);

/*!
 * @brief Set the cursor wrap source.
 * @description The multiples of the last drawn glyph (that cause the cursor to wrap) to wrap the cursor position by.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param Width The amount to multiply the last glyph's width by.
 * @param Height The amount to multiply the last glyph's height by.
 */
void HKHubModuleGraphicsAdapterSetCursorWrapSource(HKHubModule Adapter, uint8_t Layer, int8_t Width, int8_t Height);

/*!
 * @brief Set the cursor wrap offset.
 * @description The amount to offset the cursor position when it's being wrapped.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param X The x offset.
 * @param Y The y offset.
 */
void HKHubModuleGraphicsAdapterSetCursorWrapOffset(HKHubModule Adapter, uint8_t Layer, int8_t X, int8_t Y);

/*!
 * @brief Set the cursor bounds.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param X The x position of the cursour bounds.
 * @param Y The y position of the cursour bounds.
 * @param Width The width of the cursour bounds.
 * @param Height The height of the cursour bounds.
 */
void HKHubModuleGraphicsAdapterSetCursorBounds(HKHubModule Adapter, uint8_t Layer, uint8_t X, uint8_t Y, uint8_t Width, uint8_t Height);

/*!
 * @brief Set the palette index offset.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param Offset The amount to offset the palette indexes.
 */
void HKHubModuleGraphicsAdapterSetCursorControl(HKHubModule Adapter, uint8_t Layer, uint8_t Index, CCChar Character, uint8_t ProgramID);

/*!
 * @brief Set the palette page.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param Page The page of the palette to be used. Pages are in the range from 0 to HK_HUB_MODULE_GRAPHICS_ADAPTER_PALETTE_PAGE_COUNT - 1.
 */
void HKHubModuleGraphicsAdapterSetPalettePage(HKHubModule Adapter, uint8_t Layer, uint8_t Page);

/*!
 * @brief Set the palette index offset.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param Offset The amount to offset the palette indexes.
 */
void HKHubModuleGraphicsAdapterSetPaletteOffset(HKHubModule Adapter, uint8_t Layer, uint8_t Offset);

/*!
 * @brief Set the palette colour.
 * @param Adapter The graphics adapter to set.
 * @param Page The palette page to be set.
 * @param Index The index of the palette to set the colour of.
 * @param Colour The new colour.
 */
void HKHubModuleGraphicsAdapterSetPaletteColour(HKHubModule Adapter, uint8_t Page, uint8_t Index, uint8_t Colour);

/*!
 * @brief Enable/disable bold.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param Enable Whether bold should be on or off.
 */
void HKHubModuleGraphicsAdapterSetBold(HKHubModule Adapter, uint8_t Layer, _Bool Enable);

/*!
 * @brief Enable/disable italics.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param Enable Whether italics should be on or off.
 */
void HKHubModuleGraphicsAdapterSetItalic(HKHubModule Adapter, uint8_t Layer, _Bool Enable);

/*!
 * @brief Set the slope of italic.
 * @note This applies to the entire layer including previously drawn cells.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param Slope The degree of slope the italic glyphs should have.
 */
void HKHubModuleGraphicsAdapterSetItalicSlope(HKHubModule Adapter, uint8_t Layer, uint8_t Slope);

/*!
 * @brief Set the animation offset.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param Offset The amount to offset animations by.
 */
void HKHubModuleGraphicsAdapterSetAnimationOffset(HKHubModule Adapter, uint8_t Layer, uint8_t Offset);

/*!
 * @brief Set the animation filter.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param Filter The animation filter to be applied. @b 0 = rrrr rrrr, @b 1 = rxrx rxrx, @b 2 = rrxx rrxx, @b 3 = rrrr xxxx (where @b r is
 *               a rendered frame, and @b x is not rendered frame).
 */
void HKHubModuleGraphicsAdapterSetAnimationFilter(HKHubModule Adapter, uint8_t Layer, uint8_t Filter);

/*!
 * @brief Set the attribute modifier.
 * @param Adapter The graphics adapter to set.
 * @param Layer The layer context to be set.
 * @param Modifier The new attribute modifier to be used for any references. @b 0 = inherits all attributes (palette index offset, palette page,
 *                 bold, italics, animation offset, animation filter) from the reference, @b 1 = inherits (bold, italics, animation offset,
 *                 animation filter) and resets (palette index offset, palette page), @b 2 = inherits (palette index offset, palette page, bold,
 *                 italics) and resets (animation offset, animation filter), @b 3 = resets all attributes (palette index offset, palette page,
 *                 bold, italics, animation offset, animation filter). The current attribute values are added onto the referenced attribute
 *                 (which has been inherited or reset).
 */
void HKHubModuleGraphicsAdapterSetAttributeModifier(HKHubModule Adapter, uint8_t Layer, uint8_t Modifier);


/*!
 * @brief Clear the region in the bounds.
 * @param Adapter The graphics adapter to clear.
 * @param Layer The layer to be cleared.
 * @param X The X position of the bounds.
 * @param Y The Y position of the bounds.
 * @param Width The width of the bounds.
 * @param Height The height of the bounds.
 */
void HKHubModuleGraphicsAdapterClear(HKHubModule Adapter, uint8_t Layer, uint8_t X, uint8_t Y, uint8_t Width, uint8_t Height);

/*!
 * @brief Draw a character.
 * @param Adapter The graphics adapter to draw the character to.
 * @param Layer The layer to the draw the character on.
 * @param Character The character to be drawn.
 */
void HKHubModuleGraphicsAdapterDrawCharacter(HKHubModule Adapter, uint8_t Layer, CCChar Character);

/*!
 * @brief Draw a reference.
 * @param Adapter The graphics adapter to draw the reference to.
 * @param Layer The layer to the draw the reference on.
 * @param X The X position of the reference on the @b RefLayer.
 * @param Y The Y position of the reference on the @b RefLayer.
 * @param Width The width of the reference on the @b RefLayer.
 * @param Height The height of the reference on the @b RefLayer.
 * @param RefLayer The layer to be referenced.
 */
void HKHubModuleGraphicsAdapterDrawRef(HKHubModule Adapter, uint8_t Layer, uint8_t X, uint8_t Y, uint8_t Width, uint8_t Height, uint8_t RefLayer);

/*!
 * @brief Modify a program.
 * @param Adapter The graphics adapter to set the program of.
 * @param ProgramID The ID to reference the program. In the range of 0 to @b (HK_HUB_MODULE_GRAPHICS_ADAPTER_PROGRAM_COUNT @b - @b 1).
 * @param Payload The program binary.
 * @param Size The size of the payload. The payload size must not exceed @b HK_HUB_MODULE_GRAPHICS_ADAPTER_PROGRAM_SIZE.
 */
void HKHubModuleGraphicsAdapterProgramSet(HKHubModule Adapter, uint8_t ProgramID, const uint8_t *Payload, size_t Size);

/*!
 * @brief Run a program.
 * @param Adapter The graphics adapter to run the program of.
 * @param Layer The layer to be used as the target context.
 * @param ProgramID The ID of the program to run. In the range of 0 to @b (HK_HUB_MODULE_GRAPHICS_ADAPTER_PROGRAM_COUNT @b - @b 1).
 * @param X The x-offset of the initial character to put on the stack.
 * @param Y The y-offset of the initial character to put on the stack.
 * @param Width The width of the initial character to put on the stack.
 * @param Height The heightt of the initial character to put on the stack.
 * @param Character The initial character to put on the stack.
 */
void HKHubModuleGraphicsAdapterProgramRun(HKHubModule Adapter, uint8_t Layer, uint8_t ProgramID, uint8_t X, uint8_t Y, uint8_t Width, uint8_t Height, CCChar Character);

/*!
 * @brief Initialise the static glyphs.
 */
void HKHubModuleGraphicsAdapterStaticGlyphInit(void);

/*!
 * @brief Modify static glyphs.
 * @description Static glyphs do not use the memory of the graphics adapter.
 * @param Character The first character in the set to modify.
 * @param Width The number of cells wide of the new glyphs. In range 0 to 15 (where there's an implicit +1 width).
 * @param Height The number of cells high of the new glyphs. In range 0 to 15 (where there's an implicit +1 height).
 * @param PaletteSize The bit size of the palette used by the glyph. In range 0 to 7 (where there's an implicit +1 palette size).
 * @param Bitmap The bitmap data of the glyphs. Starts with the data for @b Character and continues up to @b Count characters.
 * @param Count The number of glyphs to be set from @b Character to @b Character @b + @b (Count @b - @b 1).
 */
void HKHubModuleGraphicsAdapterStaticGlyphSet(CCChar Character, uint8_t Width, uint8_t Height, uint8_t PaletteSize, const uint8_t *Bitmap, size_t Count);

/*!
 * @brief Get a static glyph.
 * @param Character The character to lookup the static glyph data for.
 * @param Width A pointer to where the width of the glyph should be stored. May be NULL.
 * @param Height A pointer to where the height of the glyph should be stored. May be NULL.
 * @param PaletteSize A pointer to where the palette bit size of the glyph should be stored. May be NULL.
 * @return The bitmap data for the glyph or NULL if there was no static glyph for the given character.
 */
const uint8_t *HKHubModuleGraphicsAdapterStaticGlyphGet(CCChar Character, uint8_t *Width, uint8_t *Height, uint8_t *PaletteSize);

#endif
