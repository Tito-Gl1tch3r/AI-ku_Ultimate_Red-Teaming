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

#include "HubModuleDisplay.h"
#include "HubArchProcessor.h"

typedef struct {
    uint8_t buffer[256];
} HKHubModuleDisplayState;


static CCData HKHubModuleDisplayBufferConversion_None(CCAllocatorType Allocator, const uint8_t Buffer[256]);
static CCData HKHubModuleDisplayBufferConversion_UniformColourRGB888(CCAllocatorType Allocator, const uint8_t Buffer[256]);
static CCData HKHubModuleDisplayBufferConversion_DirectColourRGB888(CCAllocatorType Allocator, const uint8_t Buffer[256]);
static CCData HKHubModuleDisplayBufferConversion_GradientColourRGB888(CCAllocatorType Allocator, const uint8_t Buffer[256]);
static CCData HKHubModuleDisplayBufferConversion_YUVColourRGB888(CCAllocatorType Allocator, const uint8_t Buffer[256]);


const HKHubModuleDisplayBufferConverter HKHubModuleDisplayBuffer = HKHubModuleDisplayBufferConversion_None;
const HKHubModuleDisplayBufferConverter HKHubModuleDisplayBuffer_UniformColourRGB888 = HKHubModuleDisplayBufferConversion_UniformColourRGB888;
const HKHubModuleDisplayBufferConverter HKHubModuleDisplayBuffer_DirectColourRGB888 = HKHubModuleDisplayBufferConversion_DirectColourRGB888;
const HKHubModuleDisplayBufferConverter HKHubModuleDisplayBuffer_GradientColourRGB888 = HKHubModuleDisplayBufferConversion_GradientColourRGB888;
const HKHubModuleDisplayBufferConverter HKHubModuleDisplayBuffer_YUVColourRGB888 = HKHubModuleDisplayBufferConversion_YUVColourRGB888;


static HKHubArchPortResponse HKHubModuleDisplaySetBuffer(HKHubArchPortConnection Connection, HKHubModule Device, HKHubArchPortID Port, HKHubArchPortMessage *Message, HKHubArchPortDevice ConnectedDevice, int64_t Timestamp, size_t *Wait)
{
    const HKHubArchPort *OppositePort = HKHubArchPortConnectionGetOppositePort(Connection, Device, Port);
    
    if (HKHubArchPortIsReady(OppositePort))
    {
        if (Message->size > 1)
        {
            HKHubModuleDisplayState *State = Device->internal;
            
            uint8_t Offset = Message->memory[Message->offset];
            for (uint8_t Size = Message->size; Size-- > 1; )
            {
                State->buffer[Offset + (Size - 1)] = Message->memory[Message->offset + Size];
            }
        }
    }
    
    return HKHubArchPortResponseSuccess;
}

HKHubModule HKHubModuleDisplayCreate(CCAllocatorType Allocator)
{
    HKHubModuleDisplayState *State = CCMalloc(Allocator, sizeof(HKHubModuleDisplayState), NULL, CC_DEFAULT_ERROR_CALLBACK);
    if (State)
    {
        memset(State->buffer, 0, sizeof(State->buffer));
        
        return HKHubModuleCreate(Allocator, NULL, (HKHubArchPortTransmit)HKHubModuleDisplaySetBuffer, State, CCFree, CCDataBufferCreate(Allocator, CCDataHintReadWrite, sizeof(State->buffer), State->buffer, NULL, NULL));
    }
    
    else CC_LOG_ERROR("Failed to create display module due to allocation failure: allocation of size (%zu)", sizeof(HKHubModuleDisplayState));
    
    return NULL;
}

CCData HKHubModuleDisplayConvertBuffer(CCAllocatorType Allocator, HKHubModule Module, HKHubModuleDisplayBufferConverter Converter)
{
    CCAssertLog(Module, "Module must not be null");
    CCAssertLog(Converter, "Converter must not be null");
    
    return Converter(Allocator, ((HKHubModuleDisplayState*)Module->internal)->buffer);
}

#pragma mark - Buffer Converters

static CCData HKHubModuleDisplayBufferConversion_None(CCAllocatorType Allocator, const uint8_t Buffer[256])
{
    return CCDataBufferCreate(Allocator, CCDataBufferHintCopy, 256, Buffer, NULL, NULL);
}

static CCData HKHubModuleDisplayBufferConversion_UniformColourRGB888(CCAllocatorType Allocator, const uint8_t Buffer[256])
{
    /*
     ffrrggbb
     
     r = red
     g = green
     b = blue
     f = scale factor
     
     Channel values are in multiples of 68. e.g. r = 1 (red = 68)
     Scale factor is a multiple of 17. e.g. r = 1 (red = 68), sf = 2 (scale factor = 34) = red = 68+34 = 102
     
     The scale factor is applied to each channel.
     
     Pros:
     Good colour distribution (equal reds, greens, blues), mixed channels, good selection of greys.
     
     Cons:
     No absolute red, green, or blue.
     */
    
    size_t DataSize = 256 * sizeof(uint8_t) * 3;
    uint8_t *Data = CCMalloc(Allocator, DataSize, NULL, CC_DEFAULT_ERROR_CALLBACK);
    if (!Data)
    {
        CC_LOG_ERROR("Failed to create data buffer. Allocation failure of size (%zu)", DataSize);
        return NULL;
    }
    
    for (size_t Loop = 0; Loop < 256; Loop++)
    {
        const uint8_t b = Buffer[Loop] & (3 << 0);
        const uint8_t g = (Buffer[Loop] & (3 << 2)) >> 2;
        const uint8_t r = (Buffer[Loop] & (3 << 4)) >> 4;
        const uint8_t f = (Buffer[Loop] & (3 << 6)) >> 6;
        
        Data[Loop * 3] = ((r * 4) + f) * 17; //red
        Data[(Loop * 3) + 1] = ((g * 4) + f) * 17; //green
        Data[(Loop * 3) + 2] = ((b * 4) + f) * 17; //blue
    }
    
    return CCDataBufferCreate(Allocator, CCDataBufferHintFree, DataSize, Data, NULL, NULL);
}

static CCData HKHubModuleDisplayBufferConversion_DirectColourRGB888(CCAllocatorType Allocator, const uint8_t Buffer[256])
{
    /*
     RGB332
     rrrgggbb
     
     r = red
     g = green
     b = blue
     
     Channel values are evenly spread across range from 0 mapping to absolute zero, and max mapping to absolute
     one.
     
     Pros:
     Distributes colour in-favour of human sight, where blues are weakest so less depth is given to it.
     Decent colour distribution across channels and mixed channels.
     
     Cons:
     Poor selection of greys and blues.
     */
    
    size_t DataSize = 256 * sizeof(uint8_t) * 3;
    uint8_t *Data = CCMalloc(Allocator, DataSize, NULL, CC_DEFAULT_ERROR_CALLBACK);
    if (!Data)
    {
        CC_LOG_ERROR("Failed to create data buffer. Allocation failure of size (%zu)", DataSize);
        return NULL;
    }
    
    for (size_t Loop = 0; Loop < 256; Loop++)
    {
        const uint8_t b = Buffer[Loop] & (3 << 0);
        const uint8_t g = (Buffer[Loop] & (7 << 2)) >> 2;
        const uint8_t r = (Buffer[Loop] & (7 << 5)) >> 5;
        
        Data[Loop * 3] = ((r >> 2) * 0x92) | (((r & 2) >> 1) * 0x49)  | ((r & 1) * 0x24); //red
        Data[(Loop * 3) + 1] = ((g >> 2) * 0x92) | (((g & 2) >> 1) * 0x49)  | ((g & 1) * 0x24); //green
        Data[(Loop * 3) + 2] = b * 85; //blue
    }
    
    return CCDataBufferCreate(Allocator, CCDataBufferHintFree, DataSize, Data, NULL, NULL);
}

static CCData HKHubModuleDisplayBufferConversion_GradientColourRGB888(CCAllocatorType Allocator, const uint8_t Buffer[256])
{
    /*
     rgbvvvvv
     
     r = red
     g = green
     b = blue
     v = value
     
     Channel are flagged in-use/not in-use (1 = on, 0 = off).
     Value is intensity factor use by the desired channels.
     
     Pros:
     Absolutes (black, white, red, green, blue, cyan, magenta, yellow).
     High level gradients for greys, primaries (red, green, blue), secondaries (cyan, magenta, yellow).
     
     Cons:
     Inability to achieve mixed ratios for colours.
     Poor use of range, lower bound (000xxxxx) when no channels in use is wasted.
     */
    
    size_t DataSize = 256 * sizeof(uint8_t) * 3;
    uint8_t *Data = CCMalloc(Allocator, DataSize, NULL, CC_DEFAULT_ERROR_CALLBACK);
    if (!Data)
    {
        CC_LOG_ERROR("Failed to create data buffer. Allocation failure of size (%zu)", DataSize);
        return NULL;
    }
    
    for (size_t Loop = 0; Loop < 256; Loop++)
    {
        const uint8_t b = (Buffer[Loop] & (1 << 5)) >> 5;
        const uint8_t g = (Buffer[Loop] & (1 << 6)) >> 6;
        const uint8_t r = (Buffer[Loop] & (1 << 7)) >> 7;
        const uint8_t f = (Buffer[Loop] & 31) + 1;
        
        Data[Loop * 3] = (uint16_t)(r * f) * 8; //red
        Data[(Loop * 3) + 1] = (uint16_t)(g * f) * 8; //green
        Data[(Loop * 3) + 2] = (uint16_t)(b * f) * 8; //blue
    }
    
    return CCDataBufferCreate(Allocator, CCDataBufferHintFree, DataSize, Data, NULL, NULL);
}

static CCData HKHubModuleDisplayBufferConversion_YUVColourRGB888(CCAllocatorType Allocator, const uint8_t Buffer[256])
{
    /*
     vvvuuuyy
     
     y = luma
     u = chromaU
     v = chromaV
     
     Greater precision is given to chroma channel values than luminance.
     */
    
    size_t DataSize = 256 * sizeof(uint8_t) * 3;
    uint8_t *Data = CCMalloc(Allocator, DataSize, NULL, CC_DEFAULT_ERROR_CALLBACK);
    if (!Data)
    {
        CC_LOG_ERROR("Failed to create data buffer. Allocation failure of size (%zu)", DataSize);
        return NULL;
    }
    
    for (size_t Loop = 0; Loop < 256; Loop++)
    {
        const uint8_t y = Buffer[Loop] & (3 << 0);
        const uint8_t u = (Buffer[Loop] & (7 << 2)) >> 2;
        const uint8_t v = (Buffer[Loop] & (7 << 5)) >> 5;
        
        const float uf = (float)u - 4;
        const float vf = (float)v - 4;
        
        CCVector3D YUV = CCVector3DMake((float)y / 3.0f, uf / (uf < 0.0f ? 4.0f : 3.0f), vf / (vf < 0.0f ? 4.0f : 3.0f));
        
        CCMatrix4 Mat = CCMatrix4Make(1.0f,      0.0f,  1.28033f, 0.0f,
                                      1.0f, -0.21482f, -0.38059f, 0.0f,
                                      1.0f,  2.12798f,     0.0f,  0.0f,
                                      0.0f,      0.0f,     0.0f,  1.0f);
        
        CCVector3D RGB = CCVector3MulScalar(CCVector3Clamp(CCMatrix4MulPositionVector3D(Mat, YUV), CCVector3DZero, CCVector3DFill(1.0f)), 255.0f);
        
        
        Data[Loop * 3] = RGB.x; //red
        Data[(Loop * 3) + 1] = RGB.y; //green
        Data[(Loop * 3) + 2] = RGB.z; //blue
    }
    
    return CCDataBufferCreate(Allocator, CCDataBufferHintFree, DataSize, Data, NULL, NULL);
}
