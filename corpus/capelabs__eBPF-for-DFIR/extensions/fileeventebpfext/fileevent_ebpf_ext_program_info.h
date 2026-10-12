// Copyright (c) Microsoft Corporation
// SPDX-License-Identifier: MIT
#pragma once

#include "ebpf_ext.h"
#include "ebpf_extension.h"
#include "ebpf_fileevent_hooks.h"
#include "ebpf_fileevent_program_attach_type_guids.h"
#include "ebpf_program_types.h"

#define BPF_ATTACH_TYPE_FILEEVENT 99910
#define BPF_PROG_TYPE_FILEEVENT 99910

static const ebpf_helper_function_prototype_t _fileevent_ebpf_extension_helper_function_prototype[] = {
    {.header =
         {.version = EBPF_HELPER_FUNCTION_PROTOTYPE_CURRENT_VERSION,
          .size = EBPF_HELPER_FUNCTION_PROTOTYPE_CURRENT_VERSION_SIZE},
     .helper_id = EBPF_MAX_GENERAL_HELPER_FUNCTION + 1,
     .name = "bpf_fileevent_push_event",
     .return_type = EBPF_RETURN_TYPE_INTEGER,
     .arguments = {EBPF_ARGUMENT_TYPE_PTR_TO_CTX}} };

static const ebpf_context_descriptor_t _ebpf_fileevent_program_context_descriptor = {
    (int)sizeof(fileevent_md_t),
    EBPF_OFFSET_OF(fileevent_md_t, event_data_start),
    EBPF_OFFSET_OF(fileevent_md_t, event_data_end),
    -1,
};

static const ebpf_program_type_descriptor_t _ebpf_program_type_fileevent_guid = {
    .header =
        {.version = EBPF_PROGRAM_TYPE_DESCRIPTOR_CURRENT_VERSION,
         .size = EBPF_PROGRAM_TYPE_DESCRIPTOR_CURRENT_VERSION_SIZE},
    .name = "fileevent",
    .context_descriptor = &_ebpf_fileevent_program_context_descriptor,
    .program_type = EBPF_PROGRAM_TYPE_FILEEVENT_GUID,
    .bpf_prog_type = BPF_PROG_TYPE_FILEEVENT,
    .is_privileged = 0 };

static const ebpf_program_info_t _ebpf_fileevent_program_info = {
    .header =
        {.version = EBPF_PROGRAM_INFORMATION_CURRENT_VERSION, .size = EBPF_PROGRAM_INFORMATION_CURRENT_VERSION_SIZE},
    .program_type_descriptor = &_ebpf_program_type_fileevent_guid,
    .count_of_program_type_specific_helpers = EBPF_COUNT_OF(_fileevent_ebpf_extension_helper_function_prototype),
    .program_type_specific_helper_prototype = _fileevent_ebpf_extension_helper_function_prototype,
    .count_of_global_helpers = 0,
    .global_helper_prototype = NULL };

static const ebpf_program_section_info_t _ebpf_fileevent_section_info[] = {
    {
        .header =
            {.version = EBPF_PROGRAM_SECTION_INFORMATION_CURRENT_VERSION,
             .size = EBPF_PROGRAM_SECTION_INFORMATION_CURRENT_VERSION_SIZE},
        .section_name = L"fileevent",
        .program_type = &EBPF_PROGRAM_TYPE_FILEEVENT,
        .attach_type = &EBPF_ATTACH_TYPE_FILEEVENT,
        .bpf_program_type = BPF_PROG_TYPE_FILEEVENT,
        .bpf_attach_type = BPF_ATTACH_TYPE_FILEEVENT,
    },
};
