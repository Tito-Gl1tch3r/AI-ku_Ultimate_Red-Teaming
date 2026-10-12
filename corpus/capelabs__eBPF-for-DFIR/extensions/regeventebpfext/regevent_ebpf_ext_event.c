#include "ebpf_ntos_hooks.h"
#include "regevent_ebpf_ext_event.h"
#include "regevent_ebpf_ext_program_info.h"

#include <errno.h>

#define MAX_PATH 260

// Define a dynamic event buffer for optimizing the event data copy.
static uint8_t* _event_buffer = NULL; ///< Event buffer for copying the event data.
static size_t _event_buffer_size =
4096; ///< Initial size of the event buffer, which will be dynamically resized as needed.
EX_PUSH_LOCK _ebpf_regevent_push_event_lock;


static ebpf_result_t
_ebpf_regevent_context_create(
    _In_reads_bytes_opt_(data_size_in) const uint8_t* data_in,
    size_t data_size_in,
    _In_reads_bytes_opt_(context_size_in) const uint8_t* context_in,
    size_t context_size_in,
    _Outptr_ void** context);

static void
_ebpf_regevent_context_destroy(
    _In_opt_ void* context,
    _Out_writes_bytes_to_(*data_size_out, *data_size_out) uint8_t* data_out,
    _Inout_ size_t* data_size_out,
    _Out_writes_bytes_to_(*context_size_out, *context_size_out) uint8_t* context_out,
    _Inout_ size_t* context_size_out);

void
_ebpf_regevent_push_event(_In_ regevent_md_t* regevent_event);

static const void* _ebpf_regevent_helper_functions[] = {(void*)&_ebpf_regevent_push_event};

#define Log(format, ...) DbgPrintEx(DPFLTR_DEFAULT_ID, DPFLTR_ERROR_LEVEL, "[event]" format "\n", ##__VA_ARGS__)


static ebpf_helper_function_addresses_t _ebpf_regevent_helper_function_address_table = {
    .header = {EBPF_HELPER_FUNCTION_ADDRESSES_CURRENT_VERSION, EBPF_HELPER_FUNCTION_ADDRESSES_CURRENT_VERSION_SIZE},
    .helper_function_count = EBPF_COUNT_OF(_ebpf_regevent_helper_functions),
    .helper_function_address = (uint64_t*)_ebpf_regevent_helper_functions,
};

//
// Registry Program Information NPI Provider.
//
static ebpf_program_data_t _ebpf_regevent_program_data = {
    .header = EBPF_PROGRAM_DATA_HEADER,
    .program_info = &_ebpf_regevent_program_info,
    .program_type_specific_helper_function_addresses = &_ebpf_regevent_helper_function_address_table,
    .context_create = _ebpf_regevent_context_create,
    .context_destroy = _ebpf_regevent_context_destroy,
    .required_irql = PASSIVE_LEVEL,
    .capabilities = {.supports_context_header = true},
};

static ebpf_extension_data_t _ebpf_regevent_program_info_provider_data = {
    .header = {EBPF_EXTENSION_NPI_PROVIDER_VERSION, sizeof(_ebpf_regevent_program_data)},
    .data = &_ebpf_regevent_program_data};

NPI_MODULEID DECLSPEC_SELECTANY _ebpf_regevent_program_info_provider_moduleid = {sizeof(NPI_MODULEID), MIT_GUID, {0}};

static ebpf_extension_program_info_provider_t* _ebpf_regevent_program_info_provider_context = NULL;

//
// Registry Hook NPI Provider.
//
ebpf_attach_provider_data_t _ntos_ebpf_regevent_hook_provider_data = {
    .header = {EBPF_ATTACH_PROVIDER_DATA_CURRENT_VERSION, EBPF_ATTACH_PROVIDER_DATA_CURRENT_VERSION_SIZE},
    .supported_program_type = EBPF_PROGRAM_TYPE_REGEVENT_GUID,
    .bpf_attach_type = (bpf_attach_type_t)BPF_ATTACH_TYPE_REGEVENT,
};

NPI_MODULEID DECLSPEC_SELECTANY _ebpf_regevent_hook_provider_moduleid = {sizeof(NPI_MODULEID), MIT_GUID, {0}};

static ebpf_extension_hook_provider_t* _ebpf_regevent_hook_provider_context = NULL;

EX_PUSH_LOCK _ebpf_regevent_hook_provider_lock;
bool _ebpf_regevent_hook_provider_registered = FALSE;
uint64_t _ebpf_regevent_hook_provider_registration_count = 0;

//
// Registry monitoring
//

LARGE_INTEGER cookie;

NTSTATUS
RegistryCallback(PVOID CallbackContext, PVOID Argument1, PVOID Argument2);

NTSTATUS
GetKeyPath(PVOID Object, PUNICODE_STRING KeyPath);

NTSTATUS
RegistryCallback(
    PVOID CallbackContext,
    PVOID Argument1,
    PVOID Argument2
)
{
    UNREFERENCED_PARAMETER(CallbackContext);

    NTSTATUS status = STATUS_SUCCESS;
    REG_NOTIFY_CLASS notifyClass = (REG_NOTIFY_CLASS)(ULONG_PTR)Argument1;
    UNICODE_STRING keyPath = {0};
    PREG_SET_VALUE_KEY_INFORMATION preInfo;
    PREG_DELETE_VALUE_KEY_INFORMATION preDelValueInfo;
    PREG_DELETE_KEY_INFORMATION preDelInfo;
    PREG_CREATE_KEY_INFORMATION preCreateInfo;
    PREG_SET_INFORMATION_KEY_INFORMATION preSetInfo;
    PREG_QUERY_VALUE_KEY_INFORMATION preQueryValueInfo;
    PREG_QUERY_MULTIPLE_VALUE_KEY_INFORMATION preQueryMulValueInfo;
    PREG_POST_OPERATION_INFORMATION postOpInfo;

    HANDLE processId = PsGetCurrentProcessId();

    switch (notifyClass) {
    case RegNtPreDeleteValueKey:
        preDelValueInfo = (PREG_DELETE_VALUE_KEY_INFORMATION)Argument2;
        status = GetKeyPath(preDelValueInfo->Object, &keyPath);
        if (NT_SUCCESS(status)) {
            Log("[DeleteValueKey Reg][PID: %wZ] Key Path: %wZ / Value: %wZ",
                HandleToULong(processId),
                &keyPath,
                preDelValueInfo->ValueName);
        } else {
            Log("Failed to delete value key - status=0x%x", status);
        }
        break;

    case RegNtPreDeleteKey:
        preDelInfo = (PREG_DELETE_KEY_INFORMATION)Argument2;
        status = GetKeyPath(preDelInfo->Object, &keyPath);
        if (NT_SUCCESS(status)) {
            Log("[DeleteKey Reg][PID: %u] Key Path: %wZ", HandleToULong(processId), &keyPath);
        }
        break;

    case RegNtPreCreateKeyEx:
        preCreateInfo = (PREG_CREATE_KEY_INFORMATION)Argument2;
        status = GetKeyPath(preCreateInfo->RootObject, &keyPath);
        if (NT_SUCCESS(status)) {
            Log("[CreateKey Reg][PID: %u] Key Path: %wZ",
                HandleToULong(processId),
                &keyPath);
        }
        break;

    case RegNtPreSetValueKey:
        preInfo = (PREG_SET_VALUE_KEY_INFORMATION)Argument2;
        status = GetKeyPath(preInfo->Object, &keyPath);
        if (NT_SUCCESS(status)) {
            Log("[SetValue Reg][PID: %u][Type: %u] Key Path: %wZ / Value: %wZ", HandleToULong(processId),
                preInfo->Type,
                &keyPath,
                preInfo->ValueName);
        }
        break;

    case RegNtPreSetInformationKey:
        preSetInfo = (PREG_SET_INFORMATION_KEY_INFORMATION)Argument2;
        status = GetKeyPath(preSetInfo->Object, &keyPath);
        if (NT_SUCCESS(status)) {
            Log("[SetInformation Reg][PID: %u] Key Path: %wZ",
                HandleToULong(processId),
                &keyPath);
        }

    case RegNtPreQueryValueKey:
        preQueryValueInfo = (PREG_QUERY_VALUE_KEY_INFORMATION)Argument2;
        status = GetKeyPath(preQueryValueInfo->Object, &keyPath);
        if (NT_SUCCESS(status)) {
            Log("[QueryValue Reg][PID: %u] Key Path: %wZ / Value: %wZ", HandleToULong(processId), &keyPath, preQueryValueInfo->ValueName);
        }
        break;

    case RegNtPreQueryMultipleValueKey:
        preQueryMulValueInfo = (PREG_QUERY_MULTIPLE_VALUE_KEY_INFORMATION)Argument2;
        status = GetKeyPath(preQueryMulValueInfo->Object, &keyPath);
        if (NT_SUCCESS(status)) {
            Log("[QueryMultipleValue Reg][PID: %u] Key Path: %wZ / Entries: %u",
                HandleToULong(processId),
                &keyPath,
                preQueryMulValueInfo->EntryCount);
        }
        break;

    case RegNtPostDeleteKey:
    case RegNtPostSetValueKey:
    case RegNtPostDeleteValueKey:
    case RegNtPostSetInformationKey:
    case RegNtPostRenameKey:
    case RegNtPostQueryValueKey:
    case RegNtPostQueryMultipleValueKey:
        postOpInfo = (PREG_POST_OPERATION_INFORMATION)Argument2;
        status = GetKeyPath(postOpInfo->Object, &keyPath);
        if (NT_SUCCESS(status)) {
            Log("[PostOp][Type: %u][PID: %u] Key Path: %wZ", notifyClass, HandleToULong(processId), &keyPath);
        }
        break;

    default:
        break;
    }

    if (keyPath.Buffer != NULL) {
        RtlFreeUnicodeString(&keyPath);
    }

    return STATUS_SUCCESS;
}

NTSTATUS
GetKeyPath(PVOID Object, PUNICODE_STRING KeyPath)
{
    NTSTATUS status;
    ULONG resultLength = 0;
    POBJECT_NAME_INFORMATION nameInfo = NULL;

    // Query for the required length first
    status = ObQueryNameString(Object, NULL, 0, &resultLength);
    if (status != STATUS_INFO_LENGTH_MISMATCH) {
        Log("Initial query failed. status = 0x%x", status);
        return status;
    }

    // Allocate memory for the name information structure using ExAllocatePool2
    nameInfo = (POBJECT_NAME_INFORMATION)ExAllocatePool2(POOL_FLAG_NON_PAGED, resultLength, 'nmoN');
    if (!nameInfo) {
        Log("Memory allocation failed");
        return STATUS_INSUFFICIENT_RESOURCES;
    }

    // Query the actual name
    status = ObQueryNameString(Object, nameInfo, resultLength, &resultLength);
    if (NT_SUCCESS(status)) {
        status = RtlDuplicateUnicodeString(RTL_DUPLICATE_UNICODE_STRING_NULL_TERMINATE, &nameInfo->Name, KeyPath);
        if (!NT_SUCCESS(status)) {
            Log("Failed to duplicate KeyPath. status = 0x%x", status);
        }
    } else {
        Log("ObQueryNameString failed. status = 0x%x", status);
    }

    if (nameInfo != NULL) {
        ExFreePoolWithTag(nameInfo, 'nmoN');
    }

    return status;
}


//
// Client attach/detach handler routines.
//

static ebpf_result_t
_ntos_ebpf_extension_regevent_on_client_attach(
    _In_ const ebpf_extension_hook_client_t* attaching_client,
    _In_ const ebpf_extension_hook_provider_t* provider_context)
{
    ebpf_result_t result = EBPF_SUCCESS;
    bool push_lock_acquired = false;

    EBPF_EXT_LOG_ENTRY();

    UNREFERENCED_PARAMETER(attaching_client);
    UNREFERENCED_PARAMETER(provider_context);

    push_lock_acquired = true;

    if (!_ebpf_regevent_hook_provider_registered) {
        UNICODE_STRING altitude;
        RtlInitUnicodeString(&altitude, L"370000");

        NTSTATUS status = CmRegisterCallbackEx(RegistryCallback, &altitude, _ebpf_driver_object, NULL, &cookie, NULL);
        if (!NT_SUCCESS(status)) {
            Log("CmRegisterCallbackEx failed");
            goto Exit;
        }

        _ebpf_regevent_hook_provider_registered = TRUE;
    }

    _ebpf_regevent_hook_provider_registration_count++;

Exit:
    if (push_lock_acquired) {
        ExReleasePushLockExclusive(&_ebpf_regevent_hook_provider_lock);
    }

    EBPF_EXT_RETURN_RESULT(result);
}

static void
_ntos_ebpf_extension_regevent_on_client_detach(_In_ const ebpf_extension_hook_client_t* detaching_client)
{
    EBPF_EXT_LOG_ENTRY();

    UNREFERENCED_PARAMETER(detaching_client);

    if (_ebpf_regevent_hook_provider_registered) {
        CmUnRegisterCallback(cookie);
        _ebpf_regevent_hook_provider_registered = FALSE;
    }

    EBPF_EXT_LOG_EXIT();
}

//
// NMR Registration Helper Routines.
//

void
ebpf_ext_unregister_regevent()
{
    if (_ebpf_regevent_program_info_provider_context) {
        ebpf_extension_program_info_provider_unregister(_ebpf_regevent_program_info_provider_context);
        _ebpf_regevent_program_info_provider_context = NULL;
    }
}

NTSTATUS
ebpf_ext_register_regevent()
{
    NTSTATUS status = STATUS_SUCCESS;

    EBPF_EXT_LOG_ENTRY();

    const ebpf_extension_program_info_provider_parameters_t program_info_provider_parameters = {
        &_ebpf_regevent_program_info_provider_moduleid, &_ebpf_regevent_program_data};
    const ebpf_extension_hook_provider_parameters_t hook_provider_parameters = {
        &_ebpf_regevent_hook_provider_moduleid, &_ntos_ebpf_regevent_hook_provider_data};

    // Set the program type as the provider module id.
    _ebpf_regevent_program_info_provider_moduleid.Guid = EBPF_PROGRAM_TYPE_REGEVENT;
    _ebpf_regevent_hook_provider_moduleid.Guid = EBPF_ATTACH_TYPE_REGEVENT;
    status = ebpf_extension_program_info_provider_register(
        &program_info_provider_parameters, &_ebpf_regevent_program_info_provider_context);
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
        _ntos_ebpf_extension_regevent_on_client_attach,
        _ntos_ebpf_extension_regevent_on_client_detach,
        NULL,
        &_ebpf_regevent_hook_provider_context);
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
        ebpf_ext_unregister_regevent();
    }
    EBPF_EXT_RETURN_NTSTATUS(status);
}

typedef struct _regevent_notify_context
{
    EBPF_CONTEXT_HEADER;
    regevent_md_t regevent_md;
} regevent_notify_context_t;

static ebpf_result_t
_ebpf_regevent_context_create(
    _In_reads_bytes_opt_(data_size_in) const uint8_t* data_in,
    size_t data_size_in,
    _In_reads_bytes_opt_(context_size_in) const uint8_t* context_in,
    size_t context_size_in,
    _Outptr_ void** context)
{
    EBPF_EXT_LOG_ENTRY();
    ebpf_result_t result;
    regevent_notify_context_t* regevent_context = NULL;

    *context = NULL;

    if (context_in == NULL || context_size_in < sizeof(regevent_md_t)) {
        EBPF_EXT_LOG_MESSAGE(EBPF_EXT_TRACELOG_LEVEL_ERROR, EBPF_EXT_TRACELOG_KEYWORD_PROCESS, "Context is required");
        result = EBPF_INVALID_ARGUMENT;
        goto Exit;
    }

    regevent_context = (regevent_notify_context_t*)ExAllocatePoolUninitialized(
        NonPagedPoolNx, sizeof(regevent_notify_context_t), EBPF_EXTENSION_POOL_TAG);
    EBPF_EXT_BAIL_ON_ALLOC_FAILURE_RESULT(
        EBPF_EXT_TRACELOG_KEYWORD_PROCESS, regevent_context, "regevent_context", result);

    // Copy the context from the caller.
    memcpy(regevent_context, context_in, sizeof(regevent_md_t));

    // Replace the process_id_start and process_id_end with pointers to data_in.
    regevent_context->regevent_md.event_data_start = (uint8_t*)data_in;
    regevent_context->regevent_md.event_data_end = (uint8_t*)data_in + data_size_in;

    *context = regevent_context;
    regevent_context = NULL;
    result = EBPF_SUCCESS;

Exit:
    if (regevent_context) {
        ExFreePool(regevent_context);
        regevent_context = NULL;
    }
    EBPF_EXT_RETURN_RESULT(result);
}

static void
_ebpf_regevent_context_destroy(
    _In_opt_ void* context,
    _Out_writes_bytes_to_(*data_size_out, *data_size_out) uint8_t* data_out,
    _Inout_ size_t* data_size_out,
    _Out_writes_bytes_to_(*context_size_out, *context_size_out) uint8_t* context_out,
    _Inout_ size_t* context_size_out)
{
    EBPF_EXT_LOG_ENTRY();
    regevent_notify_context_t* regevent_context = NULL;
    regevent_md_t* regevent_context_out = NULL;

    if (!context) {
        goto Exit;
    }

    regevent_context = CONTAINING_RECORD(context, regevent_notify_context_t, regevent_md);
    regevent_context_out = (regevent_md_t*)context_out;

    if (context_out != NULL && *context_size_out >= sizeof(regevent_md_t)) {
        // Copy the context to the caller.
        memcpy(regevent_context_out, &regevent_context->regevent_md, sizeof(regevent_md_t));

        // Zero out the event context info.
        regevent_context_out->event_data_start = 0;
        regevent_context_out->event_data_end = 0;
        *context_size_out = sizeof(regevent_md_t);
    }
    else {
        *context_size_out = 0;
    }

    // Copy the event data to 'data_out'.
    if (data_out != NULL && *data_size_out >= (size_t)(regevent_context->regevent_md.event_data_end -
        regevent_context->regevent_md.event_data_start)) {
        memcpy(
            data_out,
            regevent_context->regevent_md.event_data_start,
            regevent_context->regevent_md.event_data_end -
            regevent_context->regevent_md.event_data_start);
        *data_size_out = regevent_context->regevent_md.event_data_end -
            regevent_context->regevent_md.event_data_start;
    }
    else {
        *data_size_out = 0;
    }

    ExFreePool(regevent_context);

Exit:
    EBPF_EXT_LOG_EXIT();
}

void
_ebpf_regevent_push_event(_In_ regevent_md_t* regevent_event)
{
    // Logging may delay the event processing, consider enabling only for debugging or if the calling frequency for a
    // specific use case is low.
    // EBPF_EXT_LOG_ENTRY();

    if (regevent_event == NULL) {
        return;
    }

    ebpf_result_t result;
    ebpf_extension_hook_client_t* client_context = NULL;
    regevent_notify_context_t regevent_event_notify_context = { 0 };
    uint64_t event_size = regevent_event->event_data_end - regevent_event->event_data_start;
    bool push_lock_acquired = false;

    // Currently, the verifier does not support read-only contexts, so we need to copy the event data, rather than
    // directly passing the existing pointers.
    // Verifier feature proposal: https://github.com/vbpf/ebpf-verifier/issues/639
    ExAcquirePushLockExclusive(&_ebpf_regevent_push_event_lock);
    push_lock_acquired = true;
    if (event_size > _event_buffer_size) {
        // If the event buffer is too small, attempt to resize it.
        uint8_t* new_event_buffer =
            (uint8_t*)ExAllocatePoolUninitialized(NonPagedPoolNx, event_size, EBPF_REGEVENT_EXTENSION_POOL_TAG);
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
    memcpy(_event_buffer, regevent_event->event_data_start, event_size);
    regevent_event_notify_context.regevent_md.event_data_start = _event_buffer;
    regevent_event_notify_context.regevent_md.event_data_end = _event_buffer + event_size;

    // For each attached client call the netevent hook.
    client_context = ebpf_extension_hook_get_next_attached_client(_ebpf_regevent_hook_provider_context, NULL);
    while (client_context != NULL) {
        NTSTATUS status = 0;
        if (ebpf_extension_hook_client_enter_rundown(client_context)) {
            result = ebpf_extension_hook_invoke_program(
                client_context, &regevent_event_notify_context.regevent_md, (uint32_t*)&status);
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
            ebpf_extension_hook_get_next_attached_client(_ebpf_regevent_hook_provider_context, client_context);
    }

Exit:
    if (push_lock_acquired) {
        ExReleasePushLockExclusive(&_ebpf_regevent_push_event_lock);
    }

    // EBPF_EXT_LOG_EXIT();
}
