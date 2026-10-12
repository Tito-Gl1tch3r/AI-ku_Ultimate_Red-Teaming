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

#include "HubArchAssembly.h"
#include "HubArchInstruction.h"

#define HK_HUB_ARCH_ASSEMBLY_COMPILE_DEPTH_MAX 512

typedef enum {
    HKHubArchAssemblyIfBlockTaken,
    HKHubArchAssemblyIfBlockNotTaken,
    HKHubArchAssemblyIfBlockEnd,
    
    HKHubArchAssemblyIfBlockNone = HKHubArchAssemblyIfBlockTaken
} HKHubArchAssemblyIfBlock;

CC_ARRAY_DECLARE(HKHubArchAssemblyIfBlock);

static inline HKHubArchAssemblyIfBlock HKHubArchAssemblyIfBlockCurrent(CCArray(HKHubArchAssemblyIfBlock) IfBlocks)
{
    const size_t Count = CCArrayGetCount(IfBlocks);
    if (Count) return *(HKHubArchAssemblyIfBlock*)CCArrayGetElementAtIndex(IfBlocks, Count - 1);
    
    return HKHubArchAssemblyIfBlockNone;
}

typedef struct {
    CCOrderedCollection(HKHubArchAssemblyASTNode) ast;
    CCOrderedCollection(CCString) args;
} HKHubArchAssemblyMacro;

typedef struct {
    CCString name;
    size_t count;
} HKHubArchAssemblyMacroName;

CC_DICTIONARY_DECLARE(HKHubArchAssemblyMacroName, HKHubArchAssemblyMacro);

CC_DICTIONARY_DECLARE(CCOrderedCollection(HKHubArchAssemblyASTNode), CCDictionary(CCString, uint8_t));

typedef struct {
    CCOrderedCollection(HKHubArchAssemblyASTError) errors;
    CCOrderedCollection(HKHubArchAssemblyASTError) hardErrors;
    CCDictionary(CCString, uint8_t) labels;
    CCDictionary(CCString, uint8_t) defines;
    CCArray(HKHubArchAssemblyIfBlock) ifBlocks;
    CCDictionary(HKHubArchAssemblyMacroName, HKHubArchAssemblyMacro) macros;
    CCDictionary(CCOrderedCollection(HKHubArchAssemblyASTNode), CCDictionary(CCString, uint8_t)) scopedLabels;
    HKHubArchAssemblySymbolExpansion expand;
    struct {
        CCDictionary(CCString, uint8_t) labels;
        CCDictionary(CCString, uint8_t) defines;
        CCDictionary(HKHubArchAssemblyMacroName, HKHubArchAssemblyMacro) macros;
    } saved;
    _Bool *stop;
    size_t *counter;
    struct {
        uint16_t count;
        uint8_t offset;
    } bits;
} HKHubArchAssemblyCompilationContext;

static size_t HKHubArchAssemblyRecursiveCompile(size_t Offset, HKHubArchBinary Binary, CCOrderedCollection(HKHubArchAssemblyASTNode) AST, HKHubArchAssemblyCompilationContext *Context, int Pass, size_t Depth, HKHubArchAssemblyASTNode *Command);

static void HKHubArchAssemblyMacroDestructor(void *Container, HKHubArchAssemblyMacro *Macro);
static uintmax_t HKHubArchAssemblyMacroNameHasher(HKHubArchAssemblyMacroName *Key);
static CCComparisonResult HKHubArchAssemblyMacroNameComparator(HKHubArchAssemblyMacroName *Left, HKHubArchAssemblyMacroName *Right);

static void HKHubArchAssemblyASTNodeDestructor(void *Container, HKHubArchAssemblyASTNode *Node)
{
    if (Node->string) CCStringDestroy(Node->string);
    if (Node->childNodes) CCCollectionDestroy(Node->childNodes);
}

#define CC_CONTAINER_TYPE_DISABLE
static size_t HKHubArchAssemblyResolveLiteralValue(CCArray(HKHubArchAssemblyASTNode *) Parents, const char *String, size_t Length, _Bool Hex, _Bool Sym, _Bool Dec, char Operator)
{
#undef CC_CONTAINER_TYPE_DISABLE
    const size_t Index = CCArrayGetCount(Parents) - 1;
    if ((Operator == ')') && (Index))
    {
        CCArrayRemoveElementAtIndex(Parents, Index);
        return 0;
    }
    
    HKHubArchAssemblyASTNode *Parent = *(HKHubArchAssemblyASTNode**)CCArrayGetElementAtIndex(Parents, Index);
    
    HKHubArchAssemblyASTNode Node = {
        .type = HKHubArchAssemblyASTTypeUnknown,
        .line = Parent->line,
        .childNodes = NULL
    };
    
    size_t Skip = 0;
    
    if ((Hex) || (Dec))
    {
        Node.type = HKHubArchAssemblyASTTypeInteger;
        Node.integer.value = (uint8_t)strtol(String, NULL, Dec ? 10 : 16);
    }
    
    else if (Sym)
    {
        Node.type = HKHubArchAssemblyASTTypeSymbol;
    }
    
    else
    {
        switch (Operator)
        {
            case '?':
                Node.type = HKHubArchAssemblyASTTypeRandom;
                break;
                
            case '.':
                Node.type = HKHubArchAssemblyASTTypeOffset;
                break;
                
            case '+':
                Node.type = HKHubArchAssemblyASTTypePlus;
                break;
                
            case '-':
                Node.type = HKHubArchAssemblyASTTypeMinus;
                break;
                
            case '*':
                Node.type = HKHubArchAssemblyASTTypeMultiply;
                break;
                
            case '/':
                Node.type = HKHubArchAssemblyASTTypeDivide;
                break;
                
            case '%':
                Node.type = HKHubArchAssemblyASTTypeModulo;
                break;
                
            case '!':
            {
                switch (String[1])
                {
                    case '=':
                        Skip = 1;
                        Node.type = HKHubArchAssemblyASTTypeNotEqual;
                        break;
                        
                    default:
                        Node.type = HKHubArchAssemblyASTTypeNot;
                        break;
                }
                break;
            }
                
            case '~':
                Node.type = HKHubArchAssemblyASTTypeOnesComplement;
                break;
                
            case '=':
                if (String[1])
                {
                    Skip = 1;
                    Node.type = HKHubArchAssemblyASTTypeEqual;
                }
                break;
                
            case '<':
            {
                switch (String[1])
                {
                    case '<':
                        Skip = 1;
                        Node.type = HKHubArchAssemblyASTTypeShiftLeft;
                        break;
                        
                    case '=':
                        Skip = 1;
                        Node.type = HKHubArchAssemblyASTTypeLessThanOrEqual;
                        break;
                        
                    default:
                        Node.type = HKHubArchAssemblyASTTypeLessThan;
                        break;
                }
                break;
            }
                
            case '>':
            {
                switch (String[1])
                {
                    case '>':
                        Skip = 1;
                        Node.type = HKHubArchAssemblyASTTypeShiftRight;
                        break;
                        
                    case '=':
                        Skip = 1;
                        Node.type = HKHubArchAssemblyASTTypeGreaterThanOrEqual;
                        break;
                        
                    default:
                        Node.type = HKHubArchAssemblyASTTypeGreaterThan;
                        break;
                }
                break;
            }
                
            case '&':
            {
                switch (String[1])
                {
                    case '&':
                        Skip = 1;
                        Node.type = HKHubArchAssemblyASTTypeLogicalAnd;
                        break;
                        
                    default:
                        Node.type = HKHubArchAssemblyASTTypeBitwiseAnd;
                        break;
                }
                break;
            }
                
            case '|':
            {
                switch (String[1])
                {
                    case '|':
                        Skip = 1;
                        Node.type = HKHubArchAssemblyASTTypeLogicalOr;
                        break;
                        
                    default:
                        Node.type = HKHubArchAssemblyASTTypeBitwiseOr;
                        break;
                }
                break;
            }
                
            case '^':
                Node.type = HKHubArchAssemblyASTTypeBitwiseXor;
                break;
                
            case '(':
                Node.type = HKHubArchAssemblyASTTypeExpression;
                Node.childNodes = CCCollectionCreate(CC_STD_ALLOCATOR, CCCollectionHintOrdered, sizeof(HKHubArchAssemblyASTNode), (CCCollectionElementDestructor)HKHubArchAssemblyASTNodeDestructor);
                break;
        }
    }
    
    if (!Parent->childNodes) Parent->childNodes = CCCollectionCreate(CC_STD_ALLOCATOR, CCCollectionHintOrdered, sizeof(HKHubArchAssemblyASTNode), (CCCollectionElementDestructor)HKHubArchAssemblyASTNodeDestructor);
    
    if (Node.type != HKHubArchAssemblyASTTypeExpression) Node.string = CCStringCreateWithSize(CC_STD_ALLOCATOR, CCStringHintCopy | CCStringEncodingASCII, String, Length + Skip);
    
    CCCollectionEntry Entry = CCOrderedCollectionAppendElement(Parent->childNodes, &Node);
    
    if (Node.type == HKHubArchAssemblyASTTypeExpression)
    {
        HKHubArchAssemblyASTNode *ExpressionNode = CCCollectionGetElement(Parent->childNodes, Entry);
        CCArrayAppendElement(Parents, &ExpressionNode);
    }
    
    return Skip;
}

static void HKHubArchAssemblyParseOperand(HKHubArchAssemblyASTNode *Node)
{
#define CC_CONTAINER_TYPE_DISABLE
    CCArray(HKHubArchAssemblyASTNode *) Parents = CCArrayCreate(CC_STD_ALLOCATOR, sizeof(HKHubArchAssemblyASTNode*), 16);
#undef CC_CONTAINER_TYPE_DISABLE
    CCArrayAppendElement(Parents, &Node);
    
    CCOrderedCollection(CCString) Strings = CCStringCreateBySeparatingOccurrencesOfGroupedStrings(Node->string, (CCString[2]){ CC_STRING(" "), CC_STRING("\t") }, 2);
    
    CC_COLLECTION_FOREACH(CCString, String, Strings)
    {
        if (CCStringGetLength(String))
        {
            CC_STRING_TEMP_BUFFER(Buffer, String)
            {
                const char *Start = Buffer;
                _Bool Hex = FALSE, Sym = FALSE, Dec = FALSE, CreateNode = FALSE;
                size_t Index = 0;
                for (char c; (c = *(Buffer++)); Index++)
                {
                    if ((isalnum(c)) || (c == '_'))
                    {
                        if (!CreateNode)
                        {
                            Hex = TRUE;
                            Sym = TRUE;
                            Dec = TRUE;
                        }
                        
                        CreateNode = TRUE;
                        
                        if ((Index == 0) && (c != '0')) Hex = FALSE;
                        else if ((Index == 1) && ((c != 'x') && (c != 'X'))) Hex = FALSE;
                        
                        if ((!isxdigit(c)) && ((Index != 1) || ((c != 'x') && (c != 'X'))))
                        {
                            Hex = FALSE;
                            Dec = FALSE;
                        }
                        
                        else if (!isdigit(c))
                        {
                            Dec = FALSE;
                        }
                    }
                    
                    else
                    {
                        if (CreateNode) Buffer += HKHubArchAssemblyResolveLiteralValue(Parents, Start, (Buffer - Start) - 1, Hex, Sym, Dec, 0);
                        
                        Hex = FALSE;
                        Sym = FALSE;
                        Dec = FALSE;
                        CreateNode = FALSE;
                        Index = -1;
                        
                        Buffer += HKHubArchAssemblyResolveLiteralValue(Parents, Buffer - 1, 1, Hex, Sym, Dec, c);
                        Start = Buffer;
                    }
                }
                
                if (CreateNode) HKHubArchAssemblyResolveLiteralValue(Parents, Start, (Buffer - Start) - 1, Hex, Sym, Dec, 0);
            }
        }
    }
    
    CCCollectionDestroy(Strings);
    CCArrayDestroy(Parents);
}

static void HKHubArchAssemblyParseCommand(const char **Source, size_t *Line, HKHubArchAssemblyASTType ParentType, CCOrderedCollection(HKHubArchAssemblyASTNode) AST)
{
    HKHubArchAssemblyASTType Type = HKHubArchAssemblyASTTypeInstruction;
    const char *Symbol = NULL, *String = NULL;
    _Bool IsStr = FALSE, IsComment = FALSE, IsEscape = FALSE, IsCommand = ParentType == HKHubArchAssemblyASTTypeSource;
    for (char c = 0; (c = **Source); (*Source)++)
    {
        if (!Symbol) Symbol = *Source;
        
        if ((!IsComment) && (!IsStr) && (IsCommand) && (c == '.'))
        {
            Type = HKHubArchAssemblyASTTypeDirective;
        }
        
        else if ((!IsComment) && (!IsStr) && (IsCommand) && (c == ':'))
        {
            Type = HKHubArchAssemblyASTTypeLabel;
        }
        
        else if ((!IsComment) && (!IsStr) && (!IsCommand) && (c == '['))
        {
            HKHubArchAssemblyASTNode Node = {
                .type = HKHubArchAssemblyASTTypeMemory,
                .string = 0,
                .line = *Line,
                .childNodes = CCCollectionCreate(CC_STD_ALLOCATOR, CCCollectionHintOrdered, sizeof(HKHubArchAssemblyASTNode), (CCCollectionElementDestructor)HKHubArchAssemblyASTNodeDestructor)
            };
            
            (*Source)++;
            HKHubArchAssemblyParseCommand(Source, Line, Type, Node.childNodes);
            CCOrderedCollectionAppendElement(AST, &Node);
            
            Symbol = NULL;
            Type = HKHubArchAssemblyASTTypeInstruction;
            
            if (**Source == '\n') return;
        }
        
        else if ((!IsComment) && (!IsEscape) && (!IsCommand) && (c == '"'))
        {
            if (!(IsStr = !IsStr))
            {
                const size_t Length = *Source - String - 1;
                
                HKHubArchAssemblyASTNode Node = {
                    .type = HKHubArchAssemblyASTTypeString,
                    .string = CCStringCreateWithSize(CC_STD_ALLOCATOR, CCStringHintCopy | CCStringEncodingUTF8, String + 1, Length),
                    .line = *Line,
                    .childNodes = NULL
                };
                
                CCOrderedCollectionAppendElement(AST, &Node);
                
                String = NULL;
                Symbol = NULL;
            }
            
            else String = *Source;
        }
        
        else if ((!IsComment) && (!IsStr) && (((IsCommand) && (isspace(c))) || (c == '\n') || (c == ',') || ((c == '#') && (IsComment = TRUE)) || (c == ']')))
        {
            if (*Source != Symbol)
            {
                const size_t Length = (*Source - Symbol) - (Type != HKHubArchAssemblyASTTypeLabel ? 0 : 1);
                if (ParentType != HKHubArchAssemblyASTTypeSource) Type = HKHubArchAssemblyASTTypeOperand;
                
                HKHubArchAssemblyASTNode Node = {
                    .type = Type,
                    .string = CCStringCreateWithSize(CC_STD_ALLOCATOR, CCStringHintCopy | CCStringEncodingASCII, Symbol, Length),
                    .line = *Line,
                    .childNodes = NULL
                };
                
                if ((!IsComment) && (c != '\n') && ((Type == HKHubArchAssemblyASTTypeInstruction) || (Type == HKHubArchAssemblyASTTypeDirective)))
                {
                    Node.childNodes = CCCollectionCreate(CC_STD_ALLOCATOR, CCCollectionHintOrdered, sizeof(HKHubArchAssemblyASTNode), (CCCollectionElementDestructor)HKHubArchAssemblyASTNodeDestructor);
                    HKHubArchAssemblyParseCommand(Source, Line, Type, Node.childNodes);
                    
                    if (!CCCollectionGetCount(Node.childNodes))
                    {
                        CCCollectionDestroy(Node.childNodes);
                        Node.childNodes = NULL;
                    }
                }
                
                else if (Type == HKHubArchAssemblyASTTypeOperand)
                {
                    HKHubArchAssemblyParseOperand(&Node);
                    
                    if (!Node.childNodes) goto SkipNode;
                }
                
                CCOrderedCollectionAppendElement(AST, &Node);
            SkipNode:
                
                if (c == ']') return;
            }
            
            Symbol = NULL;
            Type = HKHubArchAssemblyASTTypeInstruction;
        }
        
        else if ((!IsStr) && (c == '#'))
        {
            IsComment = TRUE;
        }
        
        else if (IsEscape)
        {
            IsEscape = FALSE;
        }
        
        else if (c == '\\')
        {
            IsEscape = TRUE;
        }
        
        if (c == '\n')
        {
            Symbol = NULL;
            IsComment = FALSE;
            (*Line)++;
            
            if (ParentType != HKHubArchAssemblyASTTypeSource) return;
        }
    }
    
    if ((Symbol) && (*Symbol) && (!**Source))
    {
        const size_t Length = *Source - Symbol;
        if (ParentType != HKHubArchAssemblyASTTypeSource) Type = HKHubArchAssemblyASTTypeOperand;
        
        HKHubArchAssemblyASTNode Node = {
            .type = Type,
            .string = CCStringCreateWithSize(CC_STD_ALLOCATOR, CCStringHintCopy | CCStringEncodingASCII, Symbol, Length),
            .line = *Line,
            .childNodes = NULL
        };
        
        if (Type == HKHubArchAssemblyASTTypeOperand)
        {
            HKHubArchAssemblyParseOperand(&Node);
        }
        
        CCOrderedCollectionAppendElement(AST, &Node);
    }
}

CCOrderedCollection(HKHubArchAssemblyASTNode) HKHubArchAssemblyParse(const char *Source)
{
    CCAssertLog(Source, "Source must not be null");
    
    CCOrderedCollection(HKHubArchAssemblyASTNode) AST = CCCollectionCreate(CC_STD_ALLOCATOR, CCCollectionHintOrdered, sizeof(HKHubArchAssemblyASTNode), (CCCollectionElementDestructor)HKHubArchAssemblyASTNodeDestructor);
    
    HKHubArchAssemblyParseCommand(&Source, &(size_t){ 0 }, HKHubArchAssemblyASTTypeSource, AST);
    
    return AST;
}

_Bool HKHubArchAssemblyResolveSymbol(HKHubArchAssemblyASTNode *Value, uint8_t *Result, CCDictionary(CCString, uint8_t) Labels, CCDictionary(CCString, uint8_t) Defines, const HKHubArchAssemblySymbolExpansion *Expansion)
{
    uint8_t *Data;
    if (((HKHubArchAssemblyExpandSymbol(Value->string, Expansion, HKHubArchAssemblySymbolExpansionTypeDefine)) && (Data = CCDictionaryGetValue(Defines, &Value->string))) || ((HKHubArchAssemblyExpandSymbol(Value->string, Expansion, HKHubArchAssemblySymbolExpansionTypeLabel)) && (Data = CCDictionaryGetValue(Labels, &Value->string))))
    {
        *Result = *Data;
        return TRUE;
    }
    
    return FALSE;
}

_Bool HKHubArchAssemblyExpandSymbol(CCString Symbol, const HKHubArchAssemblySymbolExpansion *Expansion, HKHubArchAssemblySymbolExpansionType Type)
{
    if (!Expansion) return TRUE;
    
    HKHubArchAssemblySymbolExpansionRules *Rules = CCDictionaryGetValue(Expansion->symbols, &Symbol);
    
    return Rules ? *(_Bool*)((void*)Rules + Type) : *(_Bool*)((void*)&Expansion->defaults + Type);
}

#pragma mark - Error Messages

static const CCString HKHubArchAssemblyErrorMessageOperand1Symbol = CC_STRING("operand 1 should be a symbol");
static const CCString HKHubArchAssemblyErrorMessageOperand2Symbol = CC_STRING("operand 2 should be a symbol");
static const CCString HKHubArchAssemblyErrorMessageOperand1SymbolOrInteger = CC_STRING("operand 1 should be a symbol or integer");
static const CCString HKHubArchAssemblyErrorMessageOperand2SymbolOrInteger = CC_STRING("operand 2 should be a symbol or integer");
static const CCString HKHubArchAssemblyErrorMessageOperand3SymbolOrInteger = CC_STRING("operand 3 should be a symbol or integer");
static const CCString HKHubArchAssemblyErrorMessageOperand1String = CC_STRING("operand 1 should be a string");
static const CCString HKHubArchAssemblyErrorMessageOperandInteger = CC_STRING("operand should be an integer");
static const CCString HKHubArchAssemblyErrorMessageOperandString = CC_STRING("operand should be a string");
static const CCString HKHubArchAssemblyErrorMessageOperandSymbol = CC_STRING("operand should be a symbol");
static const CCString HKHubArchAssemblyErrorMessageOperandResolveInteger = CC_STRING("could not resolve operand to integer");
static const CCString HKHubArchAssemblyErrorMessageOperandResolveIntegerMinusRegister = CC_STRING("cannot resolve the equation when register is to the right of the minus sign");
static const CCString HKHubArchAssemblyErrorMessageMin0Max0Operands = CC_STRING("expects no operands");
static const CCString HKHubArchAssemblyErrorMessageMin0Max2Operands = CC_STRING("expects 0 to 2 operands");
static const CCString HKHubArchAssemblyErrorMessageMin1MaxNOperands = CC_STRING("expects 1 or more operands");
static const CCString HKHubArchAssemblyErrorMessageMin1Max2Operands = CC_STRING("expects 1 to 2 operands");
static const CCString HKHubArchAssemblyErrorMessageMin2Max3Operands = CC_STRING("expects 2 to 3 operands");
static const CCString HKHubArchAssemblyErrorMessageMin1Max1Operands = CC_STRING("expects 1 operand");
static const CCString HKHubArchAssemblyErrorMessageMin2Max2Operands = CC_STRING("expects 2 operands");
static const CCString HKHubArchAssemblyErrorMessageSizeLimit = CC_STRING("exceeded size limit");
static const CCString HKHubArchAssemblyErrorMessageCompileDepthLimit = CC_STRING("exceeded compile depth limit");
static const CCString HKHubArchAssemblyErrorMessageUnknownCommand = CC_STRING("unknown command");

#pragma mark - Directives
CCOrderedCollection(FSPath) HKHubArchAssemblyIncludeSearchPaths = NULL;
static const CCString HKHubArchAssemblyErrorMessageFile = CC_STRING("could not find file");
static const CCString HKHubArchAssemblyErrorMessageSearchPaths = CC_STRING("no include search paths specified");

static size_t HKHubArchAssemblyCompileInclude(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyASTNode *ProcOp, HKHubArchAssemblyASTNode *Proc, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCString IncludePath)
{
    if ((HKHubArchAssemblyIncludeSearchPaths) && (CCCollectionGetCount(HKHubArchAssemblyIncludeSearchPaths)))
    {
        CCOrderedCollection(FSPathComponent) FileComponents = NULL;
        CC_STRING_TEMP_BUFFER(Name, IncludePath) FileComponents = FSPathConvertPathToComponents(Name, FALSE);
        CCOrderedCollectionAppendElement(FileComponents, &(FSPathComponent){ FSPathComponentCreate(FSPathComponentTypeExtension, "chasm") });
        
        const FSPathComponentType PathType = FSPathComponentGetType(*(FSPathComponent*)CCOrderedCollectionGetElementAtIndex(FileComponents, 0));
        _Bool Found = FALSE;
        FSPath Path = NULL;
        
        if ((PathType != FSPathComponentTypeVolume) && (PathType != FSPathComponentTypeRoot))
        {
            CC_COLLECTION_FOREACH(FSPath, SearchPath, HKHubArchAssemblyIncludeSearchPaths)
            {
                Path = FSPathCopy(SearchPath);
                
                CC_COLLECTION_FOREACH(FSPathComponent, Component, FileComponents) FSPathAppendComponent(Path, FSPathComponentCopy(Component));
                
                if ((Found = FSManagerExists(Path))) break;
                
                FSPathDestroy(Path);
                Path = NULL;
            }
        }
        
        else
        {
            Path = FSPathCreateFromComponents(FileComponents);
            Found = FSManagerExists(Path);
        }
        
        if (Found)
        {
            FSHandle Handle;
            if (FSHandleOpen(Path, FSHandleTypeRead, &Handle) == FSOperationSuccess)
            {
                size_t Size = FSManagerGetSize(Path);
                char *Source;
                CC_SAFE_Malloc(Source, sizeof(char) * (Size + 2));
                
                FSHandleRead(Handle, &Size, Source, FSBehaviourDefault);
                Source[Size] = '\n';
                Source[Size + 1] = 0;
                
                FSHandleClose(Handle);
                
                CCOrderedCollection(HKHubArchAssemblyASTNode) AST = HKHubArchAssemblyParse(Source);
                CC_SAFE_Free(Source);
                
                Offset = HKHubArchAssemblyRecursiveCompile(Offset, Binary, AST, Context, !Binary, Depth, Command);
                
                if (Command->string) CCStringDestroy(Command->string);
                if (Command->childNodes) CCCollectionDestroy(Command->childNodes);
                
                Command->type = HKHubArchAssemblyASTTypeAST;
                Command->string = 0;
                Command->childNodes = AST;
            }
            
            else
            {
                CC_LOG_ERROR("Could not open file (%s)", FSPathGetPathString(Path));
                
                CCString File = CCStringCreate(CC_STD_ALLOCATOR, 0, FSPathGetPathString(Path));
                CCString ErrMsg = CCStringCreateByJoiningStrings((CCString[]){
                    CC_STRING("unable to open file ("),
                    File,
                    CC_STRING(")")
                }, 3, 0);
                
                CCStringDestroy(File);
                
                HKHubArchAssemblyErrorAddMessage(Context->errors, ErrMsg, Command, ProcOp, Proc);
            }
        }
        
        else
        {
            HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageFile, Command, ProcOp, Proc);
        }
        
        if (Path) FSPathDestroy(Path);
    }
    
    else
    {
        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageSearchPaths, Command, ProcOp, Proc);
    }
    
    return Offset;
}

static size_t HKHubArchAssemblyCompileDirectiveInclude(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) != HKHubArchAssemblyIfBlockTaken) return Offset;
    
    if ((Command->childNodes) && (CCCollectionGetCount(Command->childNodes) == 1))
    {
        HKHubArchAssemblyASTNode *ProcOp = CCOrderedCollectionGetElementAtIndex(Command->childNodes, 0);

        if ((ProcOp->type == HKHubArchAssemblyASTTypeOperand) && (ProcOp->childNodes) && (CCCollectionGetCount(ProcOp->childNodes) == 1))
        {
            HKHubArchAssemblyASTNode *Proc = CCOrderedCollectionGetElementAtIndex(ProcOp->childNodes, 0);

            if (Proc->type == HKHubArchAssemblyASTTypeSymbol)
            {
                Offset = HKHubArchAssemblyCompileInclude(Offset, Binary, Command, ProcOp, Proc, Context, Depth, Proc->string);
            }

            else
            {
                HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperand1Symbol, Command, ProcOp, Proc);
            }
        }
        
        else if (ProcOp->type == HKHubArchAssemblyASTTypeString)
        {
            Offset = HKHubArchAssemblyCompileInclude(Offset, Binary, Command, ProcOp, NULL, Context, Depth, ProcOp->string);
        }
        
        else
        {
            HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperand1Symbol, Command, ProcOp, NULL);
        }
    }

    else
    {
        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageMin1Max1Operands, Command, NULL, NULL);
    }
    
    return Offset;
}

static const CCString HKHubArchAssemblyErrorAssertion = CC_STRING("assertion failed");

static size_t HKHubArchAssemblyCompileDirectiveAssert(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) != HKHubArchAssemblyIfBlockTaken) return Offset;
    
    size_t Count;
    if ((Command->childNodes) && ((Count = CCCollectionGetCount(Command->childNodes)) >= 1) && (Count <= 2))
    {
        HKHubArchAssemblyASTNode *ExpressionOp = CCOrderedCollectionGetElementAtIndex(Command->childNodes, 0);
        
        if ((ExpressionOp->type == HKHubArchAssemblyASTTypeOperand) && (ExpressionOp->childNodes))
        {
            uint8_t Result;
            if (HKHubArchAssemblyResolveInteger(Offset, &Result, Command, ExpressionOp, Context->errors, Context->labels, Context->defines, NULL, &Context->expand))
            {
                if (!Result)
                {
                    CCString Message = HKHubArchAssemblyErrorAssertion;
                    if (Count == 2)
                    {
                        HKHubArchAssemblyASTNode *MessageOp = CCOrderedCollectionGetElementAtIndex(Command->childNodes, 1);
                        
                        if (MessageOp->type == HKHubArchAssemblyASTTypeString)
                        {
                            Message = CCStringCreateByJoiningStrings((CCString[2]){ HKHubArchAssemblyErrorAssertion, MessageOp->string }, 2, CC_STRING(": "));
                        }
                        
                        else
                        {
                            HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandString, Command, MessageOp, NULL);
                        }
                    }
                    
                    HKHubArchAssemblyErrorAddMessage(Context->errors, Message, Command, ExpressionOp, NULL);
                }
            }
        }
        
        else
        {
            HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandInteger, Command, ExpressionOp, NULL);
        }
    }
    
    else
    {
        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageMin1Max2Operands, Command, NULL, NULL);
    }
    
    return Offset;
}

static size_t HKHubArchAssemblyCompileDirectivePort(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) != HKHubArchAssemblyIfBlockTaken) return Offset;
    
    size_t Count;
    if ((Command->childNodes) && ((Count = CCCollectionGetCount(Command->childNodes)) >= 2) && (Count <= 3))
    {
        HKHubArchAssemblyASTNode *NameOp = CCOrderedCollectionGetElementAtIndex(Command->childNodes, 0);
        
        if ((NameOp->type == HKHubArchAssemblyASTTypeOperand) && (NameOp->childNodes) && (CCCollectionGetCount(NameOp->childNodes) == 1))
        {
            HKHubArchAssemblyASTNode *PortOp = CCOrderedCollectionGetElementAtIndex(Command->childNodes, 1);
            
            if ((PortOp->type == HKHubArchAssemblyASTTypeOperand) && (PortOp->childNodes) && (CCCollectionGetCount(PortOp->childNodes) >= 1))
            {
                HKHubArchAssemblyASTNode *Name = CCOrderedCollectionGetElementAtIndex(NameOp->childNodes, 0);
                
                if (Name->type == HKHubArchAssemblyASTTypeSymbol)
                {
                    uint8_t Port;
                    if (HKHubArchAssemblyResolveInteger(Offset, &Port, Command, PortOp, Context->errors, Context->labels, Context->defines, NULL, &Context->expand))
                    {
                        CCDictionarySetValue(Context->defines, &Name->string, &Port);
                        
                        uint8_t PortCount = 1;
                        
                        if (Count == 3)
                        {
                            HKHubArchAssemblyASTNode *PortCountOp = CCOrderedCollectionGetElementAtIndex(Command->childNodes, 2);
                            
                            if ((PortCountOp->type == HKHubArchAssemblyASTTypeOperand) && (PortCountOp->childNodes) && (CCCollectionGetCount(PortCountOp->childNodes) >= 1))
                            {
                                if (!HKHubArchAssemblyResolveInteger(Offset, &PortCount, Command, PortCountOp, Context->errors, Context->labels, Context->defines, NULL, &Context->expand))
                                {
                                    HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandResolveInteger, Command, PortCountOp, NULL);
                                    PortCount = 0;
                                }
                            }
                            
                            else
                            {
                                HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperand3SymbolOrInteger, Command, PortCountOp, NULL);
                            }
                        }
                        
                        if ((PortCount) && (Binary))
                        {
                            _Bool RegisterPort = TRUE;
                            const uint8_t LastPort = Port + PortCount - 1;
                            CC_COLLECTION_FOREACH_PTR(HKHubArchBinaryNamedPort, NamedPort, Binary->namedPorts)
                            {
                                const uint8_t LastNamedPort = NamedPort->start + NamedPort->count - 1;
                                if (((Port >= NamedPort->start) || (LastPort >= NamedPort->start)) && ((Port <= LastNamedPort) || (LastPort <= LastNamedPort)))
                                {
                                    RegisterPort = FALSE;
                                    
                                    if (CCStringEqual(Name->string, NamedPort->name))
                                    {
                                        NamedPort->start = Port;
                                        NamedPort->count = PortCount;
                                    }
                                    
                                    else
                                    {
                                        CCString Message = CCStringCreateByJoiningStrings((CCString[5]){
                                            CC_STRING("mapping for port '"),
                                            Name->string,
                                            CC_STRING("' overlaps pre-existing mapping on port '"),
                                            NamedPort->name,
                                            CC_STRING("'")
                                        }, 5, 0);
                                        
                                        HKHubArchAssemblyErrorAddMessage(Context->errors, Message, Command, NULL, NULL);
                                    }
                                }
                            }
                            
                            if (RegisterPort)
                            {
                                CCCollectionInsertElement(Binary->namedPorts, &(HKHubArchBinaryNamedPort){
                                    .name = CCStringCopy(Name->string),
                                    .start = Port,
                                    .count = PortCount
                                });
                            }
                        }
                    }
                    
                    else
                    {
                        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandResolveInteger, Command, PortOp, NULL);
                    }
                }
                
                else
                {
                    HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperand1Symbol, Command, NameOp, Name);
                }
            }
            
            else
            {
                HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperand2SymbolOrInteger, Command, PortOp, NULL);
            }
        }
        
        else
        {
            HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperand1Symbol, Command, NameOp, NULL);
        }
    }
    
    else
    {
        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageMin2Max3Operands, Command, NULL, NULL);
    }
    
    return Offset;
}

static size_t HKHubArchAssemblyCompileDirectiveDefine(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) != HKHubArchAssemblyIfBlockTaken) return Offset;
    
    if ((Command->childNodes) && (CCCollectionGetCount(Command->childNodes) == 2))
    {
        HKHubArchAssemblyASTNode *NameOp = CCOrderedCollectionGetElementAtIndex(Command->childNodes, 0);
        
        if ((NameOp->type == HKHubArchAssemblyASTTypeOperand) && (NameOp->childNodes) && (CCCollectionGetCount(NameOp->childNodes) == 1))
        {
            HKHubArchAssemblyASTNode *AliasOp = CCOrderedCollectionGetElementAtIndex(Command->childNodes, 1);
            
            if ((AliasOp->type == HKHubArchAssemblyASTTypeOperand) && (AliasOp->childNodes) && (CCCollectionGetCount(AliasOp->childNodes) >= 1))
            {
                HKHubArchAssemblyASTNode *Name = CCOrderedCollectionGetElementAtIndex(NameOp->childNodes, 0);
                
                if (Name->type == HKHubArchAssemblyASTTypeSymbol)
                {
                    uint8_t Result;
                    if (HKHubArchAssemblyResolveInteger(Offset, &Result, Command, AliasOp, Context->errors, Context->labels, Context->defines, NULL, &Context->expand))
                    {
                        CCDictionarySetValue(Context->defines, &Name->string, &Result);
                    }
                    
                    else
                    {
                        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandResolveInteger, Command, AliasOp, NULL);
                    }
                }
                
                else
                {
                    HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperand1Symbol, Command, NameOp, Name);
                }
            }
            
            else
            {
                HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperand2SymbolOrInteger, Command, AliasOp, NULL);
            }
        }
        
        else
        {
            HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperand1Symbol, Command, NameOp, NULL);
        }
    }
    
    else
    {
        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageMin2Max2Operands, Command, NULL, NULL);
    }
    
    return Offset;
}

static size_t HKHubArchAssemblyCompileDirectiveByte(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) != HKHubArchAssemblyIfBlockTaken) return Offset;
    
    if (Command->childNodes)
    {
        if (!Binary) return Offset + CCCollectionGetCount(Command->childNodes);
        
        CC_COLLECTION_FOREACH_PTR(HKHubArchAssemblyASTNode, Operand, Command->childNodes)
        {
            if ((Operand->type == HKHubArchAssemblyASTTypeOperand) && (Operand->childNodes))
            {
                HKHubArchAssemblyResolveInteger(Offset, &Binary->data[Offset], Command, Operand, Context->errors, Context->labels, Context->defines, NULL, &Context->expand);
            }
            
            else
            {
                HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandInteger, Command, Operand, NULL);
            }
            
            Offset++;
        }
    }
    
    else
    {
        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageMin1MaxNOperands, Command, NULL, NULL);
    }
    
    return Offset;
}

static size_t HKHubArchAssemblyCompileDirectiveBits(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) != HKHubArchAssemblyIfBlockTaken) return Offset;
    
    if (Command->childNodes)
    {
        if (!((Context->bits.count) && (Context->bits.offset == (Offset - ((Context->bits.count + 7) / 8)))))
        {
            Context->bits.count = 0;
            Context->bits.offset = Offset;
        }
        
        if (Binary)
        {
            CC_COLLECTION_FOREACH_PTR(HKHubArchAssemblyASTNode, Operand, Command->childNodes)
            {
                if ((Operand->type == HKHubArchAssemblyASTTypeOperand) && (Operand->childNodes))
                {
                    const uint8_t Index = Context->bits.count / 8;
                    Offset = Context->bits.offset + Index;
                    
                    uint8_t Result = 0;
                    HKHubArchAssemblyResolveInteger(Offset, &Result, Command, Operand, Context->errors, Context->labels, Context->defines, NULL, &Context->expand);
                    
                    const uint8_t Bit = 7 - (Context->bits.count % 8);
                    if (Bit == 7) Binary->data[Context->bits.offset + Index] = 0;
                    
                    Binary->data[Offset] |= (_Bool)Result << Bit;
                    
                    Context->bits.count++;
                }
                
                else
                {
                    HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandInteger, Command, Operand, NULL);
                }
            }
        }
        
        else Context->bits.count += CCCollectionGetCount(Command->childNodes);
        
        Offset = (size_t)Context->bits.offset + ((Context->bits.count + 7) / 8);
    }
    
    else
    {
        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageMin1MaxNOperands, Command, NULL, NULL);
    }
    
    return Offset;
}

static size_t HKHubArchAssemblyCompileDirectivePadBits(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) != HKHubArchAssemblyIfBlockTaken) return Offset;
    
    const size_t Count = Command->childNodes ? CCCollectionGetCount(Command->childNodes) : 0;
    
    uint8_t Value = 0;
    uint8_t Size = 0;
    _Bool LastByte = TRUE;
    
    switch (Count)
    {
        case 2:
        {
            LastByte = FALSE;
            
            HKHubArchAssemblyASTNode *SizeOp = CCOrderedCollectionGetElementAtIndex(Command->childNodes, 1);
            
            if ((SizeOp->type == HKHubArchAssemblyASTTypeOperand) && (SizeOp->childNodes))
            {
                if (!HKHubArchAssemblyResolveInteger(Offset, &Size, Command, SizeOp, Context->errors, Context->labels, Context->defines, NULL, &Context->expand)) return Offset;
            }
            
            else
            {
                HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandInteger, Command, SizeOp, NULL);
            }
        }
        case 1:
        {
            HKHubArchAssemblyASTNode *ValueOp = CCOrderedCollectionGetElementAtIndex(Command->childNodes, 0);
            
            if ((ValueOp->type == HKHubArchAssemblyASTTypeOperand) && (ValueOp->childNodes))
            {
                if (!HKHubArchAssemblyResolveInteger(Offset, &Value, Command, ValueOp, Context->errors, Context->labels, Context->defines, NULL, &Context->expand)) return Offset;
            }
            
            else
            {
                HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandInteger, Command, ValueOp, NULL);
            }
        }
        case 0:
            break;
            
        default:
            HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageMin0Max2Operands, Command, NULL, NULL);
            return Offset;
    }
    
    if ((Context->bits.count) && (Context->bits.offset == (Offset - ((Context->bits.count + 7) / 8))))
    {
        const uint8_t Index = Context->bits.count / 8;
        Size = Index < Size ? (Size - Index) : 0;
        
        if ((Size) || (LastByte))
        {
            Offset = Context->bits.offset + Index;
            
            const uint8_t Bit = 8 - (Context->bits.count % 8);
            
            if (Binary)
            {
                if (Bit < 8)
                {
                    Binary->data[Offset++] |= Value & CCBitSet(Bit);
                    
                    if (Size) Size--;
                }
                
                while (Size--) Binary->data[Offset++] = Value;
            }
            
            else
            {
                if (Bit < 7) Offset++;
                
                Offset += Size;
            }
        }
        
        Context->bits.count = 0;
        Context->bits.offset = 0;
    }
    
    return Offset;
}

static size_t HKHubArchAssemblyCompileDirectiveEntrypoint(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) != HKHubArchAssemblyIfBlockTaken) return Offset;
    
    if ((Command->childNodes) && (CCCollectionGetCount(Command->childNodes)))
    {
        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageMin0Max0Operands, Command, NULL, NULL);
    }
    
    else if (Binary) Binary->entrypoint = Offset;
    
    return Offset;
}

static size_t HKHubArchAssemblyCompileDirectiveBreakRW(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) != HKHubArchAssemblyIfBlockTaken) return Offset;
    
    size_t Count = 0;
    if ((Command->childNodes) && ((Count = CCCollectionGetCount(Command->childNodes)) > 2))
    {
        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageMin0Max2Operands, Command, NULL, NULL);
    }
    
    else if (Binary)
    {
        uint8_t Args[2] = { Offset, 1 };
        
        if (Count)
        {
            size_t Index = 0;
            CC_COLLECTION_FOREACH_PTR(HKHubArchAssemblyASTNode, Operand, Command->childNodes)
            {
                if ((Operand->type == HKHubArchAssemblyASTTypeOperand) && (Operand->childNodes))
                {
                    HKHubArchAssemblyResolveInteger(Offset, &Args[Index++], Command, Operand, Context->errors, Context->labels, Context->defines, NULL, &Context->expand);
                }
                
                else
                {
                    HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandInteger, Command, Operand, NULL);
                }
            }
        }
        
        for (size_t Loop = 0; Loop < Args[1]; Loop++)
        {
            CCArrayAppendElement(Binary->presetBreakpoints, &(uint8_t){ Args[0] + Loop });
        }
    }
    
    return Offset;
}

static const CCString HKHubArchAssemblyErrorMessageAbsoluteExpression = CC_STRING("must be an absolute expression");

static size_t HKHubArchAssemblyCompileDirectiveIf(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) != HKHubArchAssemblyIfBlockTaken)
    {
        CCArrayAppendElement(Context->ifBlocks, &(HKHubArchAssemblyIfBlock){ HKHubArchAssemblyIfBlockEnd });
        
        return Offset;
    }
    
    if ((Command->childNodes) && (CCCollectionGetCount(Command->childNodes) == 1))
    {
        HKHubArchAssemblyASTNode *ExpressionOp = CCOrderedCollectionGetElementAtIndex(Command->childNodes, 0);
        
        if ((ExpressionOp->type == HKHubArchAssemblyASTTypeOperand) && (ExpressionOp->childNodes))
        {
            uint8_t Result;
            if (HKHubArchAssemblyResolveInteger(Offset, &Result, Command, ExpressionOp, Context->hardErrors, Context->labels, Context->defines, NULL, &Context->expand))
            {
                CCArrayAppendElement(Context->ifBlocks, &(HKHubArchAssemblyIfBlock){ Result ? HKHubArchAssemblyIfBlockTaken : HKHubArchAssemblyIfBlockNotTaken });
            }
            
            else
            {
                HKHubArchAssemblyErrorAddMessage(Context->hardErrors, HKHubArchAssemblyErrorMessageAbsoluteExpression, Command, ExpressionOp, NULL);
            }
        }
        
        else
        {
            HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandInteger, Command, ExpressionOp, NULL);
        }
    }
    
    else
    {
        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageMin1Max1Operands, Command, NULL, NULL);
    }
    
    return Offset;
}

static const CCString HKHubArchAssemblyErrorMessageNoIfBlock = CC_STRING("used outside of if block");

static size_t HKHubArchAssemblyCompileDirectiveElseIf(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    const size_t Count = CCArrayGetCount(Context->ifBlocks);
    if (Count)
    {
        HKHubArchAssemblyIfBlock *CurentBlock = CCArrayGetElementAtIndex(Context->ifBlocks, Count - 1);
        
        if (*CurentBlock == HKHubArchAssemblyIfBlockNotTaken)
        {
            if ((Command->childNodes) && (CCCollectionGetCount(Command->childNodes) == 1))
            {
                HKHubArchAssemblyASTNode *ExpressionOp = CCOrderedCollectionGetElementAtIndex(Command->childNodes, 0);
                
                if ((ExpressionOp->type == HKHubArchAssemblyASTTypeOperand) && (ExpressionOp->childNodes))
                {
                    uint8_t Result;
                    if (HKHubArchAssemblyResolveInteger(Offset, &Result, Command, ExpressionOp, Context->hardErrors, Context->labels, Context->defines, NULL, &Context->expand))
                    {
                        if (Result) *CurentBlock = HKHubArchAssemblyIfBlockTaken;
                    }
                    
                    else
                    {
                        HKHubArchAssemblyErrorAddMessage(Context->hardErrors, HKHubArchAssemblyErrorMessageAbsoluteExpression, Command, ExpressionOp, NULL);
                    }
                }
                
                else
                {
                    HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandInteger, Command, ExpressionOp, NULL);
                }
            }
            
            else
            {
                HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageMin1Max1Operands, Command, NULL, NULL);
            }
        }
        
        else *CurentBlock = HKHubArchAssemblyIfBlockEnd;
    }
    
    else
    {
        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageNoIfBlock, Command, NULL, NULL);
    }
    
    return Offset;
}

static size_t HKHubArchAssemblyCompileDirectiveElse(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    const size_t Count = CCArrayGetCount(Context->ifBlocks);
    if (Count)
    {
        HKHubArchAssemblyIfBlock *CurentBlock = CCArrayGetElementAtIndex(Context->ifBlocks, Count - 1);
        
        if (*CurentBlock == HKHubArchAssemblyIfBlockNotTaken)
        {
            *CurentBlock = HKHubArchAssemblyIfBlockTaken;
            
            if ((Command->childNodes) && (CCCollectionGetCount(Command->childNodes)))
            {
                HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageMin0Max0Operands, Command, NULL, NULL);
            }
        }
        
        else *CurentBlock = HKHubArchAssemblyIfBlockEnd;
    }
    
    else
    {
        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageNoIfBlock, Command, NULL, NULL);
    }
    
    return Offset;
}

static size_t HKHubArchAssemblyCompileDirectiveEndIf(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    const size_t Count = CCArrayGetCount(Context->ifBlocks);
    if (Count)
    {
        CCArrayRemoveElementAtIndex(Context->ifBlocks, Count - 1);
        
        if ((Command->childNodes) && (CCCollectionGetCount(Command->childNodes)))
        {
            HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageMin0Max0Operands, Command, NULL, NULL);
        }
    }
    
    else
    {
        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageNoIfBlock, Command, NULL, NULL);
    }
    
    return Offset;
}

static const CCString HKHubArchAssemblyErrorMessageMacroNotTerminated = CC_STRING("missing .endm");

static size_t HKHubArchAssemblyCompileDirectiveMacro(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) != HKHubArchAssemblyIfBlockTaken) return Offset;
    
    CCOrderedCollection(HKHubArchAssemblyASTNode) MacroAST = CCCollectionCreate(CC_STD_ALLOCATOR, CCCollectionHintOrdered, sizeof(HKHubArchAssemblyASTNode), NULL);
    
    int Count = 1;
    for (HKHubArchAssemblyASTNode *NextCommand; (NextCommand = CCCollectionEnumeratorNext(Enumerator)); )
    {
        if (NextCommand->type == HKHubArchAssemblyASTTypeDirective)
        {
            if (CCStringEqual(CC_STRING(".endm"), NextCommand->string))
            {
                if (--Count == 0) break;
            }
            
            else if (CCStringEqual(CC_STRING(".macro"), NextCommand->string)) Count++;
        }
        
        CCOrderedCollectionAppendElement(MacroAST, NextCommand);
    }
    
    if (!Count)
    {
        if ((Command->childNodes) && (CCCollectionGetCount(Command->childNodes)) >= 1)
        {
            CCEnumerator OperandEnumerator;
            CCCollectionGetEnumerator(Command->childNodes, &OperandEnumerator);
            
            HKHubArchAssemblyASTNode *NameOp = CCCollectionEnumeratorGetCurrent(&OperandEnumerator);
            
            if ((NameOp->type == HKHubArchAssemblyASTTypeOperand) && (NameOp->childNodes) && (CCCollectionGetCount(NameOp->childNodes) == 1))
            {
                HKHubArchAssemblyASTNode *Name = CCOrderedCollectionGetElementAtIndex(NameOp->childNodes, 0);
                
                if (Name->type == HKHubArchAssemblyASTTypeSymbol)
                {
                    CCOrderedCollection(CCString) Args = CCCollectionCreate(CC_STD_ALLOCATOR, CCCollectionHintOrdered, sizeof(CCString), NULL);
                    
                    for (HKHubArchAssemblyASTNode *ArgOp; (ArgOp = CCCollectionEnumeratorNext(&OperandEnumerator)); )
                    {
                        if ((ArgOp->type == HKHubArchAssemblyASTTypeOperand) && (ArgOp->childNodes) && (CCCollectionGetCount(ArgOp->childNodes) == 1))
                        {
                            HKHubArchAssemblyASTNode *Arg = CCOrderedCollectionGetElementAtIndex(ArgOp->childNodes, 0);
                            
                            if (Arg->type == HKHubArchAssemblyASTTypeSymbol)
                            {
                                CCOrderedCollectionAppendElement(Args, &Arg->string);
                            }
                            
                            else
                            {
                                HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandSymbol, Command, ArgOp, Arg);
                                break;
                            }
                        }
                        
                        else
                        {
                            HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandSymbol, Command, ArgOp, NULL);
                            break;
                        }
                    }
                    
                    CCDictionarySetValue(Context->macros, &(HKHubArchAssemblyMacroName){
                        .name = Name->string,
                        .count = CCCollectionGetCount(Args)
                    }, &(HKHubArchAssemblyMacro){
                        .ast = CCRetain(MacroAST),
                        .args = Args
                    });
                }
                
                else
                {
                    HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperand1Symbol, Command, NameOp, Name);
                }
            }
            
            else
            {
                HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperand1Symbol, Command, NameOp, NULL);
            }
        }
        
        else
        {
            HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageMin1MaxNOperands, Command, NULL, NULL);
        }
    }
    
    else
    {
        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageMacroNotTerminated, Command, NULL, NULL);
        CCCollectionEnumeratorGetTail(Enumerator);
    }
    
    CCCollectionDestroy(MacroAST);
    
    return Offset;
}

static const CCString HKHubArchAssemblyErrorMessageMissingMacro = CC_STRING("expected .macro definition");

static size_t HKHubArchAssemblyCompileDirectiveEndMacro(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) != HKHubArchAssemblyIfBlockTaken) return Offset;
    
    HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageMissingMacro, Command, NULL, NULL);
    
    return Offset;
}

static size_t HKHubArchAssemblyCompileSetIndividualExpansionRule(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator, size_t RuleOffset, _Bool Value)
{
    if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) != HKHubArchAssemblyIfBlockTaken) return Offset;
    
    if ((Command->childNodes) && (CCCollectionGetCount(Command->childNodes)))
    {
        CC_COLLECTION_FOREACH_PTR(HKHubArchAssemblyASTNode, Operand, Command->childNodes)
        {
            if ((Operand->type == HKHubArchAssemblyASTTypeOperand) && (Operand->childNodes) && (CCCollectionGetCount(Operand->childNodes) == 1))
            {
                HKHubArchAssemblyASTNode *Symbol = CCOrderedCollectionGetElementAtIndex(Operand->childNodes, 0);
                
                if (Symbol->type == HKHubArchAssemblyASTTypeSymbol)
                {
                    CCDictionaryEntry Entry = CCDictionaryEntryForKey(Context->expand.symbols, &Symbol->string);
                    if (CCDictionaryEntryIsInitialized(Context->expand.symbols, Entry))
                    {
                        *(_Bool*)(CCDictionaryGetEntry(Context->expand.symbols, Entry) + RuleOffset) = Value;
                    }
                    
                    else
                    {
                        HKHubArchAssemblySymbolExpansionRules ExpansionRules = Context->expand.defaults;
                        *(_Bool*)((void*)&ExpansionRules + RuleOffset) = Value;
                        CCDictionarySetEntry(Context->expand.symbols, Entry, &ExpansionRules);
                    }
                }
                
                else
                {
                    HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandSymbol, Command, Operand, Symbol);
                    break;
                }
            }
            
            else
            {
                HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandSymbol, Command, Operand, NULL);
                break;
            }
        }
    }
    
    else
    {
        *(_Bool*)((void*)&Context->expand.defaults + RuleOffset) = Value;
        CC_DICTIONARY_FOREACH_VALUE_PTR(void, Symbol, Context->expand.symbols) *(_Bool*)(Symbol + RuleOffset) = Value;
    }
    
    return Offset;
}

static size_t HKHubArchAssemblyCompileSetAllExpansionRules(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator, HKHubArchAssemblySymbolExpansionRules Rules)
{
    if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) != HKHubArchAssemblyIfBlockTaken) return Offset;
    
    if ((Command->childNodes) && (CCCollectionGetCount(Command->childNodes)))
    {
        CC_COLLECTION_FOREACH_PTR(HKHubArchAssemblyASTNode, Operand, Command->childNodes)
        {
            if ((Operand->type == HKHubArchAssemblyASTTypeOperand) && (Operand->childNodes) && (CCCollectionGetCount(Operand->childNodes) == 1))
            {
                HKHubArchAssemblyASTNode *Symbol = CCOrderedCollectionGetElementAtIndex(Operand->childNodes, 0);
                
                if (Symbol->type == HKHubArchAssemblyASTTypeSymbol)
                {
                    CCDictionaryEntry Entry = CCDictionaryEntryForKey(Context->expand.symbols, &Symbol->string);
                    if (CCDictionaryEntryIsInitialized(Context->expand.symbols, Entry))
                    {
                        *((HKHubArchAssemblySymbolExpansionRules*)CCDictionaryGetEntry(Context->expand.symbols, Entry)) = Rules;
                    }
                    
                    else
                    {
                        CCDictionarySetEntry(Context->expand.symbols, Entry, &Rules);
                    }
                }
                
                else
                {
                    HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandSymbol, Command, Operand, Symbol);
                    break;
                }
            }
            
            else
            {
                HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandSymbol, Command, Operand, NULL);
                break;
            }
        }
    }
    
    else
    {
        Context->expand.defaults = Rules;
        CC_DICTIONARY_FOREACH_VALUE_PTR(HKHubArchAssemblySymbolExpansionRules, Symbol, Context->expand.symbols) *Symbol = Rules;
    }
    
    return Offset;
}

static size_t HKHubArchAssemblyCompileDirectiveNoMacro(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    return HKHubArchAssemblyCompileSetIndividualExpansionRule(Offset, Binary, Command, Context, Depth, Enumerator, offsetof(HKHubArchAssemblySymbolExpansionRules, macro), FALSE);
}

static size_t HKHubArchAssemblyCompileDirectiveNoDefine(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    return HKHubArchAssemblyCompileSetIndividualExpansionRule(Offset, Binary, Command, Context, Depth, Enumerator, offsetof(HKHubArchAssemblySymbolExpansionRules, define), FALSE);
}

static size_t HKHubArchAssemblyCompileDirectiveNoLabel(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    return HKHubArchAssemblyCompileSetIndividualExpansionRule(Offset, Binary, Command, Context, Depth, Enumerator, offsetof(HKHubArchAssemblySymbolExpansionRules, label), FALSE);
}

static size_t HKHubArchAssemblyCompileDirectiveNoExpand(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    return HKHubArchAssemblyCompileSetAllExpansionRules(Offset, Binary, Command, Context, Depth, Enumerator, (HKHubArchAssemblySymbolExpansionRules){ .macro = FALSE, .define = FALSE, .label = FALSE });
}

static size_t HKHubArchAssemblyCompileDirectiveExpand(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    return HKHubArchAssemblyCompileSetAllExpansionRules(Offset, Binary, Command, Context, Depth, Enumerator, (HKHubArchAssemblySymbolExpansionRules){ .macro = TRUE, .define = TRUE, .label = TRUE });
}

static const CCString HKHubArchAssemblyErrorMessageEncoding = CC_STRING("unable to encode argument");

static size_t HKHubArchAssemblyCompileDirectiveError(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) != HKHubArchAssemblyIfBlockTaken) return Offset;
    
    size_t Count;
    if ((Command->childNodes) && ((Count = CCCollectionGetCount(Command->childNodes)) >= 1))
    {
        HKHubArchAssemblyASTNode *String = CCOrderedCollectionGetElementAtIndex(Command->childNodes, 0);
        
        if (String->type == HKHubArchAssemblyASTTypeString)
        {
            CCString *Replacements;
            CC_TEMP_Malloc(Replacements, sizeof(CCString) * Count,
                           CC_LOG_ERROR("Failed to create error message due to allocation failure. Allocation size: %zu", sizeof(CCString) * Count);
                           HKHubArchAssemblyErrorAddMessage(Context->errors, CCStringCopy(String->string), Command, NULL, NULL);
                           return Offset;
                           );
            
            CCString *Occurrences;
            CC_TEMP_Malloc(Occurrences, sizeof(CCString) * Count,
                           CC_LOG_ERROR("Failed to create error message due to allocation failure. Allocation size: %zu", sizeof(CCString) * Count);
                           HKHubArchAssemblyErrorAddMessage(Context->errors, CCStringCopy(String->string), Command, NULL, NULL);
                           CC_TEMP_Free(Replacements);
                           return Offset;
                           );
            
            Replacements[0] = CC_STRING("%");
            Occurrences[0] = CC_STRING("%%");
            
            for (size_t Loop = Count - 1; Loop >= 1; Loop--)
            {
                Replacements[Loop] = 0;
                Occurrences[Loop] = 0;
                
                char Index[22];
                const int IndexLength = snprintf(Index, sizeof(Index), "%%%zu", Loop - 1);
                
                HKHubArchAssemblyASTNode *ArgOp = CCOrderedCollectionGetElementAtIndex(Command->childNodes, Loop);
                
                if ((ArgOp->type == HKHubArchAssemblyASTTypeOperand) && (ArgOp->childNodes))
                {
                    uint8_t Result;
                    if (HKHubArchAssemblyResolveInteger(Offset, &Result, Command, ArgOp, Context->errors, Context->labels, Context->defines, NULL, &Context->expand))
                    {
                        char Value[4];
                        const int ValueLength = snprintf(Value, sizeof(Value), "%u", Result);
                        
                        if ((IndexLength >= 0) && (ValueLength >= 0) && (IndexLength < sizeof(Index)) && (ValueLength < sizeof(Value)))
                        {
                            Replacements[Loop] = CCStringCreateWithSize(CC_STD_ALLOCATOR, CCStringHintCopy | CCStringEncodingASCII, Value, ValueLength);
                            Occurrences[Loop] = CCStringCreateWithSize(CC_STD_ALLOCATOR, CCStringHintCopy | CCStringEncodingASCII, Index, IndexLength);
                        }
                        
                        else
                        {
                            HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageEncoding, Command, ArgOp, NULL);
                        }
                    }
                    
                    else
                    {
                        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandResolveInteger, Command, ArgOp, NULL);
                    }
                }
                
                else
                {
                    HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperand2SymbolOrInteger, Command, ArgOp, NULL);
                }
            }
            
            CCString Message = CCStringCreateByReplacingOccurrencesOfGroupedStrings(String->string, Occurrences, Replacements, Count);
            HKHubArchAssemblyErrorAddMessage(Context->errors, Message, Command, NULL, NULL);
            
            for (size_t Loop = 1; Loop < Count; Loop++)
            {
                if (Replacements[Loop]) CCStringDestroy(Replacements[Loop]);
                if (Occurrences[Loop]) CCStringDestroy(Occurrences[Loop]);
            }
            
            CC_TEMP_Free(Occurrences);
            CC_TEMP_Free(Replacements);
        }
        
        else
        {
            HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperand1String, Command, String, NULL);
        }
    }
    
    else
    {
        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageMin1MaxNOperands, Command, NULL, NULL);
    }
    
    return Offset;
}

typedef HKHubArchAssemblySymbolExpansionRules HKHubArchAssemblySymbolSelection;

static size_t HKHubArchAssemblyCompileSaveSymbol(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator, HKHubArchAssemblySymbolSelection Include)
{
    if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) != HKHubArchAssemblyIfBlockTaken) return Offset;
    
    if ((Command->childNodes) && (CCCollectionGetCount(Command->childNodes)))
    {
        CC_COLLECTION_FOREACH_PTR(HKHubArchAssemblyASTNode, Operand, Command->childNodes)
        {
            if ((Operand->type == HKHubArchAssemblyASTTypeOperand) && (Operand->childNodes) && (CCCollectionGetCount(Operand->childNodes) == 1))
            {
                HKHubArchAssemblyASTNode *Symbol = CCOrderedCollectionGetElementAtIndex(Operand->childNodes, 0);
                
                if (Symbol->type == HKHubArchAssemblyASTTypeSymbol)
                {
                    if (Include.label)
                    {
                        if (!Context->saved.labels)
                        {
                            Context->saved.labels = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeSmall, sizeof(CCString), sizeof(uint8_t), &(CCDictionaryCallbacks){
                                .getHash = CCStringHasherForDictionary,
                                .compareKeys = CCStringComparatorForDictionary
                            });
                        }
                        
                        void *Value = CCDictionaryGetValue(Context->labels, &Symbol->string);
                        if (Value) CCDictionarySetValue(Context->saved.labels, &Symbol->string, Value);
                    }
                    
                    if (Include.define)
                    {
                        if (!Context->saved.defines)
                        {
                            Context->saved.defines = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeSmall, sizeof(CCString), sizeof(uint8_t), &(CCDictionaryCallbacks){
                                .getHash = CCStringHasherForDictionary,
                                .compareKeys = CCStringComparatorForDictionary
                            });
                        }
                        
                        void *Value = CCDictionaryGetValue(Context->defines, &Symbol->string);
                        if (Value) CCDictionarySetValue(Context->saved.defines, &Symbol->string, Value);
                    }
                    
                    if (Include.macro)
                    {
                        if (!Context->saved.macros)
                        {
                            Context->saved.macros = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeSmall, sizeof(HKHubArchAssemblyMacroName), sizeof(HKHubArchAssemblyMacro), &(CCDictionaryCallbacks){
                                .getHash = (CCDictionaryKeyHasher)HKHubArchAssemblyMacroNameHasher,
                                .compareKeys = (CCComparator)HKHubArchAssemblyMacroNameComparator,
                                .valueDestructor = (CCDictionaryElementDestructor)HKHubArchAssemblyMacroDestructor
                            });
                        }
                        
                        CC_DICTIONARY_FOREACH_KEY_PTR(HKHubArchAssemblyMacroName, Key, Context->macros)
                        {
                            if (CCStringEqual(Key->name, Symbol->string))
                            {
                                HKHubArchAssemblyMacro *SrcMacro = CCDictionaryGetValue(Context->macros, Key);
                                CCDictionarySetValue(Context->saved.macros, Key, &(HKHubArchAssemblyMacro){
                                    .ast = CCRetain(SrcMacro->ast),
                                    .args = CCRetain(SrcMacro->args)
                                });
                            }
                        }
                    }
                }
                
                else
                {
                    HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandSymbol, Command, Operand, Symbol);
                    break;
                }
            }
            
            else
            {
                HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageOperandSymbol, Command, Operand, NULL);
                break;
            }
        }
    }
    
    else
    {
        if (Include.label)
        {
            if (!Context->saved.labels)
            {
                Context->saved.labels = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeSmall, sizeof(CCString), sizeof(uint8_t), &(CCDictionaryCallbacks){
                    .getHash = CCStringHasherForDictionary,
                    .compareKeys = CCStringComparatorForDictionary
                });
            }
            
            CC_DICTIONARY_FOREACH_KEY_PTR(CCString, Key, Context->labels) CCDictionarySetValue(Context->saved.labels, Key, CCDictionaryGetValue(Context->labels, Key));
        }
        
        if (Include.define)
        {
            if (!Context->saved.defines)
            {
                Context->saved.defines = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeSmall, sizeof(CCString), sizeof(uint8_t), &(CCDictionaryCallbacks){
                    .getHash = CCStringHasherForDictionary,
                    .compareKeys = CCStringComparatorForDictionary
                });
            }
            
            CC_DICTIONARY_FOREACH_KEY_PTR(CCString, Key, Context->defines) CCDictionarySetValue(Context->saved.defines, Key, CCDictionaryGetValue(Context->defines, Key));
        }
        
        if (Include.macro)
        {
            if (!Context->saved.macros)
            {
                Context->saved.macros = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeSmall, sizeof(HKHubArchAssemblyMacroName), sizeof(HKHubArchAssemblyMacro), &(CCDictionaryCallbacks){
                    .getHash = (CCDictionaryKeyHasher)HKHubArchAssemblyMacroNameHasher,
                    .compareKeys = (CCComparator)HKHubArchAssemblyMacroNameComparator,
                    .valueDestructor = (CCDictionaryElementDestructor)HKHubArchAssemblyMacroDestructor
                });
            }
            
            CC_DICTIONARY_FOREACH_KEY_PTR(HKHubArchAssemblyMacroName, Key, Context->macros)
            {
                HKHubArchAssemblyMacro *SrcMacro = CCDictionaryGetValue(Context->macros, Key);
                CCDictionarySetValue(Context->saved.macros, Key, &(HKHubArchAssemblyMacro){
                    .ast = CCRetain(SrcMacro->ast),
                    .args = CCRetain(SrcMacro->args)
                });
            }
        }
    }
    
    return Offset;
}

static size_t HKHubArchAssemblyCompileDirectiveSaveDefine(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    return HKHubArchAssemblyCompileSaveSymbol(Offset, Binary, Command, Context, Depth, Enumerator, (HKHubArchAssemblySymbolSelection){ .macro = FALSE, .define = TRUE, .label = FALSE });
}

static size_t HKHubArchAssemblyCompileDirectiveSaveLabel(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    return HKHubArchAssemblyCompileSaveSymbol(Offset, Binary, Command, Context, Depth, Enumerator, (HKHubArchAssemblySymbolSelection){ .macro = FALSE, .define = FALSE, .label = TRUE });
}

static size_t HKHubArchAssemblyCompileDirectiveSaveMacro(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    return HKHubArchAssemblyCompileSaveSymbol(Offset, Binary, Command, Context, Depth, Enumerator, (HKHubArchAssemblySymbolSelection){ .macro = TRUE, .define = FALSE, .label = FALSE });
}

static size_t HKHubArchAssemblyCompileDirectiveSave(size_t Offset, HKHubArchBinary Binary, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyCompilationContext *Context, size_t Depth, CCEnumerator *Enumerator)
{
    return HKHubArchAssemblyCompileSaveSymbol(Offset, Binary, Command, Context, Depth, Enumerator, (HKHubArchAssemblySymbolSelection){ .macro = TRUE, .define = TRUE, .label = TRUE });
}

#pragma mark -

static const struct {
    CCString mnemonic;
    size_t (*compile)(size_t, HKHubArchBinary, HKHubArchAssemblyASTNode *, HKHubArchAssemblyCompilationContext *, size_t, CCEnumerator *);
} Directives[] = {
    { CC_STRING(".define"), HKHubArchAssemblyCompileDirectiveDefine },
    { CC_STRING(".byte"), HKHubArchAssemblyCompileDirectiveByte },
    { CC_STRING(".entrypoint"), HKHubArchAssemblyCompileDirectiveEntrypoint },
    { CC_STRING(".include"), HKHubArchAssemblyCompileDirectiveInclude },
    { CC_STRING(".assert"), HKHubArchAssemblyCompileDirectiveAssert },
    { CC_STRING(".port"), HKHubArchAssemblyCompileDirectivePort },
    { CC_STRING(".break"), HKHubArchAssemblyCompileDirectiveBreakRW },
    { CC_STRING(".if"), HKHubArchAssemblyCompileDirectiveIf },
    { CC_STRING(".elseif"), HKHubArchAssemblyCompileDirectiveElseIf },
    { CC_STRING(".else"), HKHubArchAssemblyCompileDirectiveElse },
    { CC_STRING(".endif"), HKHubArchAssemblyCompileDirectiveEndIf },
    { CC_STRING(".macro"), HKHubArchAssemblyCompileDirectiveMacro },
    { CC_STRING(".endm"), HKHubArchAssemblyCompileDirectiveEndMacro },
    { CC_STRING(".nomacro"), HKHubArchAssemblyCompileDirectiveNoMacro },
    { CC_STRING(".nodefine"), HKHubArchAssemblyCompileDirectiveNoDefine },
    { CC_STRING(".nolabel"), HKHubArchAssemblyCompileDirectiveNoLabel },
    { CC_STRING(".noexpand"), HKHubArchAssemblyCompileDirectiveNoExpand },
    { CC_STRING(".expand"), HKHubArchAssemblyCompileDirectiveExpand },
    { CC_STRING(".bits"), HKHubArchAssemblyCompileDirectiveBits },
    { CC_STRING(".padbits"), HKHubArchAssemblyCompileDirectivePadBits },
    { CC_STRING(".error"), HKHubArchAssemblyCompileDirectiveError },
    { CC_STRING(".savedefine"), HKHubArchAssemblyCompileDirectiveSaveDefine },
    { CC_STRING(".savelabel"), HKHubArchAssemblyCompileDirectiveSaveLabel },
    { CC_STRING(".savemacro"), HKHubArchAssemblyCompileDirectiveSaveMacro },
    { CC_STRING(".save"), HKHubArchAssemblyCompileDirectiveSave }
};

static uint8_t HKHubArchAssemblyResolveEquation(uint8_t Left, uint8_t Right, CCArray(HKHubArchAssemblyASTType) Modifiers, HKHubArchAssemblyASTType Operation)
{
    for (size_t Loop = 0, Count = CCArrayGetCount(Modifiers); Loop < Count; Loop++)
    {
        switch (*(HKHubArchAssemblyASTType*)CCArrayGetElementAtIndex(Modifiers, Loop))
        {
            case HKHubArchAssemblyASTTypeMinus:
                Right = -Right;
                break;
                
            case HKHubArchAssemblyASTTypeNot:
                Right = !Right;
                break;
                
            case HKHubArchAssemblyASTTypeOnesComplement:
                Right = ~Right;
                break;
                
            default:
                break;
        }
    }
    
    switch (Operation)
    {
        case HKHubArchAssemblyASTTypeMultiply:
            return Left * Right;
            
        case HKHubArchAssemblyASTTypeDivide:
            return Left / Right;
            
        case HKHubArchAssemblyASTTypeModulo:
            return Left % Right;
            
        case HKHubArchAssemblyASTTypeShiftLeft:
            return Left << Right;
            
        case HKHubArchAssemblyASTTypeShiftRight:
            return Left >> Right;
            
        case HKHubArchAssemblyASTTypeBitwiseAnd:
            return Left & Right;
            
        case HKHubArchAssemblyASTTypeBitwiseOr:
            return Left | Right;
            
        case HKHubArchAssemblyASTTypeBitwiseXor:
            return Left ^ Right;
            
        case HKHubArchAssemblyASTTypeLogicalAnd:
            return Left && Right;
            
        case HKHubArchAssemblyASTTypeLogicalOr:
            return Left || Right;
            
        case HKHubArchAssemblyASTTypeEqual:
            return Left == Right;
            
        case HKHubArchAssemblyASTTypeNotEqual:
            return Left != Right;
            
        case HKHubArchAssemblyASTTypeLessThan:
            return Left < Right;
            
        case HKHubArchAssemblyASTTypeLessThanOrEqual:
            return Left <= Right;
            
        case HKHubArchAssemblyASTTypeGreaterThan:
            return Left > Right;
            
        case HKHubArchAssemblyASTTypeGreaterThanOrEqual:
            return Left >= Right;
            
        default:
            return Left + Right;
    }
}

_Bool HKHubArchAssemblyResolveInteger(size_t Offset, uint8_t *Result, HKHubArchAssemblyASTNode *Command, HKHubArchAssemblyASTNode *Operand, CCOrderedCollection(HKHubArchAssemblyASTError) Errors, CCDictionary(CCString, uint8_t) Labels, CCDictionary(CCString, uint8_t) Defines, CCDictionary(CCString, uint8_t) Variables, const HKHubArchAssemblySymbolExpansion *Expansion)
{
    uint8_t Byte = 0;
    _Bool ConstantOnly = FALSE, Success = TRUE;
    HKHubArchAssemblyASTType Operation = HKHubArchAssemblyASTTypeUnknown;
    CCArray(HKHubArchAssemblyASTType) Modifiers = CCArrayCreate(CC_STD_ALLOCATOR, sizeof(HKHubArchAssemblyASTType), 16);
    
    CC_COLLECTION_FOREACH_PTR(HKHubArchAssemblyASTNode, Value, Operand->childNodes)
    {
        switch (Value->type)
        {
            case HKHubArchAssemblyASTTypeInteger:
                Byte = HKHubArchAssemblyResolveEquation(Byte, Value->integer.value, Modifiers, Operation);
                CCArrayRemoveAllElements(Modifiers);
                ConstantOnly = FALSE;
                Operation = HKHubArchAssemblyASTTypeUnknown;
                break;
                
            case HKHubArchAssemblyASTTypeOffset:
                Byte = HKHubArchAssemblyResolveEquation(Byte, Offset, Modifiers, Operation);
                CCArrayRemoveAllElements(Modifiers);
                ConstantOnly = FALSE;
                Operation = HKHubArchAssemblyASTTypeUnknown;
                break;
                
            case HKHubArchAssemblyASTTypeRandom:
                Byte = HKHubArchAssemblyResolveEquation(Byte, CCRandom() & UINT8_MAX, Modifiers, Operation);
                CCArrayRemoveAllElements(Modifiers);
                ConstantOnly = FALSE;
                Operation = HKHubArchAssemblyASTTypeUnknown;
                break;
                
            case HKHubArchAssemblyASTTypeMinus:
            case HKHubArchAssemblyASTTypeNot:
            case HKHubArchAssemblyASTTypeOnesComplement:
                ConstantOnly = TRUE;
            case HKHubArchAssemblyASTTypePlus:
                CCArrayAppendElement(Modifiers, &Value->type);
                break;
                
            case HKHubArchAssemblyASTTypeMultiply:
            case HKHubArchAssemblyASTTypeDivide:
            case HKHubArchAssemblyASTTypeModulo:
            case HKHubArchAssemblyASTTypeShiftLeft:
            case HKHubArchAssemblyASTTypeShiftRight:
            case HKHubArchAssemblyASTTypeBitwiseAnd:
            case HKHubArchAssemblyASTTypeBitwiseOr:
            case HKHubArchAssemblyASTTypeBitwiseXor:
            case HKHubArchAssemblyASTTypeLogicalAnd:
            case HKHubArchAssemblyASTTypeLogicalOr:
            case HKHubArchAssemblyASTTypeEqual:
            case HKHubArchAssemblyASTTypeNotEqual:
            case HKHubArchAssemblyASTTypeLessThan:
            case HKHubArchAssemblyASTTypeLessThanOrEqual:
            case HKHubArchAssemblyASTTypeGreaterThan:
            case HKHubArchAssemblyASTTypeGreaterThanOrEqual:
            {
                ConstantOnly = TRUE;
                
                if (Operation == HKHubArchAssemblyASTTypeUnknown)
                {
                    Operation = Value->type;
                }
                
                else
                {
                    HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchAssemblyErrorMessageOperandResolveInteger, Command, Operand, Value);
                    Success = FALSE;
                }
                break;
            }
                
            case HKHubArchAssemblyASTTypeSymbol:
            {
                uint8_t ResolvedValue;
                if ((Variables) && (CCDictionaryFindKey(Variables, &Value->string)))
                {
                    if (ConstantOnly)
                    {
                        HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchAssemblyErrorMessageOperandResolveIntegerMinusRegister, Command, Operand, Value);
                        Success = FALSE;
                    }
                }
                
                else if (HKHubArchAssemblyResolveSymbol(Value, &ResolvedValue, Labels, Defines, Expansion))
                {
                    Byte = HKHubArchAssemblyResolveEquation(Byte, ResolvedValue, Modifiers, Operation);
                    CCArrayRemoveAllElements(Modifiers);
                    ConstantOnly = FALSE;
                    Operation = HKHubArchAssemblyASTTypeUnknown;
                }
                
                else
                {
                    HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchAssemblyErrorMessageOperandResolveInteger, Command, Operand, Value);
                    Success = FALSE;
                }
                break;
            }
                
            case HKHubArchAssemblyASTTypeExpression:
            {
                uint8_t ResolvedValue;
                if (HKHubArchAssemblyResolveInteger(Offset, &ResolvedValue, Command, Value, Errors, Labels, Defines, Variables, Expansion))
                {
                    Byte = HKHubArchAssemblyResolveEquation(Byte, ResolvedValue, Modifiers, Operation);
                    CCArrayRemoveAllElements(Modifiers);
                    ConstantOnly = FALSE;
                    Operation = HKHubArchAssemblyASTTypeUnknown;
                }
                
                else
                {
                    HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchAssemblyErrorMessageOperandResolveInteger, Command, Operand, Value);
                    Success = FALSE;
                }
                break;
            }
                
            default:
                HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchAssemblyErrorMessageOperandResolveInteger, Command, Operand, Value);
                Success = FALSE;
                break;
        }
    }
    
    CCArrayDestroy(Modifiers);
    
    if (Result) *Result = Byte;
    
    return Success;
}

static void HKHubArchAssemblyMacroDestructor(void *Container, HKHubArchAssemblyMacro *Macro)
{
    CCCollectionDestroy(Macro->args);
    CCCollectionDestroy(Macro->ast);
}

static uintmax_t HKHubArchAssemblyMacroNameHasher(HKHubArchAssemblyMacroName *Key)
{
    return CCStringGetHash(Key->name) + Key->count;
}

static CCComparisonResult HKHubArchAssemblyMacroNameComparator(HKHubArchAssemblyMacroName *Left, HKHubArchAssemblyMacroName *Right)
{
    return (Left->count == Right->count) && CCStringEqual(Left->name, Right->name) ? CCComparisonResultEqual : CCComparisonResultInvalid;
}

static size_t HKHubArchAssemblyCompile(size_t Offset, HKHubArchBinary Binary, CCOrderedCollection(HKHubArchAssemblyASTNode) AST, HKHubArchAssemblyCompilationContext *Context, int Pass, size_t Depth)
{
    CC_COLLECTION_FOREACH_PTR(HKHubArchAssemblyASTNode, Command, AST)
    {
        (*Context->counter)++;
        
        if (*Context->stop) return Offset;
        
        switch (Command->type)
        {
            case HKHubArchAssemblyASTTypeLabel:
                if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) == HKHubArchAssemblyIfBlockTaken) CCDictionarySetValue(Context->labels, &Command->string, &Offset);
                break;
                
            case HKHubArchAssemblyASTTypeInstruction:
                if (HKHubArchAssemblyIfBlockCurrent(Context->ifBlocks) == HKHubArchAssemblyIfBlockTaken)
                {
                    const HKHubArchAssemblyMacro *Macro = HKHubArchAssemblyExpandSymbol(Command->string, &Context->expand, HKHubArchAssemblySymbolExpansionTypeMacro) ? CCDictionaryGetValue(Context->macros, &(HKHubArchAssemblyMacroName){ .name = Command->string, .count = Command->childNodes ? CCCollectionGetCount(Command->childNodes) : 0 }) : NULL;
                    if (Macro)
                    {
                        HKHubArchAssemblyCompilationContext Local = *Context;
                        
                        Local.saved.labels = NULL;
                        Local.saved.defines = NULL;
                        Local.saved.macros = NULL;
                        
                        CCDictionaryEntry Entry = CCDictionaryEntryForKey(Local.scopedLabels, &(size_t){ *Context->counter });
                        if (!CCDictionaryEntryIsInitialized(Local.scopedLabels, Entry))
                        {
                            Local.labels = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeSmall, sizeof(CCString), sizeof(uint8_t), &(CCDictionaryCallbacks){
                                .getHash = CCStringHasherForDictionary,
                                .compareKeys = CCStringComparatorForDictionary
                            });
                            
                            CCDictionarySetEntry(Local.scopedLabels, Entry, &Local.labels);
                        }
                        
                        else Local.labels = *(CCDictionary*)CCDictionaryGetEntry(Local.scopedLabels, Entry);
                        
                        Local.defines = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeSmall, sizeof(CCString), sizeof(uint8_t), &(CCDictionaryCallbacks){
                            .getHash = CCStringHasherForDictionary,
                            .compareKeys = CCStringComparatorForDictionary
                        });
                        
                        Local.macros = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeSmall, sizeof(HKHubArchAssemblyMacroName), sizeof(HKHubArchAssemblyMacro), &(CCDictionaryCallbacks){
                            .getHash = (CCDictionaryKeyHasher)HKHubArchAssemblyMacroNameHasher,
                            .compareKeys = (CCComparator)HKHubArchAssemblyMacroNameComparator,
                            .valueDestructor = (CCDictionaryElementDestructor)HKHubArchAssemblyMacroDestructor
                        });
                        
                        Local.expand.symbols = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeSmall, sizeof(CCString), sizeof(HKHubArchAssemblySymbolExpansionRules), &(CCDictionaryCallbacks){
                            .getHash = CCStringHasherForDictionary,
                            .compareKeys = CCStringComparatorForDictionary
                        });
                        
                        CC_DICTIONARY_FOREACH_KEY_PTR(CCString, Key, Context->expand.symbols) CCDictionarySetValue(Local.expand.symbols, Key, CCDictionaryGetValue(Context->expand.symbols, Key));
                        CC_DICTIONARY_FOREACH_KEY_PTR(CCString, Key, Context->labels)
                        {
                            CCDictionaryEntry Entry = CCDictionaryEntryForKey(Local.labels, Key);
                            if (!CCDictionaryEntryIsInitialized(Local.labels, Entry))
                            {
                                CCDictionarySetEntry(Local.labels, Entry, CCDictionaryGetValue(Context->labels, Key));
                            }
                        }
                        CC_DICTIONARY_FOREACH_KEY_PTR(CCString, Key, Context->defines) CCDictionarySetValue(Local.defines, Key, CCDictionaryGetValue(Context->defines, Key));
                        CC_DICTIONARY_FOREACH_KEY_PTR(HKHubArchAssemblyMacroName, Key, Context->macros)
                        {
                            HKHubArchAssemblyMacro *SrcMacro = CCDictionaryGetValue(Context->macros, Key);
                            CCDictionarySetValue(Local.macros, Key, &(HKHubArchAssemblyMacro){
                                .ast = CCRetain(SrcMacro->ast),
                                .args = CCRetain(SrcMacro->args)
                            });
                        }
                        
                        CCOrderedCollection(HKHubArchAssemblyASTError) Errors = (Pass ? NULL : Context->errors);
                        
                        size_t Index = 0;
                        CC_COLLECTION_FOREACH_PTR(CCString, ArgName, Macro->args)
                        {
                            HKHubArchAssemblyASTNode *Operand = CCOrderedCollectionGetElementAtIndex(Command->childNodes, Index);
                            
                            uint8_t Result = 0;
                            if (HKHubArchAssemblyResolveInteger(Offset, &Result, Command, Operand, Errors, Context->labels, Context->defines, NULL, &Context->expand)) CCDictionarySetValue(Local.defines, ArgName, &Result);
                            else HKHubArchAssemblyErrorAddMessage(Errors, HKHubArchAssemblyErrorMessageOperandResolveInteger, Command, Operand, NULL);
                            
                            Index++;
                        }
                        
                        Offset = HKHubArchAssemblyRecursiveCompile(Offset, Binary, Macro->ast, &Local, Pass, Depth, Command);
                        
                        CCDictionaryDestroy(Local.defines);
                        CCDictionaryDestroy(Local.macros);
                        CCDictionaryDestroy(Local.expand.symbols);
                        
                        if (Local.saved.labels)
                        {
                            CC_DICTIONARY_FOREACH_KEY_PTR(CCString, Key, Local.saved.labels) CCDictionarySetValue(Context->labels, Key, CCDictionaryGetValue(Local.saved.labels, Key));
                            
                            CCDictionaryDestroy(Local.saved.labels);
                        }
                        
                        if (Local.saved.defines)
                        {
                            CC_DICTIONARY_FOREACH_KEY_PTR(CCString, Key, Local.saved.defines) CCDictionarySetValue(Context->defines, Key, CCDictionaryGetValue(Local.saved.defines, Key));
                            
                            CCDictionaryDestroy(Local.saved.defines);
                        }
                        
                        if (Local.saved.macros)
                        {
                            CC_DICTIONARY_FOREACH_KEY_PTR(HKHubArchAssemblyMacroName, Key, Local.saved.macros)
                            {
                                HKHubArchAssemblyMacro *SrcMacro = CCDictionaryGetValue(Local.saved.macros, Key);
                                CCDictionarySetValue(Context->macros, Key, &(HKHubArchAssemblyMacro){
                                    .ast = CCRetain(SrcMacro->ast),
                                    .args = CCRetain(SrcMacro->args)
                                });
                            }
                            
                            CCDictionaryDestroy(Local.saved.macros);
                        }
                        
                        Context->bits = Local.bits;
                    }
                    
                    else Offset = HKHubArchInstructionEncode(Offset, (Pass ? NULL : Binary->data), Command, (Pass ? NULL : Context->errors), Context->labels, Context->defines, &Context->expand);
                }
                break;
                
            case HKHubArchAssemblyASTTypeDirective:
                for (size_t Loop = 0; Loop < sizeof(Directives) / sizeof(typeof(*Directives)); Loop++) //TODO: make dictionary
                {
                    if (CCStringEqual(Directives[Loop].mnemonic, Command->string))
                    {
                        CCOrderedCollection(HKHubArchAssemblyASTError) Err = Context->errors;
                        if (Pass) Context->errors = NULL;
                        Offset = Directives[Loop].compile(Offset, (Pass ? NULL : Binary), Command, Context, Depth, &CC_COLLECTION_CURRENT_ENUMERATOR);
                        Context->errors = Err;
                        break;
                    }
                }
                break;
                
            case HKHubArchAssemblyASTTypeAST:
                Offset = HKHubArchAssemblyRecursiveCompile(Offset, Binary, Command->childNodes, Context, Pass, Depth, Command);
                break;
                
            default:
                HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageUnknownCommand, Command, NULL, NULL);
                break;
        }
        
        if (Offset > sizeof(Binary->data))
        {
            HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageSizeLimit, Command, NULL, NULL);
            Pass = 0;
            break;
        }
    }
    
    return Offset;
}

static size_t HKHubArchAssemblyRecursiveCompile(size_t Offset, HKHubArchBinary Binary, CCOrderedCollection(HKHubArchAssemblyASTNode) AST, HKHubArchAssemblyCompilationContext *Context, int Pass, size_t Depth, HKHubArchAssemblyASTNode *Command)
{
    if (++Depth < HK_HUB_ARCH_ASSEMBLY_COMPILE_DEPTH_MAX) Offset = HKHubArchAssemblyCompile(Offset, Binary, AST, Context, Pass, Depth);
    else
    {
        HKHubArchAssemblyErrorAddMessage(Context->errors, HKHubArchAssemblyErrorMessageCompileDepthLimit, Command, NULL, NULL);
        *Context->stop = TRUE;
    }
    
    return Offset;
}

static void HKHubArchAssemblyASTErrorDestructor(void *Container, HKHubArchAssemblyASTError *Error)
{
    if (Error->message) CCStringDestroy(Error->message);
}

HKHubArchBinary HKHubArchAssemblyCreateBinary(CCAllocatorType Allocator, CCOrderedCollection(HKHubArchAssemblyASTNode) AST, CCOrderedCollection(HKHubArchAssemblyASTError) *Errors)
{
    CCAssertLog(AST, "AST must not be null");
    
    HKHubArchBinary Binary = HKHubArchBinaryCreate(Allocator);
    
    HKHubArchAssemblyCompilationContext Global = {
        .labels = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeSmall, sizeof(CCString), sizeof(uint8_t), &(CCDictionaryCallbacks){
            .getHash = CCStringHasherForDictionary,
            .compareKeys = CCStringComparatorForDictionary
        }),
        .scopedLabels = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeSmall, sizeof(CCOrderedCollection(HKHubArchAssemblyASTNode)), sizeof(CCDictionary(CCString, uint8_t)), &(CCDictionaryCallbacks){
            .valueDestructor = CCDictionaryDestructorForDictionary
        }),
        .errors = CCCollectionCreate(CC_STD_ALLOCATOR, CCCollectionHintOrdered, sizeof(HKHubArchAssemblyASTError), (CCCollectionElementDestructor)HKHubArchAssemblyASTErrorDestructor),
        .ifBlocks = CCArrayCreate(CC_STD_ALLOCATOR, sizeof(HKHubArchAssemblyIfBlock), 16),
        .saved = { NULL, NULL, NULL },
        .stop = &(_Bool){ FALSE }
    };
    
    Global.hardErrors = Global.errors;
    
    for (int Pass = 1; (Pass >= 0) && (!*Global.stop); Pass--)
    {
        Global.defines = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeSmall, sizeof(CCString), sizeof(uint8_t), &(CCDictionaryCallbacks){
            .getHash = CCStringHasherForDictionary,
            .compareKeys = CCStringComparatorForDictionary
        });
        
        Global.macros = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeSmall, sizeof(HKHubArchAssemblyMacroName), sizeof(HKHubArchAssemblyMacro), &(CCDictionaryCallbacks){
            .getHash = (CCDictionaryKeyHasher)HKHubArchAssemblyMacroNameHasher,
            .compareKeys = (CCComparator)HKHubArchAssemblyMacroNameComparator,
            .valueDestructor = (CCDictionaryElementDestructor)HKHubArchAssemblyMacroDestructor
        });
        
        Global.expand.symbols = CCDictionaryCreate(CC_STD_ALLOCATOR, CCDictionaryHintSizeSmall, sizeof(CCString), sizeof(HKHubArchAssemblySymbolExpansionRules), &(CCDictionaryCallbacks){
            .getHash = CCStringHasherForDictionary,
            .compareKeys = CCStringComparatorForDictionary
        });
        Global.expand.defaults = (HKHubArchAssemblySymbolExpansionRules){ .macro = TRUE, .define = TRUE, .label = TRUE };
        
        Global.bits.count = 0;
        Global.bits.offset = 0;
        Global.counter = &(size_t){ 0 };
        
        HKHubArchAssemblyCompile(0, Binary, AST, &Global, Pass, 0);
        
        CCDictionaryDestroy(Global.defines);
        CCDictionaryDestroy(Global.macros);
        CCDictionaryDestroy(Global.expand.symbols);
    }
    
    if (Global.saved.labels) CCDictionaryDestroy(Global.saved.labels);
    if (Global.saved.defines) CCDictionaryDestroy(Global.saved.defines);
    if (Global.saved.macros) CCDictionaryDestroy(Global.saved.macros);
    
    CCDictionaryDestroy(Global.scopedLabels);
    CCDictionaryDestroy(Global.labels);
    
    if (CCCollectionGetCount(Global.errors))
    {
        HKHubArchBinaryDestroy(Binary);
        Binary = NULL;
        
        if (Errors) *Errors = Global.errors;
        else CCCollectionDestroy(Global.errors);
    }
    
    else CCCollectionDestroy(Global.errors);
    
    return Binary;
}

static void HKHubArchAssemblyPrintASTNodes(CCOrderedCollection(HKHubArchAssemblyASTNode) AST)
{
    if (!AST) return;
    
    size_t Line = 0;
    _Bool First = TRUE;
    CC_COLLECTION_FOREACH_PTR(HKHubArchAssemblyASTNode, Node, AST)
    {
        if (Line != Node->line)
        {
            if (!First) printf("\n");
            
            Line = Node->line;
            First = TRUE;
        }
        
        static const char *Types[] = {
            "source",
            "ast",
            "unknown",
            "instruction",
            "directive",
            "label",
            "string",
            "integer",
            "register",
            "memory",
            "expression",
            "operand",
            "symbol",
            "random",
            "plus",
            "minus",
            "multiply",
            "divide",
            "modulo",
            "not",
            "ones_complement",
            "shift_left",
            "shift_right",
            "bitwise_and",
            "bitwise_or",
            "bitwise_xor",
            "logical_and",
            "logical_or",
            "equal",
            "not_equal",
            "less_than",
            "less_than_or_equal",
            "greater_than",
            "greater_than_or_equal",
            "offset"
        };
        
        _Static_assert(sizeof(Types) / sizeof(typeof(*Types)) == HKHubArchAssemblyASTTypeMax, "AST types have changed");
        
        if (!First) printf(", ");
        
        printf("%s", Types[Node->type]);
        
        if (Node->string)
        {
            CC_STRING_TEMP_BUFFER(Buffer, Node->string)
            {
                printf("<%s>", Buffer);
            }
        }
        
        printf("(");
        
        HKHubArchAssemblyPrintASTNodes(Node->childNodes);
        
        printf(")");
        
        First = FALSE;
    }
}

void HKHubArchAssemblyPrintAST(CCOrderedCollection(HKHubArchAssemblyASTNode) AST)
{
    HKHubArchAssemblyPrintASTNodes(AST);
    printf("\n");
}

void HKHubArchAssemblyPrintError(CCOrderedCollection(HKHubArchAssemblyASTError) Errors)
{
    if (!Errors) return;
    
    CC_COLLECTION_FOREACH_PTR(HKHubArchAssemblyASTError, Error, Errors)
    {
        CCString Focus = (Error->value ? Error->value->string : (Error->operand ? Error->operand->string : Error->command->string));
        CC_LOG_DEBUG_CUSTOM("Line %zu:%S: %S", Error->command->line, Error->message, Focus);
    }
}
