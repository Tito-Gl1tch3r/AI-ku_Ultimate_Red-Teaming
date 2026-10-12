#include "ebpf_ntos_hooks.h"
#include "fileevent_ebpf_ext_event.h"
#include "fileevent_ebpf_ext_program_info.h"

#include <errno.h>

#define MAX_PATH 260

 // Define a dynamic event buffer for optimizing the event data copy.
static uint8_t* _event_buffer = NULL; ///< Event buffer for copying the event data.
static size_t _event_buffer_size =
4096; ///< Initial size of the event buffer, which will be dynamically resized as needed.
EX_PUSH_LOCK _ebpf_fileevent_push_event_lock;

static ebpf_result_t
_ebpf_fileevent_context_create(
    _In_reads_bytes_opt_(data_size_in) const uint8_t* data_in,
    size_t data_size_in,
    _In_reads_bytes_opt_(context_size_in) const uint8_t* context_in,
    size_t context_size_in,
    _Outptr_ void** context);

static void
_ebpf_fileevent_context_destroy(
    _In_opt_ void* context,
    _Out_writes_bytes_to_(*data_size_out, *data_size_out) uint8_t* data_out,
    _Inout_ size_t* data_size_out,
    _Out_writes_bytes_to_(*context_size_out, *context_size_out) uint8_t* context_out,
    _Inout_ size_t* context_size_out);

void
_ebpf_fileevent_push_event(_In_ fileevent_md_t* fileevent_event);

static const void* _ebpf_fileevent_helper_functions[] = {(void*)&_ebpf_fileevent_push_event};

#define Log(format, ...) DbgPrintEx(DPFLTR_DEFAULT_ID, DPFLTR_ERROR_LEVEL, "[event]" format "\n", ##__VA_ARGS__)


static ebpf_helper_function_addresses_t _ebpf_fileevent_helper_function_address_table = {
    .header = {EBPF_HELPER_FUNCTION_ADDRESSES_CURRENT_VERSION, EBPF_HELPER_FUNCTION_ADDRESSES_CURRENT_VERSION_SIZE},
    .helper_function_count = EBPF_COUNT_OF(_ebpf_fileevent_helper_functions),
    .helper_function_address = (uint64_t*)_ebpf_fileevent_helper_functions,
};

//
// File Event Program Information NPI Provider.
//
static ebpf_program_data_t _ebpf_fileevent_program_data = {
    .header = EBPF_PROGRAM_DATA_HEADER,
    .program_info = &_ebpf_fileevent_program_info,
    .program_type_specific_helper_function_addresses = &_ebpf_fileevent_helper_function_address_table,
    .context_create = _ebpf_fileevent_context_create,
    .context_destroy = _ebpf_fileevent_context_destroy,
    .required_irql = PASSIVE_LEVEL,
    .capabilities = {.supports_context_header = true},
};

static ebpf_extension_data_t _ebpf_fileevent_program_info_provider_data = {
    .header = {EBPF_EXTENSION_NPI_PROVIDER_VERSION, sizeof(_ebpf_fileevent_program_data)},
    .data = &_ebpf_fileevent_program_data};

NPI_MODULEID DECLSPEC_SELECTANY _ebpf_fileevent_program_info_provider_moduleid = {sizeof(NPI_MODULEID), MIT_GUID, {0}};

static ebpf_extension_program_info_provider_t* _ebpf_fileevent_program_info_provider_context = NULL;

//
// Process Hook NPI Provider.
//
ebpf_attach_provider_data_t _ntos_ebpf_fileevent_hook_provider_data = {
    .header = {EBPF_ATTACH_PROVIDER_DATA_CURRENT_VERSION, EBPF_ATTACH_PROVIDER_DATA_CURRENT_VERSION_SIZE},
    .supported_program_type = EBPF_PROGRAM_TYPE_FILEEVENT_GUID,
    .bpf_attach_type = (bpf_attach_type_t)BPF_ATTACH_TYPE_FILEEVENT,
};

NPI_MODULEID DECLSPEC_SELECTANY _ebpf_fileevent_hook_provider_moduleid = {sizeof(NPI_MODULEID), MIT_GUID, {0}};

static ebpf_extension_hook_provider_t* _ebpf_fileevent_hook_provider_context = NULL;

EX_PUSH_LOCK _ebpf_fileevent_hook_provider_lock;
bool _ebpf_fileevent_hook_provider_registered = FALSE;
uint64_t _ebpf_fileevent_hook_provider_registration_count = 0;


// file system global variables
PFLT_FILTER gFilterHandle;
ULONG_PTR OperationStatusCtx = 1;

NTSTATUS
FilterInstanceSetup(
    _In_ PCFLT_RELATED_OBJECTS FltObjects,
    _In_ FLT_INSTANCE_SETUP_FLAGS Flags,
    _In_ DEVICE_TYPE VolumeDeviceType,
    _In_ FLT_FILESYSTEM_TYPE VolumeFilesystemType);

NTSTATUS
FilterInstanceQueryTeardown(
    _In_ PCFLT_RELATED_OBJECTS FltObjects,
    _In_ FLT_INSTANCE_QUERY_TEARDOWN_FLAGS Flags);

VOID
FilterInstanceTeardownStart(
    _In_ PCFLT_RELATED_OBJECTS FltObjects,
    _In_ FLT_INSTANCE_TEARDOWN_FLAGS Flags);

VOID
FilterInstanceTeardownComplete(
    _In_ PCFLT_RELATED_OBJECTS FltObjects,
    _In_ FLT_INSTANCE_TEARDOWN_FLAGS Flags);

NTSTATUS
UnloadCallback(_In_ FLT_FILTER_UNLOAD_FLAGS Flags);


#ifdef ALLOC_PRAGMA
#pragma alloc_text(PAGE, UnloadCallback)
#pragma alloc_text(PAGE, FilterInstanceQueryTeardown)
#pragma alloc_text(PAGE, FilterInstanceSetup)
#pragma alloc_text(PAGE, FilterInstanceTeardownStart)
#pragma alloc_text(PAGE, FilterInstanceTeardownComplete)
#endif

NTSTATUS
FilterInstanceSetup(
    _In_ PCFLT_RELATED_OBJECTS FltObjects,
    _In_ FLT_INSTANCE_SETUP_FLAGS Flags,
    _In_ DEVICE_TYPE VolumeDeviceType,
    _In_ FLT_FILESYSTEM_TYPE VolumeFilesystemType)
{
    UNREFERENCED_PARAMETER(FltObjects);
    UNREFERENCED_PARAMETER(Flags);
    UNREFERENCED_PARAMETER(VolumeDeviceType);
    UNREFERENCED_PARAMETER(VolumeFilesystemType);

    PAGED_CODE();

    return STATUS_SUCCESS;
}

NTSTATUS
FilterInstanceQueryTeardown(
    _In_ PCFLT_RELATED_OBJECTS FltObjects,
    _In_ FLT_INSTANCE_QUERY_TEARDOWN_FLAGS Flags
)
{
    UNREFERENCED_PARAMETER(FltObjects);
    UNREFERENCED_PARAMETER(Flags);

    PAGED_CODE();

    return STATUS_SUCCESS;
}

VOID
FilterInstanceTeardownStart(
    _In_ PCFLT_RELATED_OBJECTS FltObjects,
    _In_ FLT_INSTANCE_TEARDOWN_FLAGS Flags
)
{
    UNREFERENCED_PARAMETER(FltObjects);
    UNREFERENCED_PARAMETER(Flags);

    PAGED_CODE();
}

VOID
FilterInstanceTeardownComplete (
    _In_ PCFLT_RELATED_OBJECTS FltObjects,
    _In_ FLT_INSTANCE_TEARDOWN_FLAGS Flags
    )
{
    UNREFERENCED_PARAMETER( FltObjects );
    UNREFERENCED_PARAMETER( Flags );

    PAGED_CODE();
}

BOOLEAN
DoRequestOperationStatus(
    _In_ PFLT_CALLBACK_DATA Data
)
{
    PFLT_IO_PARAMETER_BLOCK iopb = Data->Iopb;
    return (BOOLEAN)

        //
        //  Check for oplock operations
        //

        (((iopb->MajorFunction == IRP_MJ_FILE_SYSTEM_CONTROL) &&
          ((iopb->Parameters.FileSystemControl.Common.FsControlCode == FSCTL_REQUEST_FILTER_OPLOCK) ||
           (iopb->Parameters.FileSystemControl.Common.FsControlCode == FSCTL_REQUEST_BATCH_OPLOCK) ||
           (iopb->Parameters.FileSystemControl.Common.FsControlCode == FSCTL_REQUEST_OPLOCK_LEVEL_1) ||
           (iopb->Parameters.FileSystemControl.Common.FsControlCode == FSCTL_REQUEST_OPLOCK_LEVEL_2)))

         ||

         //
         //    Check for directy change notification
         //

         ((iopb->MajorFunction == IRP_MJ_DIRECTORY_CONTROL) &&
          (iopb->MinorFunction == IRP_MN_NOTIFY_CHANGE_DIRECTORY))


            ||

         //
         //    Check for READ or WRITE activity
         //

         (
             (iopb->MajorFunction == IRP_MJ_CREATE) || (iopb->MajorFunction == IRP_MJ_CLOSE) ||
             (iopb->MajorFunction == IRP_MJ_READ) || (iopb->MajorFunction == IRP_MJ_WRITE) ||
             (iopb->MajorFunction == IRP_MJ_SET_INFORMATION) || (iopb->MajorFunction == IRP_MJ_FLUSH_BUFFERS) ||
          (iopb->MajorFunction == IRP_MJ_DIRECTORY_CONTROL) || (iopb->MajorFunction == IRP_MJ_FILE_SYSTEM_CONTROL) ||
             (iopb->MajorFunction == IRP_MJ_CLEANUP)
         )
         );
}


VOID
OperationStatusCallback(
    _In_ PCFLT_RELATED_OBJECTS FltObjects,
    _In_ PFLT_IO_PARAMETER_BLOCK ParameterSnapshot,
    _In_ NTSTATUS OperationStatus,
    _In_ PVOID RequesterContext)
{
    UNREFERENCED_PARAMETER(OperationStatus);
    //UNREFERENCED_PARAMETER(RequesterContext);

    EBPF_EXT_LOG_ENTRY();

    PFILE_OBJECT fileObject = ParameterSnapshot->TargetFileObject;
    NTSTATUS status;
    FILE_BASIC_INFORMATION basicInfo;
    FILE_STANDARD_INFORMATION standardInfo;
    HANDLE pid = *(HANDLE *)RequesterContext;

    if (fileObject && fileObject->FileName.Length > 0) {
        status = FltQueryInformationFile(
            FltObjects->Instance, fileObject, &basicInfo, sizeof(FILE_BASIC_INFORMATION), FileBasicInformation, NULL);

        if (!NT_SUCCESS(status)) {
            Log("FltQueryInformationFile (Basic) failed. Status: 0x%x", status);
        }

        status = FltQueryInformationFile(
            FltObjects->Instance,
            fileObject,
            &standardInfo,
            sizeof(FILE_STANDARD_INFORMATION),
            FileStandardInformation,
            NULL);

        if (!NT_SUCCESS(status)) {
            Log("FltQueryInformationFile (Standard) failed. Status: 0x%x", status);
            return;
        }

        WCHAR volumeBuffer[MAX_PATH];
        UNICODE_STRING volumeName;

        RtlInitEmptyUnicodeString(&volumeName, volumeBuffer, sizeof(volumeBuffer));

        status = FltGetVolumeName(FltObjects->Volume, &volumeName, NULL);

        if (NT_SUCCESS(status)) {
            // publish information
            Log("[%s][PID: %d] Full Path: %wZ%wZ | Size: %llu bytes | Creation: %llu | Last Access: %llu | Last Write: "
                "%llu",
                FltGetIrpName(ParameterSnapshot->MajorFunction),
                HandleToULong(pid),
                &volumeName,
                &fileObject->FileName,
                standardInfo.EndOfFile.QuadPart,
                basicInfo.CreationTime.QuadPart,
                basicInfo.LastAccessTime.QuadPart,
                basicInfo.LastWriteTime.QuadPart);
        }
    } else {
        Log("Invalid file object or empty file name.");
    }

    if (RequesterContext != NULL) {
        ExFreePoolWithTag(RequesterContext, 'ctxT');
    }

    EBPF_EXT_LOG_EXIT();
}


FLT_POSTOP_CALLBACK_STATUS
PostOperationCallback(
    _Inout_ PFLT_CALLBACK_DATA Data,
    _In_ PCFLT_RELATED_OBJECTS FltObjects,
    _In_opt_ PVOID CompletionContext,
    _In_ FLT_POST_OPERATION_FLAGS Flags)
{
    UNREFERENCED_PARAMETER(Data);
    UNREFERENCED_PARAMETER(FltObjects);
    UNREFERENCED_PARAMETER(CompletionContext);
    UNREFERENCED_PARAMETER(Flags);

    return FLT_POSTOP_FINISHED_PROCESSING;
}

FLT_PREOP_CALLBACK_STATUS
PreOperationCallback(
    _Inout_ PFLT_CALLBACK_DATA Data,
    _In_ PCFLT_RELATED_OBJECTS FltObjects,
    _Flt_CompletionContext_Outptr_ PVOID* CompletionContext)
{
    NTSTATUS status;
    UNREFERENCED_PARAMETER(FltObjects);

    if (DoRequestOperationStatus(Data)) {
        HANDLE* context = ExAllocatePoolWithTag(NonPagedPool, sizeof(HANDLE), 'ctxT');
        if (context == NULL) {
            return FLT_PREOP_COMPLETE;
        }

        *context = PsGetProcessId(PsGetCurrentProcess());
        *CompletionContext = context;

        status = FltRequestOperationStatusCallback(
            Data,
            OperationStatusCallback,
            *CompletionContext
            // (PVOID)(++OperationStatusCtx)
        );

        if (!NT_SUCCESS(status)) {
            Log("FltRequestOperationStatusCallback failed. status = 0x%x", status);
            ExFreePoolWithTag(context, 'ctxT');
        }
    }

    return FLT_PREOP_SUCCESS_WITH_CALLBACK;
}

// Unload callback
NTSTATUS
UnloadCallback(_In_ FLT_FILTER_UNLOAD_FLAGS Flags)
{
    UNREFERENCED_PARAMETER(Flags);

    PAGED_CODE();

    FltUnregisterFilter(gFilterHandle);
    Log("Filter unloaded successfully.\n");

    return STATUS_SUCCESS;
}

const FLT_OPERATION_REGISTRATION Operations[] = {
    {IRP_MJ_CREATE, 0, PreOperationCallback, PostOperationCallback},
    {IRP_MJ_CLOSE, 0, PreOperationCallback, PostOperationCallback},
    {IRP_MJ_READ, 0, PreOperationCallback, PostOperationCallback},
    {IRP_MJ_WRITE, 0, PreOperationCallback, PostOperationCallback},
    {IRP_MJ_SET_INFORMATION, 0, PreOperationCallback, PostOperationCallback},
    {IRP_MJ_FLUSH_BUFFERS, 0, PreOperationCallback, PostOperationCallback},
    {IRP_MJ_DIRECTORY_CONTROL, 0, PreOperationCallback, PostOperationCallback},
    {IRP_MJ_FILE_SYSTEM_CONTROL, 0, PreOperationCallback, PostOperationCallback},
    {IRP_MJ_CLEANUP, 0, PreOperationCallback, PostOperationCallback},
    {IRP_MJ_OPERATION_END}};

// Filter registration structure
const FLT_REGISTRATION FilterRegistration = {
    sizeof(FLT_REGISTRATION), // Size
    FLT_REGISTRATION_VERSION, // Version
    0,                        // Flags
    NULL,                     // Context
    Operations,
    UnloadCallback, // Unload
    FilterInstanceSetup,           // Instance setup
    FilterInstanceQueryTeardown,           // Instance query teardown
    FilterInstanceTeardownStart,           // Instance teardown start
    FilterInstanceTeardownComplete,           // Instance teardown complete
    NULL,           // Generate file name
    NULL,           // Normalize name component
    NULL            // Normalize context cleanup
};

//
// Client attach/detach handler routines.
//

static ebpf_result_t
_ntos_ebpf_extension_fileevent_on_client_attach(
    _In_ const ebpf_extension_hook_client_t* attaching_client,
    _In_ const ebpf_extension_hook_provider_t* provider_context)
{
    ebpf_result_t result = EBPF_SUCCESS;
    bool push_lock_acquired = false;

    EBPF_EXT_LOG_ENTRY();

    UNREFERENCED_PARAMETER(attaching_client);
    UNREFERENCED_PARAMETER(provider_context);

    ExAcquirePushLockExclusive(&_ebpf_fileevent_hook_provider_lock);

    push_lock_acquired = true;

    if (!_ebpf_fileevent_hook_provider_registered) {
        // Register file system filter
        NTSTATUS status = FltRegisterFilter(_ebpf_driver_object, &FilterRegistration, &gFilterHandle);
        Log("Register filter result: 0x%x", status);
        Log("gFilterHandle: %w", gFilterHandle);
        if (NT_SUCCESS(status)) {
            status = FltStartFiltering(gFilterHandle);
            Log("FltStartFiltering filter result: 0x%x", status);
            if (!NT_SUCCESS(status)) {
                FltUnregisterFilter(gFilterHandle);
                goto Exit;
            }
        }
        _ebpf_fileevent_hook_provider_registered = TRUE;
    }

    _ebpf_fileevent_hook_provider_registration_count++;

Exit:
    if (push_lock_acquired) {
        ExReleasePushLockExclusive(&_ebpf_fileevent_hook_provider_lock);
    }

    EBPF_EXT_RETURN_RESULT(result);
}

static void
_ntos_ebpf_extension_fileevent_on_client_detach(_In_ const ebpf_extension_hook_client_t* detaching_client)
{
    EBPF_EXT_LOG_ENTRY();

    UNREFERENCED_PARAMETER(detaching_client);

    ExAcquirePushLockExclusive(&_ebpf_fileevent_hook_provider_lock);

    _ebpf_fileevent_hook_provider_registration_count--;

    if (_ebpf_fileevent_hook_provider_registered) {
        FltUnregisterFilter(gFilterHandle);
        _ebpf_fileevent_hook_provider_registered = FALSE; 
    }

    ExReleasePushLockExclusive(&_ebpf_fileevent_hook_provider_lock);

    EBPF_EXT_LOG_EXIT();
}

//
// NMR Registration Helper Routines.
//

void
ebpf_ext_unregister_fileevent()
{
    if (_ebpf_fileevent_hook_provider_context) {
        ebpf_extension_hook_provider_unregister(_ebpf_fileevent_hook_provider_context);
        _ebpf_fileevent_hook_provider_context = NULL;
    }
}

NTSTATUS
ebpf_ext_register_fileevent()
{
    NTSTATUS status = STATUS_SUCCESS;

    EBPF_EXT_LOG_ENTRY();

    const ebpf_extension_program_info_provider_parameters_t program_info_provider_parameters = {
        &_ebpf_fileevent_program_info_provider_moduleid, &_ebpf_fileevent_program_data};
    const ebpf_extension_hook_provider_parameters_t hook_provider_parameters = {
        &_ebpf_fileevent_hook_provider_moduleid, &_ntos_ebpf_fileevent_hook_provider_data};

    // Set the program type as the provider module id.
    _ebpf_fileevent_program_info_provider_moduleid.Guid = EBPF_PROGRAM_TYPE_FILEEVENT;
    _ebpf_fileevent_hook_provider_moduleid.Guid = EBPF_ATTACH_TYPE_FILEEVENT;
    status = ebpf_extension_program_info_provider_register(
        &program_info_provider_parameters, &_ebpf_fileevent_program_info_provider_context);
    if (!NT_SUCCESS(status)) {
        EBPF_EXT_LOG_MESSAGE_NTSTATUS(
            EBPF_EXT_TRACELOG_LEVEL_ERROR,
            EBPF_EXT_TRACELOG_KEYWORD_PROCESS,
            "ebpf_extension_program_info_provider_register",
            status);
        goto Exit;
    }

    status = ebpf_extension_hook_provider_register(
        &hook_provider_parameters,
        _ntos_ebpf_extension_fileevent_on_client_attach,
        _ntos_ebpf_extension_fileevent_on_client_detach,
        NULL,
        &_ebpf_fileevent_hook_provider_context);
    if (status != EBPF_SUCCESS) {
        EBPF_EXT_LOG_MESSAGE_NTSTATUS(
            EBPF_EXT_TRACELOG_LEVEL_ERROR,
            EBPF_EXT_TRACELOG_KEYWORD_PROCESS,
            "ebpf_extension_hook_provider_register",
            status);
        goto Exit;
    }


Exit:
    if (!NT_SUCCESS(status)) {
        ebpf_ext_unregister_fileevent();
    }
    EBPF_EXT_RETURN_NTSTATUS(status);
}

typedef struct _fileevent_notify_context
{
    EBPF_CONTEXT_HEADER;
    fileevent_md_t fileevent_md;
} fileevent_notify_context_t;

static ebpf_result_t
_ebpf_fileevent_context_create(
    _In_reads_bytes_opt_(data_size_in) const uint8_t* data_in,
    size_t data_size_in,
    _In_reads_bytes_opt_(context_size_in) const uint8_t* context_in,
    size_t context_size_in,
    _Outptr_ void** context)
{
    EBPF_EXT_LOG_ENTRY();
    ebpf_result_t result;
    fileevent_notify_context_t* fileevent_context = NULL;

    *context = NULL;

    if (context_in == NULL || context_size_in < sizeof(fileevent_md_t)) {
        EBPF_EXT_LOG_MESSAGE(EBPF_EXT_TRACELOG_LEVEL_ERROR, EBPF_EXT_TRACELOG_KEYWORD_PROCESS, "Context is required");
        result = EBPF_INVALID_ARGUMENT;
        goto Exit;
    }

    fileevent_context = (fileevent_notify_context_t*)ExAllocatePoolUninitialized(
        NonPagedPoolNx, sizeof(fileevent_notify_context_t), EBPF_EXTENSION_POOL_TAG);
    EBPF_EXT_BAIL_ON_ALLOC_FAILURE_RESULT(
        EBPF_EXT_TRACELOG_KEYWORD_PROCESS, fileevent_context, "fileevent_context", result);

    // Copy the context from the caller.
    memcpy(fileevent_context, context_in, sizeof(fileevent_md_t));

    // Replace the process_id_start and process_id_end with pointers to data_in.
    fileevent_context->fileevent_md.event_data_start = (uint8_t*)data_in;
    fileevent_context->fileevent_md.event_data_end = (uint8_t*)data_in + data_size_in;

    *context = fileevent_context;
    fileevent_context = NULL;
    result = EBPF_SUCCESS;

Exit:
    if (fileevent_context) {
        ExFreePool(fileevent_context);
        fileevent_context = NULL;
    }
    EBPF_EXT_RETURN_RESULT(result);
}

static void
_ebpf_fileevent_context_destroy(
    _In_opt_ void* context,
    _Out_writes_bytes_to_(*data_size_out, *data_size_out) uint8_t* data_out,
    _Inout_ size_t* data_size_out,
    _Out_writes_bytes_to_(*context_size_out, *context_size_out) uint8_t* context_out,
    _Inout_ size_t* context_size_out)
{
    EBPF_EXT_LOG_ENTRY();
    fileevent_notify_context_t* fileevent_context = NULL;
    fileevent_md_t* fileevent_context_out = NULL;

    if (!context) {
        goto Exit;
    }

    fileevent_context = CONTAINING_RECORD(context, fileevent_notify_context_t, fileevent_md);
    fileevent_context_out = (fileevent_md_t*)context_out;

    if (context_out != NULL && *context_size_out >= sizeof(fileevent_md_t)) {
        // Copy the context to the caller.
        memcpy(fileevent_context_out, &fileevent_context->fileevent_md, sizeof(fileevent_md_t));

        // Zero out the event context info.
        fileevent_context_out->event_data_start = 0;
        fileevent_context_out->event_data_end = 0;
        *context_size_out = sizeof(fileevent_md_t);
    }
    else {
        *context_size_out = 0;
    }

    // Copy the event data to 'data_out'.
    if (data_out != NULL && *data_size_out >= (size_t)(fileevent_context->fileevent_md.event_data_end -
        fileevent_context->fileevent_md.event_data_start)) {
        memcpy(
            data_out,
            fileevent_context->fileevent_md.event_data_start,
            fileevent_context->fileevent_md.event_data_end -
            fileevent_context->fileevent_md.event_data_start);
        *data_size_out = fileevent_context->fileevent_md.event_data_end -
            fileevent_context->fileevent_md.event_data_start;
    }
    else {
        *data_size_out = 0;
    }

    ExFreePool(fileevent_context);

Exit:
    EBPF_EXT_LOG_EXIT();
}

void
_ebpf_fileevent_push_event(_In_ fileevent_md_t* fileevent_event)
{
    // Logging may delay the event processing, consider enabling only for debugging or if the calling frequency for a
    // specific use case is low.
    // EBPF_EXT_LOG_ENTRY();

    if (fileevent_event == NULL) {
        return;
    }

    ebpf_result_t result;
    ebpf_extension_hook_client_t* client_context = NULL;
    fileevent_notify_context_t fileevent_event_notify_context = { 0 };
    uint64_t event_size = fileevent_event->event_data_end - fileevent_event->event_data_start;
    bool push_lock_acquired = false;

    // Currently, the verifier does not support read-only contexts, so we need to copy the event data, rather than
    // directly passing the existing pointers.
    // Verifier feature proposal: https://github.com/vbpf/ebpf-verifier/issues/639
    ExAcquirePushLockExclusive(&_ebpf_fileevent_push_event_lock);
    push_lock_acquired = true;
    if (event_size > _event_buffer_size) {
        // If the event buffer is too small, attempt to resize it.
        uint8_t* new_event_buffer =
            (uint8_t*)ExAllocatePoolUninitialized(NonPagedPoolNx, event_size, EBPF_FILEEVENT_EXTENSION_POOL_TAG);
        if (new_event_buffer == NULL) {
            EBPF_EXT_LOG_MESSAGE(
                EBPF_EXT_TRACELOG_LEVEL_ERROR,
                EBPF_EXT_TRACELOG_KEYWORD_NETEVENT,
                "Failed to resize the event buffer - event lost");
            goto Exit;
        }
        if (_event_buffer) {
            ExFreePool(_event_buffer);
        }
        _event_buffer = new_event_buffer;
        _event_buffer_size = event_size;
    }
    memcpy(_event_buffer, fileevent_event->event_data_start, event_size);
    fileevent_event_notify_context.fileevent_md.event_data_start = _event_buffer;
    fileevent_event_notify_context.fileevent_md.event_data_end = _event_buffer + event_size;

    // For each attached client call the netevent hook.
    client_context = ebpf_extension_hook_get_next_attached_client(_ebpf_fileevent_hook_provider_context, NULL);
    while (client_context != NULL) {
        NTSTATUS status = 0;
        if (ebpf_extension_hook_client_enter_rundown(client_context)) {
            result = ebpf_extension_hook_invoke_program(
                client_context, &fileevent_event_notify_context.fileevent_md, (uint32_t*)&status);
            if (result != EBPF_SUCCESS) {
                EBPF_EXT_LOG_MESSAGE_GUID_STATUS(
                    EBPF_EXT_TRACELOG_LEVEL_ERROR,
                    EBPF_EXT_TRACELOG_KEYWORD_NETEVENT,
                    "regevent_ebpf_extension_hook_invoke_program failed module ",
                    ebpf_extension_hook_provider_get_client_module_id(client_context),
                    status);
            }
            ebpf_extension_hook_client_leave_rundown(client_context);
        }
        else {
            EBPF_EXT_LOG_MESSAGE(
                EBPF_EXT_TRACELOG_LEVEL_ERROR,
                EBPF_EXT_TRACELOG_KEYWORD_NETEVENT,
                "regevent_ebpf_extension_hook_client_enter_rundown failed");
        }
        client_context =
            ebpf_extension_hook_get_next_attached_client(_ebpf_fileevent_hook_provider_context, client_context);
    }

Exit:
    if (push_lock_acquired) {
        ExReleasePushLockExclusive(&_ebpf_fileevent_push_event_lock);
    }

    // EBPF_EXT_LOG_EXIT();
}
