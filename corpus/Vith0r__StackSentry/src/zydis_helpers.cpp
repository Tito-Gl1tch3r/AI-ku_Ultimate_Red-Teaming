#include <Zydis/Zydis.h>

enum class ZydisBranchKind {
    Unknown,
    Other,
    Call,
    Jump,
    Return
};

static bool DecodeZydisInstruction64(
    const uint8_t* bytes,
    size_t size,
    uint64_t runtime_address,
    ZydisDecodedInstruction& instruction,
    ZydisDecodedOperand operands[ZYDIS_MAX_OPERAND_COUNT]) {
    if (!bytes || size == 0) {
        return false;
    }
    (void)runtime_address;

    ZydisDecoder decoder;
    if (!ZYAN_SUCCESS(ZydisDecoderInit(&decoder, ZYDIS_MACHINE_MODE_LONG_64, ZYDIS_STACK_WIDTH_64))) {
        return false;
    }

    return ZYAN_SUCCESS(ZydisDecoderDecodeFull(
        &decoder,
        bytes,
        static_cast<ZyanUSize>(size),
        &instruction,
        operands));
}

static ZydisBranchKind ZydisBranchKindOf(const ZydisDecodedInstruction& instruction) {
    switch (instruction.mnemonic) {
    case ZYDIS_MNEMONIC_CALL:
        return ZydisBranchKind::Call;
    case ZYDIS_MNEMONIC_JMP:
        return ZydisBranchKind::Jump;
    case ZYDIS_MNEMONIC_RET:
        return ZydisBranchKind::Return;
    default:
        return ZydisBranchKind::Other;
    }
}

static bool ZydisIsGprRegister(ZydisRegister reg) {
    const ZydisRegisterClass klass = ZydisRegisterGetClass(reg);
    return klass == ZYDIS_REGCLASS_GPR64 ||
        klass == ZYDIS_REGCLASS_GPR32 ||
        klass == ZYDIS_REGCLASS_GPR16 ||
        klass == ZYDIS_REGCLASS_GPR8;
}

static bool ZydisHasExplicitGprRegisterTarget(
    const ZydisDecodedInstruction& instruction,
    const ZydisDecodedOperand operands[ZYDIS_MAX_OPERAND_COUNT]) {
    for (uint8_t i = 0; i < instruction.operand_count; ++i) {
        const auto& operand = operands[i];
        if (operand.visibility != ZYDIS_OPERAND_VISIBILITY_EXPLICIT) {
            continue;
        }
        if (operand.type == ZYDIS_OPERAND_TYPE_REGISTER && ZydisIsGprRegister(operand.reg.value)) {
            return true;
        }
    }
    return false;
}

[[maybe_unused]] static bool ZydisDecodeInstructionEndingAt(
    const uint8_t* bytes,
    size_t size,
    uint64_t runtime_address,
    size_t end_offset,
    ZydisDecodedInstruction& instruction,
    ZydisDecodedOperand operands[ZYDIS_MAX_OPERAND_COUNT]) {
    if (!bytes || end_offset == 0 || end_offset > size) {
        return false;
    }

    bool have_fallback = false;
    ZydisDecodedInstruction fallback{};
    ZydisDecodedOperand fallback_operands[ZYDIS_MAX_OPERAND_COUNT]{};
    const size_t max_instruction_length = 15;
    const size_t first_start = end_offset > max_instruction_length ? end_offset - max_instruction_length : 0;
    for (size_t start = first_start; start < end_offset; ++start) {
        ZydisDecodedInstruction candidate{};
        ZydisDecodedOperand candidate_operands[ZYDIS_MAX_OPERAND_COUNT]{};
        if (!DecodeZydisInstruction64(
            bytes + start,
            end_offset - start,
            runtime_address + start,
            candidate,
            candidate_operands)) {
            continue;
        }
        if (start + candidate.length != end_offset) {
            continue;
        }

        const ZydisBranchKind kind = ZydisBranchKindOf(candidate);
        if (kind == ZydisBranchKind::Call || kind == ZydisBranchKind::Jump || kind == ZydisBranchKind::Return) {
            instruction = candidate;
            for (size_t i = 0; i < ZYDIS_MAX_OPERAND_COUNT; ++i) {
                operands[i] = candidate_operands[i];
            }
            return true;
        }

        if (!have_fallback) {
            fallback = candidate;
            for (size_t i = 0; i < ZYDIS_MAX_OPERAND_COUNT; ++i) {
                fallback_operands[i] = candidate_operands[i];
            }
            have_fallback = true;
        }
    }
    if (!have_fallback) {
        return false;
    }

    instruction = fallback;
    for (size_t i = 0; i < ZYDIS_MAX_OPERAND_COUNT; ++i) {
        operands[i] = fallback_operands[i];
    }
    return true;
}

static bool ZydisBufferHasReturnAfter(
    const uint8_t* bytes,
    size_t size,
    uint64_t runtime_address,
    size_t start_offset) {
    size_t offset = start_offset;
    for (uint32_t decoded = 0; decoded < 6 && offset < size; ++decoded) {
        ZydisDecodedInstruction instruction{};
        ZydisDecodedOperand operands[ZYDIS_MAX_OPERAND_COUNT]{};
        if (!DecodeZydisInstruction64(
            bytes + offset,
            size - offset,
            runtime_address + offset,
            instruction,
            operands)) {
            return false;
        }
        if (instruction.mnemonic == ZYDIS_MNEMONIC_RET) {
            return true;
        }
        if (ZydisBranchKindOf(instruction) == ZydisBranchKind::Jump) {
            return false;
        }
        offset += instruction.length;
    }
    return false;
}

[[maybe_unused]] static bool ZydisLooksLikeRegisterProxyGadget(
    const uint8_t* bytes,
    size_t size,
    uint64_t runtime_address) {
    ZydisDecodedInstruction instruction{};
    ZydisDecodedOperand operands[ZYDIS_MAX_OPERAND_COUNT]{};
    if (!DecodeZydisInstruction64(bytes, size, runtime_address, instruction, operands)) {
        return false;
    }

    const ZydisBranchKind kind = ZydisBranchKindOf(instruction);
    if ((kind != ZydisBranchKind::Call && kind != ZydisBranchKind::Jump) ||
        !ZydisHasExplicitGprRegisterTarget(instruction, operands)) {
        return false;
    }

    if (kind == ZydisBranchKind::Jump) {
        return true;
    }

    return ZydisBufferHasReturnAfter(bytes, size, runtime_address, instruction.length);
}
