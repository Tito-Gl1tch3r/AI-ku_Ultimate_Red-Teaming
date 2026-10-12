/*
 *  Copyright (c) 2016, Stefan Johnson
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

#include "Base.h"
#include "HubArchExpressions.h"
#include "HubArchAssembly.h"
#include "RapServer.h"
#include "HubSystem.h"
#include "HubProcessorComponent.h"
#include "HubPortConnectionComponent.h"
#include "HubDebuggerComponent.h"
#include "HubSchematicComponent.h"
#include "HubModuleComponent.h"
#include "HubModuleKeyboardComponent.h"
#include "HubModuleDisplayComponent.h"
#include "HubModuleWirelessTransceiverComponent.h"
#include "ItemManualComponent.h"
#include "HubModuleGraphicsAdapter.h"

#if CC_PLATFORM_OS_X || CC_PLATFORM_IOS
#include <CoreFoundation/CoreFoundation.h>
#endif

FSPath HKAssetPath = NULL;

static void PreSetup(void)
{
    char Path[] = __FILE__;
    if ((sizeof(__FILE__) > sizeof("Hacking-Game/src/main.c")) && (!strcmp(Path + (sizeof(__FILE__) - sizeof("Hacking-Game/src/main.c")), "Hacking-Game/src/main.c")))
    {
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Warray-bounds"
        Path[sizeof(__FILE__) - sizeof("Hacking-Game/src/main.c")] = 0;
#pragma clang diagnostic pop

        CCFileFilterInputAddPath(Path);
    }
    
    CCExpressionEvaluatorRegister(CC_STRING("disassemble"), HKHubArchExpressionDisassemble);
    
    HKRapServerStart();
}

static void Setup(void)
{
    HKHubModuleGraphicsAdapterStaticGlyphInit();
    HKHubSystemRegister();
    HKHubProcessorComponentRegister();
    HKHubPortConnectionComponentRegister();
    HKHubDebuggerComponentRegister();
    HKHubSchematicComponentRegister();
    HKHubModuleComponentRegister();
    HKHubModuleKeyboardComponentRegister();
    HKHubModuleDisplayComponentRegister();
    HKHubModuleWirelessTransceiverComponentRegister();
    
    HKItemManualComponentRegister();
    
    HKHubArchAssemblyIncludeSearchPaths = CCCollectionCreate(CC_STD_ALLOCATOR, CCCollectionHintOrdered, sizeof(FSPath), FSPathComponentDestructorForCollection);
    
    FSPath IncludeSearchPath = FSPathCopy(HKAssetPath);
    
    FSPathAppendComponent(IncludeSearchPath, FSPathComponentCreate(FSPathComponentTypeDirectory, "logic"));
    FSPathAppendComponent(IncludeSearchPath, FSPathComponentCreate(FSPathComponentTypeDirectory, "programs"));
    
    CCOrderedCollectionAppendElement(HKHubArchAssemblyIncludeSearchPaths, &IncludeSearchPath);
    
    IncludeSearchPath = FSPathCopy(IncludeSearchPath);
    FSPathSetComponentAtIndex(IncludeSearchPath, FSPathComponentCreate(FSPathComponentTypeDirectory, "procedures"), FSPathGetComponentCount(IncludeSearchPath) - 1);
    
    CCOrderedCollectionAppendElement(HKHubArchAssemblyIncludeSearchPaths, &IncludeSearchPath);
}

int main(int argc, const char *argv[])
{
    B2EngineSetupBegin = PreSetup;
    B2EngineSetupComplete = Setup;
    
    B2EngineConfiguration.launch = B2LaunchOptionGame;
    
#if CC_PLATFORM_OS_X || CC_PLATFORM_IOS
    CFBundleRef Bundle = CFBundleGetBundleWithIdentifier(CFSTR("io.scrimpycat.HackingGame"));
    if (Bundle)
    {
        CFURLRef ResourceURL = CFBundleCopyResourcesDirectoryURL(Bundle);
        char ResourcePath[PATH_MAX];
        
        if ((!ResourceURL) || (!CFURLGetFileSystemRepresentation(ResourceURL, TRUE, (UInt8*)ResourcePath, sizeof(ResourcePath))))
        {
            CC_LOG_ERROR("Could not find asset path");
            return EXIT_FAILURE;
        }
        
        CFRelease(ResourceURL);
        
        HKAssetPath = FSPathCreateFromSystemPath(ResourcePath);
    }

    else
#endif
    {
        CCOrderedCollection(FSPathComponent) Path = FSPathConvertSystemPathToComponents(argv[0], TRUE);
        CCOrderedCollectionRemoveLastElement(Path);
        HKAssetPath = FSPathCreateFromComponents(Path);
    }
    
    FSPathAppendComponent(HKAssetPath, FSPathComponentCreate(FSPathComponentTypeDirectory, "assets"));
    
    B2EngineConfiguration.project = FSPathCopy(HKAssetPath);
    FSPathAppendComponent(B2EngineConfiguration.project, FSPathComponentCreate(FSPathComponentTypeFile, "game"));
    FSPathAppendComponent(B2EngineConfiguration.project, FSPathComponentCreate(FSPathComponentTypeExtension, "gamepkg"));
    
    return B2EngineRun(argc, argv);
}
