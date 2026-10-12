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
#import "ProgramTests.h"

#define HKHubArchAssemblyPrintError(err) if (Errors) { HKHubArchAssemblyPrintError(err); CCCollectionDestroy(err); err = NULL; }

@interface ProgramTests ()

@property HKHubArchProcessor processor;
@property HKHubArchScheduler scheduler;

@end


size_t RetCallCount = 0;

_Bool RetTrue(void)
{
    return TRUE;
}

_Bool RetFalse(void)
{
    return FALSE;
}

@implementation ProgramTests
@synthesize processor, scheduler;

-(const char*) program
{
    CCAssertLog(0, "Should be redefined by the subclass");
    return "";
}

-(const char*) defines
{
    return "";
}

+(void) setUp
{
    if (HKHubArchAssemblyIncludeSearchPaths) CCCollectionDestroy(HKHubArchAssemblyIncludeSearchPaths);
    
    HKHubArchAssemblyIncludeSearchPaths = CCCollectionCreate(CC_STD_ALLOCATOR, CCCollectionHintOrdered, sizeof(FSPath), FSPathComponentDestructorForCollection);
    
    CCOrderedCollectionAppendElement(HKHubArchAssemblyIncludeSearchPaths, &(FSPath){ FSPathCreate("assets/logic/programs/") });
    CCOrderedCollectionAppendElement(HKHubArchAssemblyIncludeSearchPaths, &(FSPath){ FSPathCreate("assets/logic/procedures/") });
}

-(void) setUp
{
    [super setUp];
    
    FSPath Path = FSPathCreate(self.program);
    
    FSHandle Handle;
    if (FSHandleOpen(Path, FSHandleTypeRead, &Handle) == FSOperationSuccess)
    {
        size_t Size = FSManagerGetSize(Path), DefineSize = strlen(self.defines);
        char *Source;
        CC_SAFE_Malloc(Source, sizeof(char) * (Size + DefineSize + 1));
        
        strcpy(Source, self.defines);
        
        FSHandleRead(Handle, &Size, Source + DefineSize, FSBehaviourDefault);
        Source[Size + DefineSize] = 0;
        
        FSHandleClose(Handle);
        
        CCOrderedCollection AST = HKHubArchAssemblyParse(Source);
        
        CCOrderedCollection Errors = NULL;
        HKHubArchBinary Binary = HKHubArchAssemblyCreateBinary(CC_STD_ALLOCATOR, AST, &Errors); HKHubArchAssemblyPrintError(Errors);
        CCCollectionDestroy(AST);
        
        if (Binary)
        {
            processor = HKHubArchProcessorCreate(CC_STD_ALLOCATOR, Binary);
            HKHubArchBinaryDestroy(Binary);
        }
        
        CC_SAFE_Free(Source);
    }
    
    FSPathDestroy(Path);
    
    scheduler = HKHubArchSchedulerCreate(CC_STD_ALLOCATOR);
    HKHubArchSchedulerAddProcessor(scheduler, processor);
    
    RetCallCount = 0;
}

-(void)tearDown
{
    if (processor) HKHubArchProcessorDestroy(processor);
    if (scheduler) HKHubArchSchedulerDestroy(scheduler);
    
    [super tearDown];
}

@end
