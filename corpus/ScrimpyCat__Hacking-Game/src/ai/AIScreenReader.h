/*
 *  Copyright (c) 2022, Stefan Johnson
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

#ifndef HackingGame_AIScreenReader_h
#define HackingGame_AIScreenReader_h

#include "Base.h"
#include "HubModuleGraphicsAdapter.h"

#define HK_AI_SCREEN_READER_SKIP_CHAR (1 << 22)

#define HK_AI_SCREEN_READER_INCOMPLETE_CHAR_FLAG (1 << 23)

/*!
 * @brief Normalize the cell characters.
 * @description Merges the cells into a line.
 * @param Characters The characters in the region. Must be of size @b Width @b * @b Height @b * @b HKHubModuleGraphicsAdapterCharacter.
 * @param Width The width of the region.
 * @param Height The height of the region.
 * @param Replacement The replacement character to be used for unmergeable cells.
 * @param LineHeight The height of a line (the number of rows of cells to merge).
 */
void HKAIScreenReaderNormalize(HKHubModuleGraphicsAdapterCharacter *Characters, size_t Width, size_t Height, CCChar Replacement, size_t LineHeight);

#endif
