#pragma once

#include "ebpf_ext.h"
#include "ebpf_extension.h"
#include "ebpf_regevent_hooks.h"
#include "ebpf_regevent_program_attach_type_guids.h"
#include "ebpf_program_types.h"

// registry event program information.
static const ebpf_helper_function_prototype_t _regevent_ebpf_extension_helper_function_prototype[] = {
    {.header = {EBPF_HELPER_FUNCTION_PROTOTYPE_CURRENT_VERSION, EBPF_HELPER_FUNCTION_PROTOTYPE_CURRENT_VERSION_SIZE},
     .helper_id = EBPF_MAX_GENERAL_HELPER_FUNCTION + 1,
     .name = "bpf_regevent_push_event",
     .return_type = EBPF_RETURN_TYPE_INTEGER,
     .arguments =
         {EBPF_ARGUMENT_TYPE_PTR_TO_CTX, EBPF_ARGUMENT_TYPE_PTR_TO_WRITABLE_MEM, EBPF_ARGUMENT_TYPE_CONST_SIZE}},
};

static const ebpf_context_descriptor_t _ebpf_regevent_context_descriptor = {
    sizeof(regevent_md_t),
    EBPF_OFFSET_OF(regevent_md_t, event_data_start),
    EBPF_OFFSET_OF(regevent_md_t, event_data_end),
    -1,
};

// Need to allocate these in ebpf_structs.h in ebpf-for-windows repo.
#define BPF_PROG_TYPE_REGEVENT 99940
#define BPF_ATTACH_TYPE_REGEVENT 99940

static const ebpf_program_type_descriptor_t _ebpf_regevent_program_type_descriptor = {
    .header = {EBPF_PROGRAM_TYPE_DESCRIPTOR_CURRENT_VERSION, EBPF_PROGRAM_TYPE_DESCRIPTOR_CURRENT_VERSION_SIZE},
    .name = "registry",
    .context_descriptor = &_ebpf_regevent_context_descriptor,
    .program_type = EBPF_PROGRAM_TYPE_REGEVENT_GUID,
    .bpf_prog_type = BPF_PROG_TYPE_REGEVENT,
};

static const ebpf_program_info_t _ebpf_regevent_program_info = {
    .header = {EBPF_PROGRAM_INFORMATION_CURRENT_VERSION, EBPF_PROGRAM_INFORMATION_CURRENT_VERSION_SIZE},
    .program_type_descriptor = &_ebpf_regevent_program_type_descriptor,
    .count_of_program_type_specific_helpers = EBPF_COUNT_OF(_regevent_ebpf_extension_helper_function_prototype),
    .program_type_specific_helper_prototype = _regevent_ebpf_extension_helper_function_prototype,
};

static const ebpf_program_section_info_t _ebpf_regevent_section_info[] = {
    {
        .header =
            {EBPF_PROGRAM_SECTION_INFORMATION_CURRENT_VERSION, EBPF_PROGRAM_SECTION_INFORMATION_CURRENT_VERSION_SIZE},
        .section_name = (wchar_t*)L"registry",
        .program_type = &EBPF_PROGRAM_TYPE_REGEVENT,
        .attach_type = &EBPF_ATTACH_TYPE_REGEVENT,
        .bpf_program_type = BPF_PROG_TYPE_REGEVENT,
        .bpf_attach_type = BPF_ATTACH_TYPE_REGEVENT,
    },
};
