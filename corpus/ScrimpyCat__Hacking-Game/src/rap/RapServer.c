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

#include "RapServer.h"
#include <sys/socket.h>
#include <netinet/in.h>

#define HK_RAP_SERVER_PORT 9999

typedef enum {
    HKRapServerOperationOpen = 1,
    HKRapServerOperationRead,
    HKRapServerOperationWrite,
    HKRapServerOperationSeek,
    HKRapServerOperationClose,
    HKRapServerOperationSystem,
    HKRapServerOperationCmd,
    
    HKRapServerOperationReply = 0x80
} HKRapServerOperation;

typedef enum {
    HKRapServerSeekSet = 0,
    HKRapServerSeekCur,
    HKRapServerSeekEnd
} HKRapServerSeek;

typedef struct {
    uint8_t op; // HKRapServerOperation
    union {
        struct {
            uint8_t rw;
            uint8_t length;
            uint8_t filename[];
        } CC_PACKED open;
        struct {
            uint32_t length;
        } CC_PACKED read;
        struct {
            uint32_t length;
            uint8_t data[];
        } CC_PACKED write;
        struct {
            uint8_t flag; // HKRapServerSeek
            uint64_t offset;
        } CC_PACKED seek;
        struct {
            uint32_t fd;
        } CC_PACKED close;
        struct {
            uint32_t length;
            uint8_t command[];
        } CC_PACKED system;
        struct {
            uint32_t length;
            uint8_t command[];
        } CC_PACKED cmd;
    };
} CC_PACKED HKRapServerDataRequest;

typedef struct {
    uint8_t op; // HKRapServerOperation
    union {
        struct {
            uint32_t fd;
        } CC_PACKED open;
        struct {
            uint32_t length;
            uint8_t data[];
        } CC_PACKED read;
        struct {
            uint32_t length;
        } CC_PACKED write;
        struct {
            uint64_t offset;
        } CC_PACKED seek;
        struct {
            uint32_t ret;
        } CC_PACKED close;
        struct {
            uint32_t length;
            uint8_t result[];
        } CC_PACKED system;
        struct {
            uint32_t length;
            uint8_t result[];
        } CC_PACKED cmd;
    };
} CC_PACKED HKRapServerDataResponse;

#define HK_RAP_SERVER_DATA_OP_SIZE sizeof(uint8_t)

#define HK_RAP_SERVER_DATA_REQUEST_OPEN_SIZE(length)    (HK_RAP_SERVER_DATA_OP_SIZE + sizeof(typeof(((HKRapServerDataRequest*)NULL)->open)) + length)
#define HK_RAP_SERVER_DATA_REQUEST_READ_SIZE            (HK_RAP_SERVER_DATA_OP_SIZE + sizeof(typeof(((HKRapServerDataRequest*)NULL)->read)))
#define HK_RAP_SERVER_DATA_REQUEST_WRITE_SIZE(length)   (HK_RAP_SERVER_DATA_OP_SIZE + sizeof(typeof(((HKRapServerDataRequest*)NULL)->write)) + length)
#define HK_RAP_SERVER_DATA_REQUEST_SEEK_SIZE            (HK_RAP_SERVER_DATA_OP_SIZE + sizeof(typeof(((HKRapServerDataRequest*)NULL)->seek)))
#define HK_RAP_SERVER_DATA_REQUEST_CLOSE_SIZE           (HK_RAP_SERVER_DATA_OP_SIZE + sizeof(typeof(((HKRapServerDataRequest*)NULL)->close)))
#define HK_RAP_SERVER_DATA_REQUEST_SYSTEM_SIZE(length)  (HK_RAP_SERVER_DATA_OP_SIZE + sizeof(typeof(((HKRapServerDataRequest*)NULL)->system)) + length)
#define HK_RAP_SERVER_DATA_REQUEST_CMD_SIZE(length)     (HK_RAP_SERVER_DATA_OP_SIZE + sizeof(typeof(((HKRapServerDataRequest*)NULL)->cmd)) + length)

#define HK_RAP_SERVER_DATA_RESPONSE_OPEN_SIZE           (HK_RAP_SERVER_DATA_OP_SIZE + sizeof(typeof(((HKRapServerDataResponse*)NULL)->open)))
#define HK_RAP_SERVER_DATA_RESPONSE_READ_SIZE(length)   (HK_RAP_SERVER_DATA_OP_SIZE + sizeof(typeof(((HKRapServerDataResponse*)NULL)->read)) + length)
#define HK_RAP_SERVER_DATA_RESPONSE_WRITE_SIZE          (HK_RAP_SERVER_DATA_OP_SIZE + sizeof(typeof(((HKRapServerDataResponse*)NULL)->write)))
#define HK_RAP_SERVER_DATA_RESPONSE_SEEK_SIZE           (HK_RAP_SERVER_DATA_OP_SIZE + sizeof(typeof(((HKRapServerDataResponse*)NULL)->seek)))
#define HK_RAP_SERVER_DATA_RESPONSE_CLOSE_SIZE          (HK_RAP_SERVER_DATA_OP_SIZE + sizeof(typeof(((HKRapServerDataResponse*)NULL)->close)))
#define HK_RAP_SERVER_DATA_RESPONSE_SYSTEM_SIZE(length) (HK_RAP_SERVER_DATA_OP_SIZE + sizeof(typeof(((HKRapServerDataResponse*)NULL)->system)) + length)
#define HK_RAP_SERVER_DATA_RESPONSE_CMD_SIZE(length)    (HK_RAP_SERVER_DATA_OP_SIZE + sizeof(typeof(((HKRapServerDataResponse*)NULL)->cmd)) + length)

static ssize_t RapServerRecv(int Connection, void *Buffer, size_t Size)
{
    ssize_t Received = 0, Ret = 0;
    for (_Bool Complete = FALSE; (!Complete) && (Received < Size) && ((Ret = recv(Connection, Buffer + Received, Size - Received, 0)) > 0); )
    {
        Received += Ret;
        
        switch (((HKRapServerDataRequest*)Buffer)->op & ~HKRapServerOperationReply)
        {
            case HKRapServerOperationOpen:
                Complete = (Received >= HK_RAP_SERVER_DATA_REQUEST_OPEN_SIZE(0)) && (Received == HK_RAP_SERVER_DATA_REQUEST_OPEN_SIZE(((HKRapServerDataRequest*)Buffer)->open.length));
                break;
                
            case HKRapServerOperationRead:
                Complete = (Received >= HK_RAP_SERVER_DATA_REQUEST_READ_SIZE);
                break;
                
            case HKRapServerOperationWrite:
                Complete = (Received >= HK_RAP_SERVER_DATA_REQUEST_WRITE_SIZE(0)) && (Received == HK_RAP_SERVER_DATA_REQUEST_WRITE_SIZE(ntohl(((HKRapServerDataRequest*)Buffer)->write.length)));
                break;
                
            case HKRapServerOperationSeek:
                Complete = (Received >= HK_RAP_SERVER_DATA_REQUEST_SEEK_SIZE);
                break;
                
            case HKRapServerOperationClose:
                Complete = (Received >= HK_RAP_SERVER_DATA_REQUEST_CLOSE_SIZE);
                break;
                
            case HKRapServerOperationSystem:
                Complete = (Received >= HK_RAP_SERVER_DATA_REQUEST_SYSTEM_SIZE(0)) && (Received == HK_RAP_SERVER_DATA_REQUEST_SYSTEM_SIZE(ntohl(((HKRapServerDataRequest*)Buffer)->system.length)));
                break;
                
            case HKRapServerOperationCmd:
                Complete = (Received >= HK_RAP_SERVER_DATA_REQUEST_CMD_SIZE(0)) && (Received == HK_RAP_SERVER_DATA_REQUEST_CMD_SIZE(ntohl(((HKRapServerDataRequest*)Buffer)->cmd.length)));
                break;
        }
    }
    
    return Ret == -1 ? -1 : Received;
}

static ssize_t RapServerSend(int Connection, void *Buffer, size_t Size)
{
    ssize_t Sent = 0, Ret = 0;
    for (_Bool Complete = FALSE; (!Complete) && ((Ret = send(Connection, Buffer + Sent, Size - Sent, 0)) <= Size) && (Ret != -1); )
    {
        Sent += Ret;
        
        switch (((HKRapServerDataResponse*)Buffer)->op & ~HKRapServerOperationReply)
        {
            case HKRapServerOperationOpen:
                Complete = (Sent >= HK_RAP_SERVER_DATA_RESPONSE_OPEN_SIZE);
                break;
                
            case HKRapServerOperationRead:
                Complete = (Sent >= HK_RAP_SERVER_DATA_RESPONSE_READ_SIZE(0)) && (Sent == HK_RAP_SERVER_DATA_RESPONSE_READ_SIZE(ntohl(((HKRapServerDataResponse*)Buffer)->read.length)));
                break;
                
            case HKRapServerOperationWrite:
                Complete = (Sent >= HK_RAP_SERVER_DATA_RESPONSE_WRITE_SIZE);
                break;
                
            case HKRapServerOperationSeek:
                Complete = (Sent >= HK_RAP_SERVER_DATA_RESPONSE_SEEK_SIZE);
                break;
                
            case HKRapServerOperationClose:
                Complete = (Sent >= HK_RAP_SERVER_DATA_RESPONSE_CLOSE_SIZE);
                break;
                
            case HKRapServerOperationSystem:
                Complete = (Sent >= HK_RAP_SERVER_DATA_RESPONSE_SYSTEM_SIZE(0)) && (Sent == HK_RAP_SERVER_DATA_RESPONSE_SYSTEM_SIZE(ntohl(((HKRapServerDataResponse*)Buffer)->system.length)));
                break;
                
            case HKRapServerOperationCmd:
                Complete = (Sent >= HK_RAP_SERVER_DATA_RESPONSE_CMD_SIZE(0)) && (Sent == HK_RAP_SERVER_DATA_RESPONSE_CMD_SIZE(ntohl(((HKRapServerDataResponse*)Buffer)->cmd.length)));
                break;
        }
    }

    return Ret == -1 ? -1 : Sent;
}

static struct {
    uint8_t pc;
    uint8_t memory[256];
} DataPool[3];
static CCConcurrentIndexBuffer DataIndex = NULL;

#define HK_RAP_SERVER_BINARY_SIZE (sizeof(DataPool->memory) / sizeof(typeof(*DataPool->memory)))

static int RapServerLoop(void *Arg)
{
    int SockFd = socket(AF_INET, SOCK_STREAM, 0);
    if (SockFd == -1)
    {
        CC_LOG_ERROR("Failed to create RAP server due to socket creation failure");
        return EXIT_FAILURE;
    }
    
    if (setsockopt(SockFd, SOL_SOCKET, SO_REUSEADDR, &(int){ 1 }, sizeof(int)) == -1)
    {
        
        CC_LOG_ERROR("Failed to create RAP server due to setting socket option failure");
        close(SockFd);
        return EXIT_FAILURE;
    }
    
    if (setsockopt(SockFd, SOL_SOCKET, SO_REUSEPORT, &(int){ 1 }, sizeof(int)) == -1)
    {
        
        CC_LOG_ERROR("Failed to create RAP server due to setting socket option failure");
        close(SockFd);
        return EXIT_FAILURE;
    }
    
    struct sockaddr_in Address = {
        .sin_family = AF_INET,
        .sin_addr = {
            .s_addr = INADDR_ANY
        },
        .sin_port = htons(HK_RAP_SERVER_PORT)
    };
    
    if (bind(SockFd, (struct sockaddr*)&Address, sizeof(Address)) == -1)
    {
        CC_LOG_ERROR("Failed to create RAP server due to address binding failure");
        close(SockFd);
        return EXIT_FAILURE;
    }
    
    if (listen(SockFd, 32) == -1)
    {
        CC_LOG_ERROR("Failed to listen for connections to RAP server");
        close(SockFd);
        return EXIT_FAILURE;
    }
    
    uint8_t Buffer[sizeof(HKRapServerDataResponse) + HK_RAP_SERVER_BINARY_SIZE];
    size_t Index = 0;
    uint64_t Offset = 0;
    for ( ; ; )
    {
        int Connection = accept(SockFd, (struct sockaddr*)&Address, &(socklen_t){ sizeof(Address) });
        if (Connection == -1) CC_LOG_ERROR("Failed to accept incoming connection to RAP server");
        
        for ( ; Connection != -1; )
        {
            ssize_t Size = RapServerRecv(Connection, Buffer, sizeof(Buffer) / sizeof(typeof(*Buffer)));
            if (Size > 0)
            {
                switch (((HKRapServerDataRequest*)Buffer)->op)
                {
                    case HKRapServerOperationOpen:
                    {
                        uint32_t Fd = 1;
                        ((HKRapServerDataResponse*)Buffer)->op |= HKRapServerOperationReply;
                        ((HKRapServerDataResponse*)Buffer)->open.fd = htonl(Fd);
                        Size = RapServerSend(Connection, Buffer, HK_RAP_SERVER_DATA_RESPONSE_OPEN_SIZE);
                        if (Size == -1) perror("reply open");
                        break;
                    }
                        
                    case HKRapServerOperationRead:
                    {
                        size_t NewIndex;
                        if (CCConcurrentIndexBufferReadAcquire(DataIndex, &NewIndex))
                        {
                            if (Index) CCConcurrentIndexBufferDiscard(DataIndex, Index);
                            
                            Index = NewIndex + 1;
                        }
                        
                        uint32_t Length = 0;
                        ((HKRapServerDataResponse*)Buffer)->op |= HKRapServerOperationReply;
                        
                        if (Index)
                        {
                            Length = ntohl(((HKRapServerDataRequest*)Buffer)->read.length);
                            if (Length > HK_RAP_SERVER_BINARY_SIZE) Length = HK_RAP_SERVER_BINARY_SIZE;
                            
                            if (Offset < HK_RAP_SERVER_BINARY_SIZE)
                            {
                                Length -= Offset;
                                memcpy(((HKRapServerDataResponse*)Buffer)->read.data, DataPool[Index - 1].memory + Offset, Length);
                            }
                            
                            else Length = 0;
                        }
                        
                        ((HKRapServerDataResponse*)Buffer)->read.length = htonl(Length);
                        
                        Size = RapServerSend(Connection, Buffer, HK_RAP_SERVER_DATA_RESPONSE_READ_SIZE(Length));
                        if (Size == -1) perror("reply read");
                        break;
                    }
                        
                    case HKRapServerOperationWrite:
                    {
                        uint32_t Length = 0;
                        ((HKRapServerDataResponse*)Buffer)->op |= HKRapServerOperationReply;
                        ((HKRapServerDataResponse*)Buffer)->write.length = htonl(Length);
                        Size = RapServerSend(Connection, Buffer, HK_RAP_SERVER_DATA_RESPONSE_WRITE_SIZE);
                        if (Size == -1) perror("reply write");
                        break;
                    }
                        
                    case HKRapServerOperationSeek:
                    {
                        ((HKRapServerDataResponse*)Buffer)->op |= HKRapServerOperationReply;
                        
                        if (Index)
                        {
                            switch (((HKRapServerDataRequest*)Buffer)->seek.flag)
                            {
                                case HKRapServerSeekSet:
                                    Offset = ntohll(((HKRapServerDataRequest*)Buffer)->seek.offset);
                                    break;
                                    
                                case HKRapServerSeekCur:
                                    Offset += ntohll(((HKRapServerDataRequest*)Buffer)->seek.offset);
                                    break;
                                    
                                case HKRapServerSeekEnd:
                                    Offset = HK_RAP_SERVER_BINARY_SIZE + ntohll(((HKRapServerDataRequest*)Buffer)->seek.offset);
                                    break;
                            }
                        }
                        
                        else Offset = 0 + ntohll(((HKRapServerDataRequest*)Buffer)->seek.offset);
                        
                        ((HKRapServerDataResponse*)Buffer)->seek.offset = htonll(Offset);
                        
                        Size = RapServerSend(Connection, Buffer, HK_RAP_SERVER_DATA_RESPONSE_SEEK_SIZE);
                        if (Size == -1) perror("reply seek");
                        break;
                    }
                        
                    case HKRapServerOperationClose:
                    {
                        uint32_t Ret = 0;
                        ((HKRapServerDataResponse*)Buffer)->op |= HKRapServerOperationReply;
                        ((HKRapServerDataResponse*)Buffer)->close.ret = htonl(Ret);
                        Size = RapServerSend(Connection, Buffer, HK_RAP_SERVER_DATA_RESPONSE_CLOSE_SIZE);
                        if (Size == -1) perror("reply close");
                        
                        close(Connection); Connection = -1;
                        break;
                    }
                        
                    case HKRapServerOperationSystem:
                    {
                        uint32_t Length = 0;
                        ((HKRapServerDataResponse*)Buffer)->op |= HKRapServerOperationReply;
                        ((HKRapServerDataResponse*)Buffer)->system.length = htonl(Length);
                        memcpy(((HKRapServerDataResponse*)Buffer)->system.result, (uint8_t[]){ 0 }, Length);
                        Size = RapServerSend(Connection, Buffer, HK_RAP_SERVER_DATA_RESPONSE_SYSTEM_SIZE(Length));
                        if (Size == -1) perror("reply system");
                        break;
                    }
                        
                    case HKRapServerOperationCmd:
                    {
                        uint32_t Length = 0;
                        ((HKRapServerDataResponse*)Buffer)->op |= HKRapServerOperationReply;
                        
                        CCString Cmd = CCStringCreateWithSize(CC_STD_ALLOCATOR, (CCStringHint)CCStringEncodingASCII, (char*)((HKRapServerDataRequest*)Buffer)->cmd.command, ntohl(((HKRapServerDataRequest*)Buffer)->cmd.length));
                        
                        if (CCStringEqual(Cmd, CC_STRING("drp")))
                        {
                            FSPath Path = FSPathCopy(HKAssetPath);
                            FSPathAppendComponent(Path, FSPathComponentCreate(FSPathComponentTypeDirectory, "radare"));
                            FSPathAppendComponent(Path, FSPathComponentCreate(FSPathComponentTypeFile, "register-profile"));
                            
                            FSHandle Handle;
                            if (FSHandleOpen(Path, FSHandleTypeRead, &Handle) == FSOperationSuccess)
                            {
                                size_t Size = FSManagerGetSize(Path);
                                char *Profile;
                                CC_SAFE_Malloc(Profile, sizeof(char) * (Size + 1));
                                
                                FSHandleRead(Handle, &Size, Profile, FSBehaviourDefault);
                                Profile[Size] = 0;
                                
                                FSHandleClose(Handle);
                                
                                Length = (uint32_t)Size + 1;
                                if (Length < HK_RAP_SERVER_BINARY_SIZE)
                                {
                                    memcpy(((HKRapServerDataResponse*)Buffer)->cmd.result, Profile, Length);
                                }
                                
                                else
                                {
                                    CC_LOG_ERROR("Path to register profile (%s) exceeds allowed size for RAP server CMD response", Profile);
                                    Length = 0;
                                }
                                
                                CC_SAFE_Free(Profile);
                            }
                            
                            FSPathDestroy(Path);
                        }
                        
                        CCStringDestroy(Cmd);
                        
                        ((HKRapServerDataResponse*)Buffer)->cmd.length = htonl(Length);
                        Size = RapServerSend(Connection, Buffer, HK_RAP_SERVER_DATA_RESPONSE_CMD_SIZE(Length));
                        if (Size == -1) perror("reply cmd");
                        break;
                    }
                        
                    case HKRapServerOperationCmd | HKRapServerOperationReply:
                    {
                        uint32_t Length = 0;
                        ((HKRapServerDataResponse*)Buffer)->op |= HKRapServerOperationReply;
                        
                        ((HKRapServerDataResponse*)Buffer)->cmd.length = htonl(Length);
                        Size = RapServerSend(Connection, Buffer, HK_RAP_SERVER_DATA_RESPONSE_CMD_SIZE(Length));
                        if (Size == -1) perror("reply cmd");
                        break;
                    }
                }
            }
            
            else if (Size == -1) perror("read");
            
            if (Size <= 0) break;
        }
        
        if (Connection != -1) close(Connection);
    }
    
    return EXIT_SUCCESS;
}

static thrd_t RapServerThread;
void HKRapServerStart(void)
{
    DataIndex = CCConcurrentIndexBufferCreate(CC_STD_ALLOCATOR, sizeof(DataPool) / sizeof(typeof(*DataPool)));
    
    int err;
    if ((err = thrd_create(&RapServerThread, (thrd_start_t)RapServerLoop, NULL)) != thrd_success)
    {
        CC_LOG_ERROR("Failed to create rap server thread (%d)", err);
        return;
    }
}

void HKRapServerUpdate(HKHubArchProcessor Processor)
{
    const size_t Index = CCConcurrentIndexBufferWriteAcquire(DataIndex);
    
    DataPool[Index].pc = Processor->state.pc;
    memcpy(DataPool[Index].memory, Processor->memory, sizeof(Processor->memory) / sizeof(typeof(*Processor->memory)));
    
    CCConcurrentIndexBufferStage(DataIndex, Index);
}
