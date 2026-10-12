static bool GetPeMachine(const fs::path& path, uint16_t& machine) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        return false;
    }

    uint16_t mz = 0;
    input.read(reinterpret_cast<char*>(&mz), sizeof(mz));
    if (mz != 0x5A4D) {
        return false;
    }

    input.seekg(0x3C, std::ios::beg);
    uint32_t pe_offset = 0;
    input.read(reinterpret_cast<char*>(&pe_offset), sizeof(pe_offset));
    input.seekg(pe_offset, std::ios::beg);
    uint32_t pe_sig = 0;
    input.read(reinterpret_cast<char*>(&pe_sig), sizeof(pe_sig));
    if (pe_sig != 0x00004550) {
        return false;
    }
    input.read(reinterpret_cast<char*>(&machine), sizeof(machine));
    return true;
}

static std::vector<ModuleInfo> EnumerateModules(DWORD pid) {
    std::vector<ModuleInfo> modules;
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid);
    if (snapshot == INVALID_HANDLE_VALUE) {
        return modules;
    }

    MODULEENTRY32W entry{};
    entry.dwSize = sizeof(entry);
    if (Module32FirstW(snapshot, &entry)) {
        do {
            ModuleInfo module;
            module.base = reinterpret_cast<uint64_t>(entry.modBaseAddr);
            module.size = static_cast<uint64_t>(entry.modBaseSize);
            module.name = entry.szModule;
            module.path = entry.szExePath;
            modules.push_back(std::move(module));
        } while (Module32NextW(snapshot, &entry));
    }

    CloseHandle(snapshot);
    return modules;
}

static const ModuleInfo* FindModuleForAddress(const std::vector<ModuleInfo>& modules, uint64_t address) {
    for (const auto& module : modules) {
        if (address >= module.base && address < module.base + module.size) {
            return &module;
        }
    }
    return nullptr;
}

static uint64_t FindRemoteModuleBase(DWORD pid, const std::wstring& module_basename) {
    const std::wstring expected = ToLower(module_basename);
    for (const auto& module : EnumerateModules(pid)) {
        if (ToLower(module.name) == expected || ToLower(BasenameOf(module.path)) == expected) {
            return module.base;
        }
    }
    return 0;
}

static std::wstring TryGetMappedFileNameForAddress(HANDLE process, uint64_t address) {
    wchar_t buffer[MAX_PATH * 4]{};
    if (GetMappedFileNameW(process, reinterpret_cast<void*>(address), buffer, _countof(buffer)) == 0) {
        return {};
    }
    return buffer;
}

struct PeSectionInfo {
    std::string name;
    uint32_t virtual_address = 0;
    uint32_t virtual_size = 0;
    uint32_t raw_offset = 0;
    uint32_t raw_size = 0;
    uint32_t characteristics = 0;
};

struct PeImageLayoutInfo {
    std::vector<PeSectionInfo> sections;
    uint32_t exception_rva = 0;
    uint32_t exception_size = 0;
};

static bool ParsePeSections(const std::vector<uint8_t>& file_bytes, std::vector<PeSectionInfo>& sections) {
    if (file_bytes.size() < sizeof(IMAGE_DOS_HEADER)) {
        return false;
    }
    const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(file_bytes.data());
    if (dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew <= 0) {
        return false;
    }
    const size_t nt_offset = static_cast<size_t>(dos->e_lfanew);
    if (nt_offset + sizeof(IMAGE_NT_HEADERS64) > file_bytes.size()) {
        return false;
    }
    const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS64*>(file_bytes.data() + nt_offset);
    if (nt->Signature != IMAGE_NT_SIGNATURE || nt->OptionalHeader.Magic != IMAGE_NT_OPTIONAL_HDR64_MAGIC) {
        return false;
    }

    const size_t section_offset = nt_offset + sizeof(uint32_t) + sizeof(IMAGE_FILE_HEADER) + nt->FileHeader.SizeOfOptionalHeader;
    const size_t section_bytes = static_cast<size_t>(nt->FileHeader.NumberOfSections) * sizeof(IMAGE_SECTION_HEADER);
    if (section_offset + section_bytes > file_bytes.size()) {
        return false;
    }

    const auto* section_headers = reinterpret_cast<const IMAGE_SECTION_HEADER*>(file_bytes.data() + section_offset);
    for (uint16_t i = 0; i < nt->FileHeader.NumberOfSections; ++i) {
        PeSectionInfo section;
        char name[9]{};
        memcpy(name, section_headers[i].Name, 8);
        section.name = name;
        section.virtual_address = section_headers[i].VirtualAddress;
        section.virtual_size = section_headers[i].Misc.VirtualSize;
        section.raw_offset = section_headers[i].PointerToRawData;
        section.raw_size = section_headers[i].SizeOfRawData;
        section.characteristics = section_headers[i].Characteristics;
        sections.push_back(section);
    }
    return true;
}

static bool ParsePeImageLayout(const std::vector<uint8_t>& file_bytes, PeImageLayoutInfo& layout) {
    if (file_bytes.size() < sizeof(IMAGE_DOS_HEADER)) {
        return false;
    }
    const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(file_bytes.data());
    if (dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew <= 0) {
        return false;
    }
    const size_t nt_offset = static_cast<size_t>(dos->e_lfanew);
    if (nt_offset + sizeof(IMAGE_NT_HEADERS64) > file_bytes.size()) {
        return false;
    }
    const auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS64*>(file_bytes.data() + nt_offset);
    if (nt->Signature != IMAGE_NT_SIGNATURE || nt->OptionalHeader.Magic != IMAGE_NT_OPTIONAL_HDR64_MAGIC) {
        return false;
    }

    layout.exception_rva = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXCEPTION].VirtualAddress;
    layout.exception_size = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXCEPTION].Size;
    return ParsePeSections(file_bytes, layout.sections);
}

static std::wstring WideFromAscii(const std::string& value) {
    std::wstring out;
    out.reserve(value.size());
    for (unsigned char ch : value) {
        out.push_back(static_cast<wchar_t>(ch));
    }
    return out;
}

static std::wstring SanitizeDumpName(std::wstring value) {
    for (auto& ch : value) {
        if (ch < 32 ||
            ch == L'<' || ch == L'>' || ch == L':' || ch == L'"' ||
            ch == L'/' || ch == L'\\' || ch == L'|' || ch == L'?' || ch == L'*') {
            ch = L'_';
        }
    }
    while (!value.empty() && (value.back() == L' ' || value.back() == L'.')) {
        value.pop_back();
    }
    return value.empty() ? L"artifact" : value;
}

static void WriteLocalZeroPadding(std::ofstream& output, uint64_t size) {
    constexpr size_t kChunkSize = 64 * 1024;
    static const std::vector<char> zeroes(kChunkSize, 0);
    uint64_t written = 0;
    while (written < size) {
        const size_t chunk = static_cast<size_t>(std::min<uint64_t>(zeroes.size(), size - written));
        output.write(zeroes.data(), static_cast<std::streamsize>(chunk));
        written += chunk;
    }
}

static bool DumpProcessRangeBasic(HANDLE process, std::ofstream& output, uint64_t base, uint64_t size,
    uint64_t& bytes_from_process) {
    constexpr size_t kChunkSize = 64 * 1024;
    std::vector<char> buffer(kChunkSize);
    uint64_t total = 0;
    while (total < size) {
        const uint64_t address = base + total;
        MEMORY_BASIC_INFORMATION mbi{};
        uint64_t region_remaining = size - total;
        if (VirtualQueryEx(process, reinterpret_cast<void*>(address), &mbi, sizeof(mbi)) == sizeof(mbi) &&
            mbi.RegionSize != 0) {
            const uint64_t region_base = reinterpret_cast<uint64_t>(mbi.BaseAddress);
            const uint64_t region_end = region_base + static_cast<uint64_t>(mbi.RegionSize);
            if (region_end > address) {
                region_remaining = std::min<uint64_t>(region_remaining, region_end - address);
            }
        }

        const SIZE_T to_read = static_cast<SIZE_T>(std::min<uint64_t>(buffer.size(), region_remaining));
        SIZE_T bytes_read = 0;
        const BOOL read_ok = ReadProcessMemory(
            process,
            reinterpret_cast<void*>(address),
            buffer.data(),
            to_read,
            &bytes_read);
        if (!read_ok || bytes_read == 0) {
            WriteLocalZeroPadding(output, to_read);
            total += to_read;
            continue;
        }

        output.write(buffer.data(), static_cast<std::streamsize>(bytes_read));
        bytes_from_process += bytes_read;
        total += bytes_read;
        if (bytes_read < to_read) {
            WriteLocalZeroPadding(output, to_read - bytes_read);
            total += to_read - bytes_read;
        }
    }
    return bytes_from_process != 0;
}

struct ModifiedSectionDumpInfo {
    std::wstring path;
    std::wstring section_name;
    uint64_t section_rva = 0;
    uint64_t dump_base = 0;
    uint64_t dump_size = 0;
    uint64_t first_patch_rva = 0;
    uint64_t last_patch_rva = 0;
    uint64_t patch_count = 0;
};

static bool SectionContainsRva(const PeSectionInfo& section, uint64_t rva) {
    const uint64_t start = section.virtual_address;
    const uint64_t size = std::max<uint32_t>(section.virtual_size, section.raw_size);
    return size != 0 && rva >= start && rva < start + size;
}

static std::vector<ModifiedSectionDumpInfo> DumpModifiedSections(HANDLE process, const fs::path& dump_dir,
    const ModuleInfo& module, const ModuleIntegrityInfo& integrity) {
    std::vector<ModifiedSectionDumpInfo> result;
    if (!module.base || !module.size || integrity.patches.empty() || module.path.empty()) {
        return result;
    }

    std::vector<uint8_t> file_bytes;
    if (!ReadFileBytes(module.path, file_bytes)) {
        return result;
    }
    std::vector<PeSectionInfo> sections;
    if (!ParsePeSections(file_bytes, sections)) {
        return result;
    }

    fs::create_directories(dump_dir);

    for (const auto& section : sections) {
        uint64_t first_patch = UINT64_MAX;
        uint64_t last_patch = 0;
        uint64_t patch_count = 0;
        for (const auto& patch : integrity.patches) {
            if (!SectionContainsRva(section, patch.rva)) {
                continue;
            }
            first_patch = std::min<uint64_t>(first_patch, patch.rva);
            last_patch = std::max<uint64_t>(last_patch, patch.rva);
            ++patch_count;
        }
        if (patch_count == 0) {
            continue;
        }

        const uint64_t section_rva = section.virtual_address;
        const uint64_t section_size = std::min<uint64_t>(
            std::max<uint32_t>(section.virtual_size, section.raw_size),
            module.size > section_rva ? module.size - section_rva : 0);
        if (section_size == 0) {
            continue;
        }

        constexpr uint64_t kMaxModifiedSectionDump = 16ull * 1024ull * 1024ull;
        const uint64_t dump_size = std::min<uint64_t>(section_size, kMaxModifiedSectionDump);
        const std::wstring section_name = SanitizeDumpName(WideFromAscii(section.name.empty() ? "section" : section.name));

        std::wostringstream name;
        name << L"modified_section_"
            << std::hex << std::uppercase << module.base << L"."
            << SanitizeDumpName(BasenameOf(module.name)) << L"."
            << section_name << L"_rva_"
            << section_rva << L".bin";
        const fs::path section_path = dump_dir / name.str();

        std::ofstream output(section_path, std::ios::binary | std::ios::trunc);
        if (!output) {
            continue;
        }

        uint64_t bytes_from_process = 0;
        DumpProcessRangeBasic(process, output, module.base + section_rva, dump_size, bytes_from_process);
        output.close();
        if (bytes_from_process == 0) {
            std::error_code ignored;
            fs::remove(section_path, ignored);
            continue;
        }

        const fs::path tag_path = section_path.wstring() + L".tag";
        std::ofstream tag(tag_path, std::ios::out | std::ios::trunc);
        if (tag) {
            tag << "modified_section=true\n"
                << "module=" << WideToUtf8(module.name) << "\n"
                << "section=" << section.name << "\n"
                << "section_rva=0x" << std::hex << std::uppercase << section_rva << "\n"
                << "first_patch_rva=0x" << first_patch << "\n"
                << "last_patch_rva=0x" << last_patch << "\n"
                << "patch_count=" << std::dec << patch_count << "\n";
            for (const auto& patch : integrity.patches) {
                if (!SectionContainsRva(section, patch.rva)) {
                    continue;
                }
                tag << std::hex << std::uppercase << patch.rva << ";memory="
                    << std::setw(2) << std::setfill('0') << static_cast<unsigned int>(patch.memory_byte)
                    << " disk=" << std::setw(2) << std::setfill('0') << static_cast<unsigned int>(patch.disk_byte)
                    << " kind=" << (patch.unwind_metadata ? "unwind" : "code")
                    << "\n";
            }
        }

        const fs::path meta_path = section_path.wstring() + L".json";
        std::ofstream meta(meta_path, std::ios::out | std::ios::trunc);
        if (meta) {
            meta << "{"
                << "\"type\":\"modified_section\","
                << "\"modified\":true,"
                << "\"module_name\":" << JsonString(module.name) << ","
                << "\"module_path\":" << JsonString(module.path) << ","
                << "\"module_base\":\"" << Hex64(module.base) << "\","
                << "\"section_name\":" << JsonString(WideFromAscii(section.name)) << ","
                << "\"section_rva\":\"" << Hex64(section_rva) << "\","
                << "\"dump_base\":\"" << Hex64(module.base + section_rva) << "\","
                << "\"dump_size\":" << dump_size << ","
                << "\"first_patch_rva\":\"" << Hex64(first_patch) << "\","
                << "\"last_patch_rva\":\"" << Hex64(last_patch) << "\","
                << "\"patch_count\":" << patch_count
                << "}\n";
        }

        ModifiedSectionDumpInfo info;
        info.path = section_path.wstring();
        info.section_name = WideFromAscii(section.name);
        info.section_rva = section_rva;
        info.dump_base = module.base + section_rva;
        info.dump_size = dump_size;
        info.first_patch_rva = first_patch;
        info.last_patch_rva = last_patch;
        info.patch_count = patch_count;
        result.push_back(std::move(info));
    }

    return result;
}

static bool DumpModifiedModule(HANDLE process, const fs::path& dump_dir, const ModuleInfo& module,
    const ModuleIntegrityInfo& integrity, std::wstring& dump_path) {
    if (!module.base || !module.size) {
        return false;
    }
    fs::create_directories(dump_dir);

    std::wostringstream name;
    name << L"modified_module_" << std::hex << std::uppercase << module.base << L"."
        << BasenameOf(module.name);
    const fs::path module_dump_path = dump_dir / name.str();

    std::ofstream output(module_dump_path, std::ios::binary | std::ios::trunc);
    if (!output) {
        return false;
    }

    constexpr size_t kChunkSize = 64 * 1024;
    std::vector<char> buffer(kChunkSize);
    uint64_t total = 0;
    while (total < module.size) {
        const SIZE_T to_read = static_cast<SIZE_T>(std::min<uint64_t>(buffer.size(), module.size - total));
        SIZE_T bytes_read = 0;
        if (!ReadProcessMemory(process, reinterpret_cast<void*>(module.base + total), buffer.data(), to_read, &bytes_read) || bytes_read == 0) {
            break;
        }
        output.write(buffer.data(), static_cast<std::streamsize>(bytes_read));
        total += bytes_read;
    }

    const auto section_dumps = DumpModifiedSections(process, dump_dir, module, integrity);

    const fs::path tag_path = module_dump_path.wstring() + L".tag";
    std::ofstream tag(tag_path, std::ios::out | std::ios::trunc);
    if (tag) {
        tag << "modified_module=true\n"
            << "module=" << WideToUtf8(module.name) << "\n"
            << "module_base=0x" << std::hex << std::uppercase << module.base << "\n"
            << "modified_bytes=" << std::dec << integrity.modified_bytes << "\n"
            << "executable_modified_bytes=" << integrity.executable_modified_bytes << "\n"
            << "unwind_modified_bytes=" << integrity.unwind_modified_bytes << "\n";
        for (const auto& section_dump : section_dumps) {
            tag << "modified_section_dump=" << WideToUtf8(section_dump.path) << "\n";
        }
        for (const auto& patch : integrity.patches) {
            tag << std::hex << std::uppercase << patch.rva << ";memory="
                << std::setw(2) << std::setfill('0') << static_cast<unsigned int>(patch.memory_byte)
                << " disk=" << std::setw(2) << std::setfill('0') << static_cast<unsigned int>(patch.disk_byte)
                << " kind=" << (patch.unwind_metadata ? "unwind" : "code")
                << "\n";
        }
    }

    const fs::path meta_path = module_dump_path.wstring() + L".json";
    std::ofstream meta(meta_path, std::ios::out | std::ios::trunc);
    if (meta) {
        meta << "{"
            << "\"type\":\"modified_module\","
            << "\"modified\":true,"
            << "\"module_name\":" << JsonString(module.name) << ","
            << "\"module_path\":" << JsonString(module.path) << ","
            << "\"module_base\":\"" << Hex64(module.base) << "\","
            << "\"module_size\":" << module.size << ","
            << "\"modified_bytes\":" << integrity.modified_bytes << ","
            << "\"executable_modified_bytes\":" << integrity.executable_modified_bytes << ","
            << "\"unwind_modified_bytes\":" << integrity.unwind_modified_bytes << ","
            << "\"section_dumps\":[";
        for (size_t i = 0; i < section_dumps.size(); ++i) {
            if (i) {
                meta << ",";
            }
            const auto& section = section_dumps[i];
            meta << "{"
                << "\"path\":" << JsonString(section.path) << ","
                << "\"section_name\":" << JsonString(section.section_name) << ","
                << "\"section_rva\":\"" << Hex64(section.section_rva) << "\","
                << "\"dump_base\":\"" << Hex64(section.dump_base) << "\","
                << "\"dump_size\":" << section.dump_size << ","
                << "\"first_patch_rva\":\"" << Hex64(section.first_patch_rva) << "\","
                << "\"last_patch_rva\":\"" << Hex64(section.last_patch_rva) << "\","
                << "\"patch_count\":" << section.patch_count
                << "}";
        }
        meta << "]}\n";
    }

    dump_path = module_dump_path.wstring();
    return total > 0;
}

static bool IsNetworkModuleArtifact(const Rules& rules, const std::wstring& module_name) {
    if (IsNetworkModule(rules, module_name)) {
        return true;
    }

    static const std::vector<std::wstring> extra_network_artifact_modules{
        L"rasapi32.dll",
        L"rasman.dll",
        L"rasadhlp.dll",
        L"fwpuclnt.dll",
        L"nsi.dll"
    };
    return ContainsInsensitive(extra_network_artifact_modules, module_name);
}

static fs::path ModifiedModuleDumpDirectory(const RunState& state, const ModuleInfo& module) {
    return CurrentOutputDirectory(state) /
        (IsNetworkModuleArtifact(state.rules, module.name) ? L"modified_network_modules" : L"modified_modules");
}

static fs::path ModifiedModuleDumpDirectory(const RunState& state, const ProcessState& process_state, const ModuleInfo& module) {
    return process_state.out_dir /
        (IsNetworkModuleArtifact(state.rules, module.name) ? L"modified_network_modules" : L"modified_modules");
}

static bool IsWindowsPath(const std::wstring& path);

static bool StackHasManagedRuntimeFrames(const std::vector<FrameInfo>& frames) {
    for (const auto& frame : frames) {
        if (frame.jit_managed ||
            IsManagedModuleName(frame.module_name) ||
            IsManagedModuleName(frame.summary_name)) {
            return true;
        }
    }
    return false;
}

static bool ModuleListHasManagedRuntime(const std::vector<ModuleInfo>& modules) {
    for (const auto& module : modules) {
        if (IsManagedModuleName(module.name)) {
            return true;
        }
    }
    return false;
}

static bool IsManagedRuntimeIntegrityNoiseModule(const ModuleInfo& module, bool managed_runtime_present,
    const ModuleIntegrityInfo& integrity) {
    if (!managed_runtime_present || integrity.unwind_modified) {
        return false;
    }

    const std::wstring lower = ToLower(BasenameOf(module.name));
    if (IsManagedModuleName(lower)) {
        return true;
    }
    if (!IsWindowsPath(module.path)) {
        return false;
    }

    return lower == L"winhttp.dll" ||
        lower == L"wininet.dll" ||
        lower == L"ws2_32.dll" ||
        lower == L"dnsapi.dll" ||
        lower == L"iphlpapi.dll" ||
        lower == L"rasapi32.dll" ||
        lower == L"rasman.dll" ||
        lower == L"sechost.dll" ||
        lower == L"combase.dll";
}

static bool IsLowSignalSystemImagePatch(const ModuleInfo& module, const ModuleIntegrityInfo& integrity) {
    return !integrity.unwind_modified &&
        integrity.modified_bytes > 0 &&
        integrity.modified_bytes <= 64 &&
        IsWindowsPath(module.path);
}

static bool IsCommonWindowsHotpatchNoise(const ModuleInfo& module, const ModuleIntegrityInfo& integrity) {
    if (integrity.unwind_modified ||
        integrity.modified_bytes > 64 ||
        !IsWindowsPath(module.path)) {
        return false;
    }

    const std::wstring lower = ToLower(BasenameOf(module.name));
    return lower == L"winhttp.dll" ||
        lower == L"rasapi32.dll" ||
        lower == L"rasman.dll" ||
        lower == L"sechost.dll" ||
        lower == L"combase.dll";
}

static ModuleIntegrityInfo AnalyzeModuleIntegrity(HANDLE process, const ModuleInfo& module) {
    ModuleIntegrityInfo info;
    info.scanned = true;
    info.module_base = module.base;
    info.module_name = module.name;
    info.module_path = module.path;

    std::vector<uint8_t> file_bytes;
    if (module.path.empty() || !ReadFileBytes(module.path, file_bytes)) {
        info.scan_error = true;
        return info;
    }

    std::vector<PeSectionInfo> sections;
    if (!ParsePeSections(file_bytes, sections)) {
        info.scan_error = true;
        return info;
    }

    constexpr size_t kChunkSize = 64 * 1024;
    std::vector<uint8_t> remote(kChunkSize);
    for (const auto& section : sections) {
        std::string lower_name = section.name;
        std::transform(lower_name.begin(), lower_name.end(), lower_name.begin(), [](unsigned char ch) {
            return static_cast<char>(std::tolower(ch));
        });

        const bool executable_section = (section.characteristics & IMAGE_SCN_MEM_EXECUTE) != 0;
        const bool unwind_section = lower_name == ".pdata" || lower_name == ".xdata";
        if ((!executable_section && !unwind_section) ||
            section.raw_offset >= file_bytes.size() ||
            section.raw_size == 0) {
            continue;
        }

        const uint64_t comparable = std::min<uint64_t>({
            section.raw_size,
            section.virtual_size ? section.virtual_size : section.raw_size,
            file_bytes.size() - section.raw_offset
        });
        uint64_t offset = 0;
        while (offset < comparable) {
            const SIZE_T to_read = static_cast<SIZE_T>(std::min<uint64_t>(remote.size(), comparable - offset));
            SIZE_T bytes_read = 0;
            if (!ReadProcessMemory(process,
                reinterpret_cast<void*>(module.base + section.virtual_address + offset),
                remote.data(), to_read, &bytes_read) || bytes_read == 0) {
                info.scan_error = true;
                break;
            }

            const uint8_t* disk = file_bytes.data() + section.raw_offset + offset;
            for (SIZE_T i = 0; i < bytes_read; ++i) {
                if (remote[i] == disk[i]) {
                    continue;
                }
                ++info.modified_bytes;
                if (executable_section) {
                    ++info.executable_modified_bytes;
                }
                if (unwind_section) {
                    ++info.unwind_modified_bytes;
                }
                if (info.patches.size() < 128) {
                    ModulePatchRecord patch;
                    patch.rva = section.virtual_address + offset + i;
                    patch.memory_byte = remote[i];
                    patch.disk_byte = disk[i];
                    patch.unwind_metadata = unwind_section && !executable_section;
                    info.patches.push_back(patch);
                }
            }
            offset += bytes_read;
        }
    }

    info.executable_modified = info.executable_modified_bytes > 0;
    info.unwind_modified = info.unwind_modified_bytes > 0;
    info.modified = info.modified_bytes > 0;
    return info;
}

static bool RvaToFileOffset(const std::vector<PeSectionInfo>& sections, uint64_t rva, uint64_t& file_offset) {
    for (const auto& section : sections) {
        const uint64_t virtual_size = std::max<uint32_t>(section.virtual_size, section.raw_size);
        const uint64_t start = section.virtual_address;
        const uint64_t end = start + virtual_size;
        if (rva < start || rva >= end) {
            continue;
        }
        const uint64_t delta = rva - start;
        if (delta >= section.raw_size) {
            return false;
        }
        file_offset = section.raw_offset + delta;
        return true;
    }
    return false;
}

static void ApplyCapturedContextIntegrity(RunState& state, const MonitorEvent& event, std::vector<FrameInfo>& frames) {
    if (!state.rules.module_integrity_enabled) {
        return;
    }

    const uint32_t count = std::min<uint32_t>({
        event.frame_count,
        static_cast<uint32_t>(frames.size()),
        kMonitorMaxFrames
    });

    for (uint32_t i = 0; i < count; ++i) {
        auto& frame = frames[i];
        const uint8_t context_size = event.frame_context_size[i];
        if (context_size == 0 ||
            frame.monitor_frame ||
            frame.module_base == 0 ||
            frame.type != MEM_IMAGE ||
            frame.module_path.empty() ||
            event.frames[i] < context_size) {
            continue;
        }

        std::vector<uint8_t> file_bytes;
        if (!ReadFileBytes(frame.module_path, file_bytes)) {
            continue;
        }
        std::vector<PeSectionInfo> sections;
        if (!ParsePeSections(file_bytes, sections)) {
            continue;
        }

        const uint64_t context_start = event.frames[i] - context_size;
        uint64_t modified = 0;
        for (uint8_t j = 0; j < context_size; ++j) {
            const uint64_t address = context_start + j;
            if (address < frame.module_base) {
                continue;
            }
            const uint64_t rva = address - frame.module_base;
            uint64_t file_offset = 0;
            if (!RvaToFileOffset(sections, rva, file_offset) || file_offset >= file_bytes.size()) {
                continue;
            }
            if (event.frame_context[i][j] != file_bytes[static_cast<size_t>(file_offset)]) {
                ++modified;
            }
        }

        if (modified == 0) {
            continue;
        }

        frame.captured_context_modified = true;
        frame.captured_context_modified_bytes = modified;
        frame.module_modified = true;
        frame.module_modified_bytes = std::max<uint64_t>(frame.module_modified_bytes, modified);
        if (!IsModuleIntegrityAllowed(state.rules, frame.module_name)) {
            frame.backed_modified = true;
            frame.suspicious = true;
            frame.summary_name = L"BackedModified";
            frame.symbol_label = frame.module_name + L"!captured-modified+" + HexRvaWide(frame.module_offset);
        }
    }
}

static uint64_t CalculateAllocationSize(HANDLE process, uint64_t allocation_base) {
    if (allocation_base == 0) {
        return 0;
    }

    uint64_t cursor = allocation_base;
    uint64_t end = allocation_base;
    constexpr uint64_t kMaxAllocationWalk = 1024ull * 1024ull * 1024ull;

    while (cursor >= allocation_base && cursor - allocation_base < kMaxAllocationWalk) {
        MEMORY_BASIC_INFORMATION mbi{};
        if (VirtualQueryEx(process, reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)) != sizeof(mbi)) {
            break;
        }
        if (reinterpret_cast<uint64_t>(mbi.AllocationBase) != allocation_base) {
            break;
        }

        const uint64_t region_base = reinterpret_cast<uint64_t>(mbi.BaseAddress);
        const uint64_t region_end = region_base + static_cast<uint64_t>(mbi.RegionSize);
        end = std::max(end, region_end);
        if (region_end <= cursor) {
            break;
        }
        cursor = region_end;
    }

    return end > allocation_base ? end - allocation_base : 0;
}

static FrameInfo ClassifyFrame(HANDLE process, const std::vector<ModuleInfo>& modules, uint64_t address) {
    FrameInfo frame;
    frame.address = address;
    frame.summary_name = L"Unknown";
    frame.symbol_label = Hex64Wide(address);

    MEMORY_BASIC_INFORMATION mbi{};
    if (address != 0 && VirtualQueryEx(process, reinterpret_cast<void*>(address), &mbi, sizeof(mbi)) == sizeof(mbi)) {
        frame.allocation_base = reinterpret_cast<uint64_t>(mbi.AllocationBase);
        frame.region_base = reinterpret_cast<uint64_t>(mbi.BaseAddress);
        frame.region_size = static_cast<uint64_t>(mbi.RegionSize);
        frame.state = mbi.State;
        frame.protect = mbi.Protect;
        frame.allocation_protect = mbi.AllocationProtect;
        frame.type = mbi.Type;
        frame.executable = mbi.State == MEM_COMMIT && IsExecutableProtect(mbi.Protect);
        frame.allocation_size = CalculateAllocationSize(process, frame.allocation_base);
    }

    if (const ModuleInfo* module = FindModuleForAddress(modules, address)) {
        frame.module_base = module->base;
        frame.module_offset = address - module->base;
        frame.module_name = module->name;
        frame.module_path = module->path;
        frame.summary_name = ToLower(module->name);
        frame.symbol_label = module->name + L"+" + HexRvaWide(frame.module_offset);
        frame.monitor_frame = EqualsInsensitive(module->name, L"CallstackMonitor.dll");
        frame.jit_managed = IsManagedModuleName(module->name);
    } else if (frame.type == MEM_IMAGE || frame.type == MEM_MAPPED) {
        frame.module_path = TryGetMappedFileNameForAddress(process, address);
        if (!frame.module_path.empty()) {
            frame.module_name = BasenameOf(frame.module_path);
            frame.summary_name = ToLower(frame.module_name);
            frame.symbol_label = frame.module_name + L"!" + Hex64Wide(address);
            frame.monitor_frame = EqualsInsensitive(frame.module_name, L"CallstackMonitor.dll");
            frame.jit_managed = IsManagedModuleName(frame.module_name);
        } else {
            frame.summary_name = frame.type == MEM_IMAGE ? L"Image" : L"Mapped";
        }
    }

    if (frame.executable &&
        (frame.type == MEM_PRIVATE || (frame.type == MEM_MAPPED && frame.module_path.empty()))) {
        frame.suspicious = true;
        frame.unbacked_executable = true;
        frame.summary_name = L"Unbacked";
        frame.symbol_label = L"Unbacked!" + Hex64Wide(address);
    }

    return frame;
}

enum class CallsiteKind {
    Unknown,
    PlausibleCall,
    TailJump,
    MissingCall
};

static CallsiteKind InspectReturnAddressCallsite(HANDLE process, uint64_t return_address) {
    constexpr size_t kCallsiteWindowBytes = 32;
    if (return_address < kCallsiteWindowBytes) {
        return CallsiteKind::Unknown;
    }

    std::array<uint8_t, kCallsiteWindowBytes> bytes{};
    SIZE_T bytes_read = 0;
    if (!ReadProcessMemory(process, reinterpret_cast<void*>(return_address - bytes.size()),
        bytes.data(), bytes.size(), &bytes_read) || bytes_read != bytes.size()) {
        return CallsiteKind::Unknown;
    }

    ZydisDecodedInstruction instruction{};
    ZydisDecodedOperand operands[ZYDIS_MAX_OPERAND_COUNT]{};
    if (!ZydisDecodeInstructionEndingAt(
        bytes.data(),
        static_cast<size_t>(bytes_read),
        return_address - bytes.size(),
        static_cast<size_t>(bytes_read),
        instruction,
        operands)) {
        return CallsiteKind::Unknown;
    }

    const ZydisBranchKind kind = ZydisBranchKindOf(instruction);
    if (kind == ZydisBranchKind::Call) {
        return CallsiteKind::PlausibleCall;
    }
    if (kind == ZydisBranchKind::Jump) {
        return CallsiteKind::TailJump;
    }
    return CallsiteKind::MissingCall;
}

static void ApplyCallsiteValidation(RunState& state, std::vector<FrameInfo>& frames) {
    if (!state.rules.callsite_validation) {
        return;
    }

    for (size_t i = 0; i < frames.size(); ++i) {
        auto& frame = frames[i];
        if (frame.address == 0 || frame.monitor_frame || frame.type != MEM_IMAGE) {
            continue;
        }
        const CallsiteKind kind = InspectReturnAddressCallsite(state.process, frame.address);
        if (kind == CallsiteKind::MissingCall) {
            frame.return_address_without_call = true;
        } else if (kind == CallsiteKind::TailJump) {
            frame.tail_call_proxy = true;
        }
    }
}

static std::wstring BuildStackSummary(const std::vector<FrameInfo>& frames) {
    std::wstring summary;
    for (const auto& frame : frames) {
        if (frame.address == 0 || frame.monitor_frame) {
            continue;
        }
        if (!summary.empty()) {
            summary += L"|";
        }
        summary += frame.summary_name;
    }
    return summary;
}

static void ApplyModuleIntegrity(RunState& state, const std::vector<ModuleInfo>& modules, std::vector<FrameInfo>& frames) {
    if (!state.rules.module_integrity_enabled) {
        return;
    }

    for (auto& frame : frames) {
        if (frame.monitor_frame || frame.module_base == 0 || frame.type != MEM_IMAGE) {
            continue;
        }
        const ModuleInfo* module = FindModuleForAddress(modules, frame.address);
        if (!module) {
            continue;
        }

        ProcessState* process_state = CurrentProcessState(state);
        auto& integrity_cache = process_state ? process_state->module_integrity_cache : state.module_integrity_cache;
        const uint64_t cache_key = module->base;
        auto cached = integrity_cache.find(cache_key);
        if (cached == integrity_cache.end()) {
            ModuleIntegrityInfo info = AnalyzeModuleIntegrity(
                state.process,
                *module);
            cached = integrity_cache.emplace(cache_key, std::move(info)).first;
        }

        ModuleIntegrityInfo& info = cached->second;
        if (!info.modified) {
            continue;
        }
        if (IsCommonWindowsHotpatchNoise(*module, info)) {
            continue;
        }
        if (IsManagedRuntimeIntegrityNoiseModule(*module, StackHasManagedRuntimeFrames(frames), info)) {
            continue;
        }
        if (IsLowSignalSystemImagePatch(*module, info)) {
            continue;
        }

        frame.module_modified = true;
        frame.module_modified_bytes = info.modified_bytes;
        frame.unwind_modified_bytes = info.unwind_modified_bytes;
        const bool allowed_module = IsModuleIntegrityAllowed(state.rules, frame.module_name);
        if (state.rules.unwind_integrity && info.unwind_modified) {
            if (info.dump_path.empty()) {
                DumpModifiedModule(state.process, ModifiedModuleDumpDirectory(state, *module), *module, info, info.dump_path);
            }
            frame.unwind_metadata_tampered = true;
            frame.suspicious = true;
            if (!info.executable_modified || allowed_module) {
                frame.summary_name = L"UnwindTampered";
                frame.symbol_label = frame.module_name + L"!unwind+" + HexRvaWide(frame.module_offset);
            }
        }
        if (info.executable_modified && !allowed_module) {
            if (info.dump_path.empty()) {
                DumpModifiedModule(state.process, ModifiedModuleDumpDirectory(state, *module), *module, info, info.dump_path);
            }
            frame.backed_modified = true;
            frame.suspicious = true;
            frame.summary_name = L"BackedModified";
            frame.symbol_label = frame.module_name + L"!modified+" + HexRvaWide(frame.module_offset);
        }
    }
}

static bool IsLikelyInsertedGadgetFrame(const RunState& state, const FrameInfo& frame, size_t index, const MonitorEvent& event) {
    if (event.event_type != kMonitorEventDllLoad ||
        index > 10 ||
        frame.module_name.empty() ||
        frame.monitor_frame ||
        frame.unbacked_executable ||
        frame.backed_modified ||
        frame.type != MEM_IMAGE) {
        return false;
    }

    if (IsModuleIntegrityAllowed(state.rules, frame.module_name) ||
        ContainsInsensitive(state.rules.sensitive_modules, frame.module_name) ||
        EqualsInsensitive(frame.module_name, state.main_module_name) ||
        EqualsInsensitive(frame.module_name, event.target_name)) {
        return false;
    }

    return true;
}

static void WriteZeroPadding(std::ofstream& output, uint64_t size) {
    constexpr size_t kChunkSize = 64 * 1024;
    static const std::vector<char> zeroes(kChunkSize, 0);
    uint64_t written = 0;
    while (written < size) {
        const size_t chunk = static_cast<size_t>(std::min<uint64_t>(zeroes.size(), size - written));
        output.write(zeroes.data(), static_cast<std::streamsize>(chunk));
        written += chunk;
    }
}

static bool CanAttemptRead(DWORD state, DWORD protect) {
    if (state != MEM_COMMIT) {
        return false;
    }
    const DWORD clean = protect & ~(PAGE_GUARD | PAGE_NOCACHE | PAGE_WRITECOMBINE);
    return (clean & PAGE_NOACCESS) == 0;
}

static bool DumpReadableRange(HANDLE process, std::ofstream& output, uint64_t base, uint64_t size,
    uint64_t& bytes_from_process) {
    constexpr size_t kChunkSize = 64 * 1024;
    std::vector<char> buffer(kChunkSize);
    uint64_t total = 0;
    const uint64_t initial_bytes_from_process = bytes_from_process;
    while (total < size) {
        const uint64_t address = base + total;
        MEMORY_BASIC_INFORMATION mbi{};
        uint64_t region_remaining = size - total;
        if (VirtualQueryEx(process, reinterpret_cast<void*>(address), &mbi, sizeof(mbi)) == sizeof(mbi) &&
            mbi.RegionSize != 0) {
            const uint64_t region_base = reinterpret_cast<uint64_t>(mbi.BaseAddress);
            const uint64_t region_end = region_base + static_cast<uint64_t>(mbi.RegionSize);
            if (region_end > address) {
                region_remaining = std::min<uint64_t>(region_remaining, region_end - address);
            }
        }

        const SIZE_T to_read = static_cast<SIZE_T>(std::min<uint64_t>(buffer.size(), region_remaining));
        DWORD restored_protect = 0;
        bool restore_guard = false;
        if (mbi.State == MEM_COMMIT && (mbi.Protect & PAGE_GUARD) != 0) {
            const DWORD no_guard = mbi.Protect & ~PAGE_GUARD;
            restore_guard = VirtualProtectEx(
                process,
                mbi.BaseAddress,
                mbi.RegionSize,
                no_guard,
                &restored_protect) != FALSE;
        }

        SIZE_T bytes_read = 0;
        const BOOL read_ok = ReadProcessMemory(process, reinterpret_cast<void*>(address),
            buffer.data(), to_read, &bytes_read);

        if (restore_guard) {
            DWORD ignored = 0;
            VirtualProtectEx(process, mbi.BaseAddress, mbi.RegionSize, restored_protect, &ignored);
        }

        if (!read_ok || bytes_read == 0) {
            WriteZeroPadding(output, to_read);
            total += to_read;
            continue;
        }
        output.write(buffer.data(), static_cast<std::streamsize>(bytes_read));
        bytes_from_process += bytes_read;
        total += bytes_read;
        if (bytes_read < to_read) {
            WriteZeroPadding(output, to_read - bytes_read);
            total += to_read - bytes_read;
        }
    }
    return bytes_from_process > initial_bytes_from_process;
}

static bool ValidatePeAtOffset(const std::vector<uint8_t>& bytes, size_t offset, uint64_t& carve_size) {
    carve_size = 0;
    if (offset + sizeof(IMAGE_DOS_HEADER) > bytes.size()) {
        return false;
    }
    const auto* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(bytes.data() + offset);
    if (dos->e_magic != IMAGE_DOS_SIGNATURE || dos->e_lfanew <= 0 || dos->e_lfanew > 0x100000) {
        return false;
    }

    const size_t nt_offset = offset + static_cast<size_t>(dos->e_lfanew);
    if (nt_offset + sizeof(uint32_t) + sizeof(IMAGE_FILE_HEADER) > bytes.size()) {
        return false;
    }
    const uint32_t signature = *reinterpret_cast<const uint32_t*>(bytes.data() + nt_offset);
    if (signature != IMAGE_NT_SIGNATURE) {
        return false;
    }

    const auto* file_header = reinterpret_cast<const IMAGE_FILE_HEADER*>(bytes.data() + nt_offset + sizeof(uint32_t));
    const size_t optional_offset = nt_offset + sizeof(uint32_t) + sizeof(IMAGE_FILE_HEADER);
    if (optional_offset + file_header->SizeOfOptionalHeader > bytes.size()) {
        return false;
    }
    if (file_header->NumberOfSections == 0 || file_header->NumberOfSections > 96) {
        return false;
    }

    const uint16_t magic = *reinterpret_cast<const uint16_t*>(bytes.data() + optional_offset);
    uint32_t size_of_image = 0;
    if (magic == IMAGE_NT_OPTIONAL_HDR64_MAGIC) {
        if (optional_offset + sizeof(IMAGE_OPTIONAL_HEADER64) > bytes.size()) {
            return false;
        }
        const auto* optional = reinterpret_cast<const IMAGE_OPTIONAL_HEADER64*>(bytes.data() + optional_offset);
        size_of_image = optional->SizeOfImage;
    } else if (magic == IMAGE_NT_OPTIONAL_HDR32_MAGIC) {
        if (optional_offset + sizeof(IMAGE_OPTIONAL_HEADER32) > bytes.size()) {
            return false;
        }
        const auto* optional = reinterpret_cast<const IMAGE_OPTIONAL_HEADER32*>(bytes.data() + optional_offset);
        size_of_image = optional->SizeOfImage;
    } else {
        return false;
    }

    const size_t section_offset = optional_offset + file_header->SizeOfOptionalHeader;
    const size_t section_bytes = static_cast<size_t>(file_header->NumberOfSections) * sizeof(IMAGE_SECTION_HEADER);
    if (section_offset + section_bytes > bytes.size()) {
        return false;
    }

    uint64_t raw_end = 0;
    const auto* sections = reinterpret_cast<const IMAGE_SECTION_HEADER*>(bytes.data() + section_offset);
    for (uint16_t i = 0; i < file_header->NumberOfSections; ++i) {
        raw_end = std::max<uint64_t>(raw_end, static_cast<uint64_t>(sections[i].PointerToRawData) + sections[i].SizeOfRawData);
    }

    const uint64_t image_size = size_of_image ? size_of_image : raw_end;
    carve_size = std::min<uint64_t>(std::max<uint64_t>(image_size, raw_end), bytes.size() - offset);
    return carve_size >= 0x400;
}

static std::vector<std::wstring> ExtractInterestingStrings(const std::vector<uint8_t>& bytes) {
    std::vector<std::wstring> strings;
    std::string current;
    auto flush = [&]() {
        if (current.size() >= 5) {
            std::string lower = current;
            std::transform(lower.begin(), lower.end(), lower.begin(), [](unsigned char ch) {
                return static_cast<char>(std::tolower(ch));
            });
            const bool interesting = lower.find("http") != std::string::npos ||
                lower.find(".dll") != std::string::npos ||
                lower.find("user-agent") != std::string::npos ||
                lower.find("powershell") != std::string::npos ||
                lower.find("cmd") != std::string::npos ||
                lower.find("wininet") != std::string::npos ||
                lower.find("winhttp") != std::string::npos ||
                lower.find("ws2_32") != std::string::npos;
            if (interesting && strings.size() < 32) {
                const int needed = MultiByteToWideChar(CP_UTF8, 0, current.data(), static_cast<int>(current.size()), nullptr, 0);
                if (needed > 0) {
                    std::wstring wide(static_cast<size_t>(needed), L'\0');
                    MultiByteToWideChar(CP_UTF8, 0, current.data(), static_cast<int>(current.size()), wide.data(), needed);
                    strings.push_back(wide);
                }
            }
        }
        current.clear();
    };

    for (uint8_t byte : bytes) {
        if (byte >= 0x20 && byte <= 0x7e) {
            if (current.size() < 256) {
                current.push_back(static_cast<char>(byte));
            }
        } else {
            flush();
        }
    }
    flush();
    return strings;
}

static DumpAnalysis AnalyzeDumpFile(const fs::path& dump_path, bool carve_embedded_pe) {
    DumpAnalysis analysis;
    std::vector<uint8_t> bytes;
    if (!ReadFileBytes(dump_path, bytes)) {
        return analysis;
    }

    analysis.analyzed = true;
    analysis.entropy = CalculateEntropy(bytes);
    analysis.sha256 = Sha256Hex(bytes);
    analysis.strings = ExtractInterestingStrings(bytes);

    for (size_t offset = 0; offset + 1 < bytes.size(); ++offset) {
        if (bytes[offset] != 'M' || bytes[offset + 1] != 'Z') {
            continue;
        }

        uint64_t carve_size = 0;
        if (!ValidatePeAtOffset(bytes, offset, carve_size)) {
            continue;
        }

        EmbeddedPeRecord record;
        record.offset = offset;
        record.carved_size = carve_size;
        if (carve_embedded_pe) {
            std::wostringstream name;
            name << L"embedded_pe_" << std::setw(3) << std::setfill(L'0') << analysis.embedded_pes.size()
                << L"_" << std::hex << std::uppercase << offset << L".bin";
            const fs::path carved_path = dump_path.parent_path() / name.str();
            std::ofstream output(carved_path, std::ios::binary | std::ios::trunc);
            if (output) {
                output.write(reinterpret_cast<const char*>(bytes.data() + offset), static_cast<std::streamsize>(carve_size));
                record.path = carved_path.wstring();
            }
        }
        analysis.embedded_pes.push_back(record);
        if (analysis.embedded_pes.size() >= 16) {
            break;
        }
    }
    return analysis;
}

static bool DumpAllocation(HANDLE process, const fs::path& dump_dir, size_t index, const FrameInfo& frame,
    uint64_t max_dump_bytes, bool analyze_dump, bool carve_embedded_pe, DumpRecord& record) {
    if (frame.allocation_base == 0 || frame.allocation_size == 0) {
        return false;
    }

    fs::create_directories(dump_dir);
    const uint64_t dump_size = std::min<uint64_t>(frame.allocation_size, max_dump_bytes);
    const bool truncated = dump_size < frame.allocation_size;

    std::wostringstream name;
    name << L"allocation_" << std::setw(3) << std::setfill(L'0') << index << L"_"
        << std::hex << std::uppercase << frame.allocation_base << L".bin";
    const fs::path dump_path = dump_dir / name.str();

    std::ofstream output(dump_path, std::ios::binary | std::ios::trunc);
    if (!output) {
        return false;
    }

    uint64_t cursor = frame.allocation_base;
    const uint64_t dump_end = frame.allocation_base + dump_size;
    uint64_t total_written = 0;
    uint64_t bytes_from_process = 0;

    while (cursor < dump_end) {
        MEMORY_BASIC_INFORMATION mbi{};
        if (VirtualQueryEx(process, reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)) != sizeof(mbi)) {
            break;
        }
        if (reinterpret_cast<uint64_t>(mbi.AllocationBase) != frame.allocation_base) {
            break;
        }

        const uint64_t region_base = reinterpret_cast<uint64_t>(mbi.BaseAddress);
        const uint64_t region_end = std::min<uint64_t>(region_base + static_cast<uint64_t>(mbi.RegionSize), dump_end);
        if (region_end <= cursor) {
            break;
        }

        if (region_base > cursor) {
            const uint64_t gap = std::min<uint64_t>(region_base - cursor, dump_end - cursor);
            WriteZeroPadding(output, gap);
            total_written += gap;
            cursor += gap;
            continue;
        }

        const uint64_t writable_size = region_end - cursor;
        if (CanAttemptRead(mbi.State, mbi.Protect)) {
            DumpReadableRange(process, output, cursor, writable_size, bytes_from_process);
        } else {
            WriteZeroPadding(output, writable_size);
        }
        total_written += writable_size;
        cursor = region_end;
    }

    if (total_written < dump_size) {
        WriteZeroPadding(output, dump_size - total_written);
        total_written = dump_size;
    }

    record.path = dump_path.wstring();
    record.base = frame.allocation_base;
    record.requested_size = frame.allocation_size;
    record.dumped_size = total_written;
    record.trigger_address = frame.address;
    record.trigger_region_base = frame.region_base;
    record.truncated = truncated;
    if (analyze_dump) {
        record.analysis = AnalyzeDumpFile(dump_path, carve_embedded_pe);
    }

    const fs::path meta_path = dump_path.wstring() + L".json";
    std::ofstream meta(meta_path, std::ios::out | std::ios::trunc);
    if (meta) {
        meta << "{"
            << "\"allocation_base\":\"" << Hex64(frame.allocation_base) << "\","
            << "\"allocation_size\":" << frame.allocation_size << ","
            << "\"trigger_address\":\"" << Hex64(frame.address) << "\","
            << "\"trigger_region_base\":\"" << Hex64(frame.region_base) << "\","
            << "\"trigger_region_size\":" << frame.region_size << ","
            << "\"dumped_size\":" << total_written << ","
            << "\"bytes_from_process\":" << bytes_from_process << ","
            << "\"truncated\":" << (truncated ? "true" : "false") << ","
            << "\"protect\":" << JsonString(ProtectToString(frame.protect)) << ","
            << "\"allocation_protect\":" << JsonString(ProtectToString(frame.allocation_protect)) << ","
            << "\"type\":" << JsonString(TypeToString(frame.type)) << ","
            << "\"analysis\":{"
            << "\"analyzed\":" << (record.analysis.analyzed ? "true" : "false") << ","
            << "\"sha256\":" << JsonString(record.analysis.sha256) << ","
            << "\"entropy\":" << std::fixed << std::setprecision(4) << record.analysis.entropy << ","
            << "\"embedded_pe_count\":" << record.analysis.embedded_pes.size() << ","
            << "\"strings\":" << JsonStringArray(record.analysis.strings)
            << "}"
            << "}\n";
    }

    return total_written > 0;
}

static std::wstring NormalizeMappedDevicePath(std::wstring path) {
    if (path.empty() || path.rfind(L"\\Device\\", 0) != 0) {
        return path;
    }

    wchar_t device_name[MAX_PATH * 2]{};
    for (wchar_t drive = L'A'; drive <= L'Z'; ++drive) {
        wchar_t drive_name[] = { drive, L':', L'\0' };
        if (QueryDosDeviceW(drive_name, device_name, _countof(device_name)) == 0) {
            continue;
        }
        const std::wstring device = device_name;
        if (device.empty() || path.rfind(device, 0) != 0) {
            continue;
        }
        return std::wstring(drive_name) + path.substr(device.size());
    }
    return path;
}

static const ModuleInfo* FindModuleForImageBase(const std::vector<ModuleInfo>& modules, uint64_t image_base) {
    for (const auto& module : modules) {
        if (module.base == image_base ||
            (image_base >= module.base && image_base < module.base + module.size)) {
            return &module;
        }
    }
    return nullptr;
}

static bool ReadRemoteBytes(HANDLE process, uint64_t address, size_t size, std::vector<uint8_t>& bytes) {
    bytes.assign(size, 0);
    if (size == 0) {
        return false;
    }
    SIZE_T bytes_read = 0;
    if (!ReadProcessMemory(process, reinterpret_cast<void*>(address), bytes.data(), size, &bytes_read) ||
        bytes_read == 0) {
        bytes.clear();
        return false;
    }
    bytes.resize(bytes_read);
    return true;
}

static bool RemoteRangeContainsMz(HANDLE process, uint64_t address, uint64_t size, uint64_t scan_limit,
    bool& starts_with_mz) {
    starts_with_mz = false;
    const size_t to_read = static_cast<size_t>(std::min<uint64_t>({ size, scan_limit, 64ull * 1024ull }));
    std::vector<uint8_t> bytes;
    if (!ReadRemoteBytes(process, address, to_read, bytes)) {
        return false;
    }
    if (bytes.size() >= 2 && bytes[0] == 'M' && bytes[1] == 'Z') {
        starts_with_mz = true;
        return true;
    }
    for (size_t i = 1; i + 1 < bytes.size(); ++i) {
        if (bytes[i] == 'M' && bytes[i + 1] == 'Z') {
            return true;
        }
    }
    return false;
}

static std::wstring SectionNameForRva(const std::vector<PeSectionInfo>& sections, uint64_t rva) {
    for (const auto& section : sections) {
        const uint64_t virtual_size = std::max<uint32_t>(section.virtual_size, section.raw_size);
        const uint64_t start = section.virtual_address;
        const uint64_t end = start + virtual_size;
        if (rva >= start && rva < end) {
            return WideFromAscii(section.name);
        }
    }
    return L"";
}

static bool ReadRemotePeExceptionDirectory(HANDLE process, uint64_t module_base, uint32_t& exception_rva, uint32_t& exception_size) {
    exception_rva = 0;
    exception_size = 0;
    IMAGE_DOS_HEADER dos{};
    SIZE_T bytes_read = 0;
    if (!ReadProcessMemory(process, reinterpret_cast<void*>(module_base), &dos, sizeof(dos), &bytes_read) ||
        bytes_read != sizeof(dos) ||
        dos.e_magic != IMAGE_DOS_SIGNATURE ||
        dos.e_lfanew <= 0) {
        return false;
    }

    IMAGE_NT_HEADERS64 nt{};
    bytes_read = 0;
    if (!ReadProcessMemory(process, reinterpret_cast<void*>(module_base + static_cast<uint32_t>(dos.e_lfanew)),
        &nt, sizeof(nt), &bytes_read) ||
        bytes_read < offsetof(IMAGE_NT_HEADERS64, OptionalHeader) + sizeof(IMAGE_OPTIONAL_HEADER64) ||
        nt.Signature != IMAGE_NT_SIGNATURE ||
        nt.OptionalHeader.Magic != IMAGE_NT_OPTIONAL_HDR64_MAGIC) {
        return false;
    }

    exception_rva = nt.OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXCEPTION].VirtualAddress;
    exception_size = nt.OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXCEPTION].Size;
    return true;
}

static bool ReadRuntimeFunctionEntriesFromFile(const std::vector<uint8_t>& file_bytes,
    const PeImageLayoutInfo& layout,
    std::vector<IMAGE_RUNTIME_FUNCTION_ENTRY>& entries) {
    entries.clear();
    if (layout.exception_rva == 0 || layout.exception_size < sizeof(IMAGE_RUNTIME_FUNCTION_ENTRY)) {
        return false;
    }
    uint64_t file_offset = 0;
    if (!RvaToFileOffset(layout.sections, layout.exception_rva, file_offset) ||
        file_offset >= file_bytes.size()) {
        return false;
    }

    const uint64_t available = std::min<uint64_t>(layout.exception_size, file_bytes.size() - file_offset);
    const uint64_t count = available / sizeof(IMAGE_RUNTIME_FUNCTION_ENTRY);
    if (count == 0) {
        return false;
    }
    entries.resize(static_cast<size_t>(count));
    memcpy(entries.data(), file_bytes.data() + file_offset, entries.size() * sizeof(entries[0]));
    return true;
}

static bool ReadRuntimeFunctionEntriesFromRemote(HANDLE process,
    uint64_t module_base,
    uint32_t exception_rva,
    uint32_t exception_size,
    std::vector<IMAGE_RUNTIME_FUNCTION_ENTRY>& entries) {
    entries.clear();
    if (exception_rva == 0 || exception_size < sizeof(IMAGE_RUNTIME_FUNCTION_ENTRY)) {
        return false;
    }
    constexpr uint32_t kMaxRuntimeFunctionEntries = 16384;
    const uint32_t count = std::min<uint32_t>(
        exception_size / sizeof(IMAGE_RUNTIME_FUNCTION_ENTRY),
        kMaxRuntimeFunctionEntries);
    if (count == 0) {
        return false;
    }
    entries.resize(count);
    SIZE_T bytes_read = 0;
    if (!ReadProcessMemory(process,
        reinterpret_cast<void*>(module_base + exception_rva),
        entries.data(),
        entries.size() * sizeof(entries[0]),
        &bytes_read) ||
        bytes_read < sizeof(entries[0])) {
        entries.clear();
        return false;
    }
    entries.resize(bytes_read / sizeof(entries[0]));
    return !entries.empty();
}

static std::wstring ByoudVisibleCallerLabel(const std::vector<FrameInfo>& frames) {
    for (const auto& frame : frames) {
        if (frame.monitor_frame || frame.address == 0) {
            continue;
        }
        if (!frame.symbol_label.empty()) {
            return frame.symbol_label;
        }
        if (!frame.summary_name.empty()) {
            return frame.summary_name + L"!" + Hex64Wide(frame.address);
        }
        return Hex64Wide(frame.address);
    }
    return L"";
}

static std::wstring ByoudTechniqueForRule(const std::wstring& rule) {
    if (rule == L"byoud_unwind_info_tampered") {
        return L"UNWIND_DATA_TAMPER";
    }
    if (rule == L"byoud_runtime_function_unwind_hijack") {
        return L"UNWIND_DATA_HIJACK";
    }
    if (rule == L"byoud_runtime_function_range_hijack") {
        return L"RT_FUNCTION_HIJACK";
    }
    if (rule == L"byoud_runtime_function_entry_injected") {
        return L"RT_FUNCTION_INJECT";
    }
    if (rule == L"byoud_dynamic_function_table_for_image_or_private_code") {
        return L"RTFI_JIT / dynamic runtime function table";
    }
    if (rule == L"byoud_unwind_section_protection_changed") {
        return L"unwind metadata protection change";
    }
    return L"BYOUD";
}

static std::wstring MakeByoudTraceKey(const ByoudTraceRecord& record) {
    std::wostringstream key;
    key << record.pid << L"|"
        << record.rule << L"|"
        << Hex64Wide(record.module_base) << L"|"
        << Hex64Wide(record.rva) << L"|"
        << Hex64Wide(record.address) << L"|"
        << record.section_name;
    return key.str();
}

static bool AddByoudTraceRecord(RunState& state, ProcessState& process_state, ByoudTraceRecord record) {
    record.pid = record.pid ? record.pid : process_state.pid;
    record.technique = record.technique.empty() ? ByoudTechniqueForRule(record.rule) : record.technique;
    const std::wstring key = MakeByoudTraceKey(record);
    if (!process_state.byoud_trace_keys.insert(key).second) {
        return false;
    }

    ++state.byoud_trace_total;
    ++process_state.byoud_trace_total;
    if (record.alert) {
        ++state.byoud_alerts_total;
        ++process_state.byoud_alerts_total;
    }
    state.byoud_trace_records.push_back(record);
    process_state.byoud_trace_records.push_back(std::move(record));
    return true;
}

struct ByoudEvidenceSummary {
    bool present = false;
    int score = 0;
    std::vector<std::wstring> rules;
    std::vector<ByoudTraceRecord> event_records;
};

static void AddByoudRule(ByoudEvidenceSummary& summary, const std::wstring& rule, int score) {
    summary.present = true;
    summary.score = std::max(summary.score, score);
    if (std::find(summary.rules.begin(), summary.rules.end(), rule) == summary.rules.end()) {
        summary.rules.push_back(rule);
    }
}

static void AddByoudRecordAndRule(RunState& state, ProcessState& process_state,
    ByoudEvidenceSummary& summary, ByoudTraceRecord record) {
    AddByoudRule(summary, record.rule, record.score);
    if (AddByoudTraceRecord(state, process_state, record)) {
        summary.event_records.push_back(record);
    }
}

static bool FrameListHasManagedRuntime(const std::vector<FrameInfo>& frames) {
    for (const auto& frame : frames) {
        if (frame.jit_managed || IsManagedModuleName(frame.module_name) || IsManagedModuleName(frame.summary_name)) {
            return true;
        }
    }
    return false;
}

static bool IsByoudRuleName(const std::wstring& name) {
    return name == L"byoud_unwind_info_tampered" ||
        name == L"byoud_runtime_function_unwind_hijack" ||
        name == L"byoud_runtime_function_range_hijack" ||
        name == L"byoud_runtime_function_entry_injected" ||
        name == L"byoud_dynamic_function_table_for_image_or_private_code" ||
        name == L"byoud_unwind_section_protection_changed";
}

static std::wstring ByoudSectionForRuleName(const std::wstring& rule) {
    if (rule == L"byoud_unwind_info_tampered") {
        return L".xdata/.rdata";
    }
    if (rule == L"byoud_runtime_function_unwind_hijack" ||
        rule == L"byoud_runtime_function_range_hijack" ||
        rule == L"byoud_runtime_function_entry_injected") {
        return L".pdata";
    }
    if (rule == L"byoud_dynamic_function_table_for_image_or_private_code") {
        return L"dynamic-function-table";
    }
    return L"unwind-metadata";
}

static void CollectByoudMonitorSideEvidence(RunState& state, ProcessState& process_state,
    const std::vector<ModuleInfo>& modules, const MonitorEvent& event,
    const std::vector<FrameInfo>& frames, ByoudEvidenceSummary& summary) {
    if (event.event_type != kMonitorEventUnwindTable || !IsByoudRuleName(event.event_name)) {
        return;
    }

    const ModuleInfo* module = nullptr;
    if (event.callback_address != 0) {
        module = FindModuleForAddress(modules, event.callback_address);
    }
    if (!module && event.event_value != 0) {
        module = FindModuleForAddress(modules, event.event_value);
    }
    if (!module && event.target_name[0]) {
        for (const auto& candidate : modules) {
            if (EqualsInsensitive(candidate.name, event.target_name)) {
                module = &candidate;
                break;
            }
        }
    }

    ByoudTraceRecord record;
    record.event_index = state.events_total;
    record.pid = event.pid;
    record.tid = event.tid;
    record.alert = true;
    record.score = 90;
    record.rule = event.event_name;
    record.confidence = L"high";
    if (module) {
        record.module_name = module->name;
        record.module_path = module->path;
        record.module_base = module->base;
    }
    record.section_name = ByoudSectionForRuleName(record.rule);
    record.address = event.event_value;
    record.rva = module && event.event_value >= module->base ? event.event_value - module->base : 0;
    record.size = event.event_flags;
    record.api_name = L"LdrLoadDll";
    record.caller_label = ByoudVisibleCallerLabel(frames);
    if (record.rule == L"byoud_runtime_function_unwind_hijack") {
        record.detail = L"monitor-side temporal snapshot caught a RUNTIME_FUNCTION UnwindInfoAddress mismatch before the sensitive DLL load";
    } else if (record.rule == L"byoud_runtime_function_range_hijack") {
        record.detail = L"monitor-side temporal snapshot caught a RUNTIME_FUNCTION Begin/End range mismatch before the sensitive DLL load";
    } else if (record.rule == L"byoud_runtime_function_entry_injected") {
        record.detail = L"monitor-side temporal snapshot caught an injected/expanded PE exception directory before the sensitive DLL load";
    } else if (record.rule == L"byoud_unwind_info_tampered") {
        record.detail = L"monitor-side temporal snapshot caught UNWIND_INFO bytes that differ from disk before the sensitive DLL load";
    } else {
        record.detail = L"monitor-side temporal snapshot caught suspicious unwind metadata before the sensitive DLL load";
    }
    AddByoudRecordAndRule(state, process_state, summary, std::move(record));
}

static void CollectRecentByoudEvidenceForDllLoad(RunState& state, ProcessState& process_state,
    const MonitorEvent& event, ByoudEvidenceSummary& summary) {
    if (event.event_type != kMonitorEventDllLoad || process_state.byoud_trace_records.empty()) {
        return;
    }
    uint32_t copied = 0;
    for (auto it = process_state.byoud_trace_records.rbegin();
        it != process_state.byoud_trace_records.rend() && copied < 4; ++it) {
        if (!it->alert || state.events_total < it->event_index ||
            state.events_total - it->event_index > 4) {
            continue;
        }
        AddByoudRule(summary, it->rule, it->score);
        summary.event_records.push_back(*it);
        ++copied;
    }
}

static void CollectByoudSectionProtectionEvidence(RunState& state, ProcessState& process_state,
    const std::vector<ModuleInfo>& modules, const MonitorEvent& event,
    const std::vector<FrameInfo>& frames, ByoudEvidenceSummary& summary) {
    if (event.event_type != kMonitorEventMemoryApi ||
        !EqualsInsensitive(event.event_name, L"NtProtectVirtualMemory") ||
        event.event_value == 0) {
        return;
    }

    const ModuleInfo* module = FindModuleForAddress(modules, event.event_value);
    if (!module || module->path.empty()) {
        return;
    }
    if (IsManagedModuleName(module->name) && FrameListHasManagedRuntime(frames)) {
        return;
    }

    std::vector<uint8_t> file_bytes;
    if (!ReadFileBytes(module->path, file_bytes)) {
        return;
    }
    PeImageLayoutInfo layout;
    if (!ParsePeImageLayout(file_bytes, layout)) {
        return;
    }

    const uint64_t rva = event.event_value - module->base;
    const std::wstring section_name = SectionNameForRva(layout.sections, rva);
    const std::wstring lower_section = ToLower(section_name);
    const bool protected_unwind_section =
        lower_section == L".pdata" ||
        lower_section == L".xdata" ||
        lower_section == L".rdata" ||
        (layout.exception_rva != 0 &&
            rva >= layout.exception_rva &&
            rva < static_cast<uint64_t>(layout.exception_rva) + layout.exception_size);
    if (!protected_unwind_section) {
        return;
    }

    ByoudTraceRecord record;
    record.event_index = state.events_total;
    record.pid = event.pid;
    record.tid = event.tid;
    record.alert = true;
    record.score = 75;
    record.rule = L"byoud_unwind_section_protection_changed";
    record.confidence = L"medium";
    record.module_name = module->name;
    record.module_path = module->path;
    record.module_base = module->base;
    record.section_name = section_name;
    record.address = event.event_value;
    record.rva = rva;
    record.size = 0;
    record.api_name = event.event_name;
    record.caller_label = ByoudVisibleCallerLabel(frames);
    record.detail = L"memory protection changed inside PE unwind metadata (.pdata/.xdata/.rdata/exception directory)";
    AddByoudRecordAndRule(state, process_state, summary, std::move(record));
}

static void CollectByoudDynamicFunctionTableEvidence(RunState& state, ProcessState& process_state,
    const std::vector<ModuleInfo>& modules, const MonitorEvent& event,
    const std::vector<FrameInfo>& frames, ByoudEvidenceSummary& summary) {
    if (event.event_type != kMonitorEventUnwindTable) {
        return;
    }

    const bool add_table = EqualsInsensitive(event.event_name, L"RtlAddFunctionTable");
    const bool callback_table = EqualsInsensitive(event.event_name, L"RtlInstallFunctionTableCallback");
    if (!add_table && !callback_table) {
        return;
    }

    const uint64_t table = event.event_value;
    const uint64_t base = event.callback_address;
    FrameInfo table_frame = ClassifyFrame(state.process, modules, table);
    FrameInfo base_frame = ClassifyFrame(state.process, modules, base);
    if ((IsManagedModuleName(base_frame.module_name) || IsManagedModuleName(base_frame.summary_name)) &&
        FrameListHasManagedRuntime(frames)) {
        return;
    }
    const bool table_private = table_frame.type == MEM_PRIVATE ||
        (table_frame.type == MEM_MAPPED && table_frame.module_path.empty());
    const bool base_private_or_image = base_frame.type == MEM_PRIVATE ||
        base_frame.type == MEM_IMAGE ||
        (base_frame.type == MEM_MAPPED && base_frame.module_path.empty());
    if (!table_private && !base_private_or_image && !callback_table) {
        return;
    }

    ByoudTraceRecord record;
    record.event_index = state.events_total;
    record.pid = event.pid;
    record.tid = event.tid;
    record.alert = true;
    record.score = 85;
    record.rule = L"byoud_dynamic_function_table_for_image_or_private_code";
    record.confidence = L"high";
    record.module_name = base_frame.module_name;
    record.module_path = base_frame.module_path;
    record.module_base = base_frame.module_base;
    record.section_name = L"dynamic-function-table";
    record.address = table;
    record.rva = base_frame.module_base ? base - base_frame.module_base : 0;
    record.size = static_cast<uint64_t>(event.event_flags) * sizeof(IMAGE_RUNTIME_FUNCTION_ENTRY);
    record.api_name = event.event_name;
    record.old_value = base;
    record.new_value = table;
    record.caller_label = ByoudVisibleCallerLabel(frames);
    record.detail = L"dynamic runtime function table registered from process memory for image/private code";
    AddByoudRecordAndRule(state, process_state, summary, std::move(record));
}

static bool AddByoudModuleDiffRecord(RunState& state, ProcessState& process_state,
    ByoudEvidenceSummary& summary, const MonitorEvent& event, const std::vector<FrameInfo>& frames,
    const ModuleInfo& module, const std::wstring& rule, int score, const std::wstring& confidence,
    const std::wstring& section_name, uint64_t rva, uint64_t size,
    uint64_t old_value, uint64_t new_value, const std::wstring& detail) {
    ByoudTraceRecord record;
    record.event_index = state.events_total;
    record.pid = event.pid;
    record.tid = event.tid;
    record.alert = true;
    record.score = score;
    record.rule = rule;
    record.confidence = confidence;
    record.module_name = module.name;
    record.module_path = module.path;
    record.module_base = module.base;
    record.section_name = section_name;
    record.address = module.base + rva;
    record.rva = rva;
    record.size = size;
    record.old_value = old_value;
    record.new_value = new_value;
    record.api_name = event.event_name;
    record.dll_name = event.target_name;
    record.caller_label = ByoudVisibleCallerLabel(frames);
    record.detail = detail;
    const size_t before = summary.event_records.size();
    AddByoudRecordAndRule(state, process_state, summary, std::move(record));
    return summary.event_records.size() != before;
}

static void CollectByoudModuleIntegrityEvidence(RunState& state, ProcessState& process_state,
    const std::vector<ModuleInfo>& modules, const MonitorEvent& event,
    const std::vector<FrameInfo>& frames, ByoudEvidenceSummary& summary) {
    if (event.event_type != kMonitorEventDllLoad) {
        return;
    }

    size_t records_added = 0;
    for (const auto& module : modules) {
        if (module.base == 0 || module.path.empty() ||
            EqualsInsensitive(module.name, L"CallstackMonitor.dll")) {
            continue;
        }

        std::vector<uint8_t> file_bytes;
        if (!ReadFileBytes(module.path, file_bytes)) {
            continue;
        }
        PeImageLayoutInfo layout;
        if (!ParsePeImageLayout(file_bytes, layout) ||
            layout.exception_rva == 0 ||
            layout.exception_size < sizeof(IMAGE_RUNTIME_FUNCTION_ENTRY)) {
            continue;
        }

        uint32_t remote_exception_rva = 0;
        uint32_t remote_exception_size = 0;
        if (!ReadRemotePeExceptionDirectory(state.process, module.base, remote_exception_rva, remote_exception_size)) {
            continue;
        }

        std::vector<IMAGE_RUNTIME_FUNCTION_ENTRY> disk_entries;
        std::vector<IMAGE_RUNTIME_FUNCTION_ENTRY> remote_entries;
        if (!ReadRuntimeFunctionEntriesFromFile(file_bytes, layout, disk_entries) ||
            !ReadRuntimeFunctionEntriesFromRemote(state.process, module.base,
                remote_exception_rva, remote_exception_size, remote_entries)) {
            continue;
        }

        bool structural_recorded = false;
        if ((remote_exception_rva != layout.exception_rva || remote_exception_size > layout.exception_size) &&
            AddByoudModuleDiffRecord(state, process_state, summary, event, frames, module,
                L"byoud_runtime_function_entry_injected", 90, L"high", L".pdata",
                remote_exception_rva ? remote_exception_rva : layout.exception_rva,
                remote_exception_size,
                (static_cast<uint64_t>(layout.exception_rva) << 32) | layout.exception_size,
                (static_cast<uint64_t>(remote_exception_rva) << 32) | remote_exception_size,
                L"PE exception directory changed in memory; runtime function table size/RVA no longer matches disk")) {
            ++records_added;
            structural_recorded = true;
        }

        const size_t comparable = std::min(disk_entries.size(), remote_entries.size());
        bool range_recorded = false;
        bool unwind_recorded = false;
        bool info_recorded = false;
        constexpr size_t kMaxUnwindInfoChecksPerModule = 8192;
        for (size_t i = 0; i < comparable; ++i) {
            const auto& disk = disk_entries[i];
            const auto& remote = remote_entries[i];
            const uint64_t entry_rva = remote_exception_rva + i * sizeof(IMAGE_RUNTIME_FUNCTION_ENTRY);
            if (!range_recorded &&
                (disk.BeginAddress != remote.BeginAddress || disk.EndAddress != remote.EndAddress)) {
                if (AddByoudModuleDiffRecord(state, process_state, summary, event, frames, module,
                    L"byoud_runtime_function_range_hijack", 90, L"high", L".pdata",
                    entry_rva, sizeof(IMAGE_RUNTIME_FUNCTION_ENTRY),
                    (static_cast<uint64_t>(disk.BeginAddress) << 32) | disk.EndAddress,
                    (static_cast<uint64_t>(remote.BeginAddress) << 32) | remote.EndAddress,
                    L"RUNTIME_FUNCTION Begin/End range changed in memory; unwind entry now covers a different code range")) {
                    ++records_added;
                    structural_recorded = true;
                }
                range_recorded = true;
            }
            if (!unwind_recorded && disk.UnwindInfoAddress != remote.UnwindInfoAddress) {
                if (AddByoudModuleDiffRecord(state, process_state, summary, event, frames, module,
                    L"byoud_runtime_function_unwind_hijack", 90, L"high", L".pdata",
                    entry_rva, sizeof(IMAGE_RUNTIME_FUNCTION_ENTRY),
                    disk.UnwindInfoAddress,
                    remote.UnwindInfoAddress,
                    L"RUNTIME_FUNCTION UnwindInfoAddress changed in memory; stack walker is redirected to different unwind metadata")) {
                    ++records_added;
                    structural_recorded = true;
                }
                unwind_recorded = true;
            }

            if (!info_recorded && structural_recorded && i < kMaxUnwindInfoChecksPerModule && disk.UnwindInfoAddress != 0) {
                uint64_t file_offset = 0;
                if (RvaToFileOffset(layout.sections, disk.UnwindInfoAddress, file_offset) &&
                    file_offset < file_bytes.size()) {
                    std::array<uint8_t, 32> remote_info{};
                    SIZE_T bytes_read = 0;
                    const SIZE_T to_read = static_cast<SIZE_T>(
                        std::min<uint64_t>(remote_info.size(), file_bytes.size() - file_offset));
                    if (to_read > 0 &&
                        ReadProcessMemory(state.process,
                            reinterpret_cast<void*>(module.base + disk.UnwindInfoAddress),
                            remote_info.data(), to_read, &bytes_read) &&
                        bytes_read == to_read &&
                        memcmp(remote_info.data(), file_bytes.data() + file_offset, to_read) != 0) {
                        const std::wstring section = SectionNameForRva(layout.sections, disk.UnwindInfoAddress);
                        uint64_t old_value = 0;
                        uint64_t new_value = 0;
                        memcpy(&old_value, file_bytes.data() + file_offset, std::min<size_t>(sizeof(old_value), to_read));
                        memcpy(&new_value, remote_info.data(), std::min<size_t>(sizeof(new_value), to_read));
                        if (AddByoudModuleDiffRecord(state, process_state, summary, event, frames, module,
                            L"byoud_unwind_info_tampered", 90, L"high",
                            section.empty() ? L".xdata/.rdata" : section,
                            disk.UnwindInfoAddress, to_read, old_value, new_value,
                            L"UNWIND_INFO bytes differ from the on-disk image while a sensitive DLL load is in progress")) {
                            ++records_added;
                        }
                        info_recorded = true;
                    }
                }
            }

            if (range_recorded && unwind_recorded && info_recorded) {
                break;
            }
        }

        if (records_added >= 8) {
            break;
        }
    }
}

static ByoudEvidenceSummary CollectByoudEvidenceForEvent(RunState& state, ProcessState& process_state,
    const std::vector<ModuleInfo>& modules, const MonitorEvent& event,
    const std::vector<FrameInfo>& frames) {
    ByoudEvidenceSummary summary;
    if (!state.rules.byoud_trace) {
        return summary;
    }

    CollectByoudMonitorSideEvidence(state, process_state, modules, event, frames, summary);
    CollectByoudSectionProtectionEvidence(state, process_state, modules, event, frames, summary);
    CollectByoudDynamicFunctionTableEvidence(state, process_state, modules, event, frames, summary);
    CollectByoudModuleIntegrityEvidence(state, process_state, modules, event, frames, summary);
    CollectRecentByoudEvidenceForDllLoad(state, process_state, event, summary);
    return summary;
}

static bool RemoteHeaderDiffersFromDisk(HANDLE process, uint64_t image_base, const fs::path& disk_path,
    uint64_t& diff_count, bool& mz_missing) {
    diff_count = 0;
    mz_missing = false;

    std::vector<uint8_t> disk;
    if (disk_path.empty() || !ReadFileBytes(disk_path, disk) || disk.empty()) {
        return false;
    }

    const size_t header_size = static_cast<size_t>(std::min<uint64_t>(disk.size(), 4096));
    std::vector<uint8_t> remote;
    if (!ReadRemoteBytes(process, image_base, header_size, remote)) {
        return false;
    }
    if (remote.size() >= 2 && (remote[0] != 'M' || remote[1] != 'Z')) {
        mz_missing = true;
    }
    const size_t comparable = std::min(remote.size(), header_size);
    for (size_t i = 0; i < comparable; ++i) {
        if (remote[i] != disk[i]) {
            ++diff_count;
        }
    }
    return true;
}

static bool IsWindowsPath(const std::wstring& path) {
    const std::wstring lower = ToLower(path);
    return lower.rfind(L"c:\\windows\\", 0) == 0 ||
        lower.rfind(L"\\windows\\", 0) == 0 ||
        lower.find(L"\\windows\\system32\\") != std::wstring::npos ||
        lower.find(L"\\windows\\winsxs\\") != std::wstring::npos ||
        lower.find(L"\\windows\\syswow64\\") != std::wstring::npos ||
        lower.find(L"\\program files\\windowsapps\\microsoft.") != std::wstring::npos ||
        lower.find(L"\\program files\\windowsapps\\microsoft_") != std::wstring::npos ||
        lower.find(L"\\program files\\windowsapps\\microsoft\\") != std::wstring::npos;
}

static bool IsManagedSatelliteResourceImagePath(const std::wstring& path) {
    const std::wstring lower = ToLower(path);
    if (lower.size() < 4) {
        return false;
    }
    return lower.find(L"\\windows\\microsoft.net\\assembly\\") != std::wstring::npos &&
        lower.find(L".resources") != std::wstring::npos &&
        lower.rfind(L".dll") == lower.size() - 4;
}

static bool ShouldEscalateImageMutation(const ProcessState& process_state, const ModuleInfo* module) {
    if (!module) {
        return true;
    }
    if (EqualsInsensitive(module->name, process_state.main_module_name)) {
        return true;
    }
    return !IsWindowsPath(module->path);
}

struct WorkingSetPrivateStats {
    uint64_t pages = 0;
    uint64_t private_pages = 0;
};

static WorkingSetPrivateStats QueryPrivateWorkingSetPages(HANDLE process, uint64_t base, uint64_t size) {
    WorkingSetPrivateStats stats;
    SYSTEM_INFO system_info{};
    GetSystemInfo(&system_info);
    const uint64_t page_size = system_info.dwPageSize ? system_info.dwPageSize : 4096;
    if (size == 0) {
        return stats;
    }

    constexpr size_t kChunkPages = 4096;
    std::vector<PSAPI_WORKING_SET_EX_INFORMATION> entries;
    entries.reserve(kChunkPages);

    uint64_t cursor = base;
    const uint64_t end = base + size;
    while (cursor < end) {
        entries.clear();
        uint64_t chunk_cursor = cursor;
        while (chunk_cursor < end && entries.size() < kChunkPages) {
            PSAPI_WORKING_SET_EX_INFORMATION entry{};
            entry.VirtualAddress = reinterpret_cast<void*>(chunk_cursor);
            entries.push_back(entry);
            chunk_cursor += page_size;
        }
        if (!entries.empty() &&
            QueryWorkingSetEx(process, entries.data(),
                static_cast<DWORD>(entries.size() * sizeof(entries[0])))) {
            for (const auto& entry : entries) {
                ++stats.pages;
                if (entry.VirtualAttributes.Valid && !entry.VirtualAttributes.Shared) {
                    ++stats.private_pages;
                }
            }
        }
        if (chunk_cursor <= cursor) {
            break;
        }
        cursor = chunk_cursor;
    }

    return stats;
}

static bool DumpMemoryAuditRange(HANDLE process, const fs::path& audit_dir, size_t index,
    MemoryAuditFinding& finding, uint64_t max_dump_bytes) {
    const uint64_t dump_base = finding.region_base ? finding.region_base : finding.allocation_base;
    const uint64_t requested_size = finding.region_size ? finding.region_size : finding.allocation_size;
    if (!dump_base || !requested_size) {
        return false;
    }

    fs::create_directories(audit_dir);
    const uint64_t dump_size = std::min<uint64_t>(requested_size, max_dump_bytes);

    std::wostringstream name;
    name << L"audit_" << std::setw(3) << std::setfill(L'0') << index << L"_"
        << SanitizeDumpName(finding.rule) << L"_"
        << std::hex << std::uppercase << dump_base << L".bin";
    const fs::path dump_path = audit_dir / name.str();

    std::ofstream output(dump_path, std::ios::binary | std::ios::trunc);
    if (!output) {
        return false;
    }

    uint64_t bytes_from_process = 0;
    DumpProcessRangeBasic(process, output, dump_base, dump_size, bytes_from_process);
    output.close();
    if (bytes_from_process == 0) {
        std::error_code ignored;
        fs::remove(dump_path, ignored);
        return false;
    }

    const fs::path meta_path = dump_path.wstring() + L".json";
    std::ofstream meta(meta_path, std::ios::out | std::ios::trunc);
    if (meta) {
        meta << "{"
            << "\"type\":\"memory_audit_dump\","
            << "\"rule\":" << JsonString(finding.rule) << ","
            << "\"score\":" << finding.score << ","
            << "\"alert\":" << (finding.alert ? "true" : "false") << ","
            << "\"pid\":" << finding.pid << ","
            << "\"dump_base\":\"" << Hex64(dump_base) << "\","
            << "\"dump_size\":" << dump_size << ","
            << "\"bytes_from_process\":" << bytes_from_process << ","
            << "\"region_base\":\"" << Hex64(finding.region_base) << "\","
            << "\"region_size\":" << finding.region_size << ","
            << "\"allocation_base\":\"" << Hex64(finding.allocation_base) << "\","
            << "\"allocation_size\":" << finding.allocation_size << ","
            << "\"protect\":" << JsonString(ProtectToString(finding.protect)) << ","
            << "\"type_name\":" << JsonString(TypeToString(finding.type)) << ","
            << "\"module_name\":" << JsonString(finding.module_name) << ","
            << "\"module_path\":" << JsonString(finding.module_path) << ","
            << "\"mapped_path\":" << JsonString(finding.mapped_path) << ","
            << "\"detail\":" << JsonString(finding.detail)
            << "}\n";
    }

    finding.dumped = true;
    finding.dump_path = dump_path.wstring();
    return true;
}

static void AddMemoryAuditFinding(RunState& state, ProcessState& process_state, MemoryAuditFinding finding) {
    if (finding.event_index == 0) {
        finding.event_index = state.events_total;
    }
    finding.pid = process_state.pid;
    if (finding.confidence.empty()) {
        finding.confidence = finding.alert ? L"proof" : L"hunting";
    }

    if (finding.alert) {
        ++state.alerts_total;
        ++process_state.alerts_total;
        ++state.memory_audit_alerts_total;
        ++process_state.memory_audit_alerts_total;
    }
    ++state.memory_audit_findings_total;
    ++process_state.memory_audit_findings_total;
    ++state.decision_counts[finding.confidence];
    ++process_state.decision_counts[finding.confidence];

    state.memory_audit_findings.push_back(finding);
    process_state.memory_audit_findings.push_back(std::move(finding));
}

static TemporalImageState* FindTemporalImageStateForAddress(ProcessState& process_state, uint64_t address) {
    for (auto& [base, item] : process_state.temporal_image_states) {
        if (address >= item.module_base && address < item.module_base + item.module_size) {
            return &item;
        }
    }
    return nullptr;
}

static bool IsTemporalImageRule(const std::wstring& rule) {
    return rule == L"image_module_temporally_stomped" ||
        rule == L"image_module_restored_after_temporal_stomp" ||
        rule == L"modified_image_unmapped_after_temporal_stomp";
}

static bool IsTemporalImageAuditAllowedModule(const std::wstring& module_name) {
    const std::wstring lower = ToLower(BasenameOf(module_name));
    return lower == L"ntdll.dll" ||
        lower == L"kernel32.dll" ||
        lower == L"kernelbase.dll" ||
        lower == L"callstackmonitor.dll" ||
        lower == L"windhawk.dll" ||
        lower == L"ucrtbase.dll" ||
        lower == L"msvcrt.dll" ||
        lower == L"vcruntime140.dll" ||
        lower == L"vcruntime140_1.dll" ||
        lower == L"concrt140.dll" ||
        lower == L"mscoree.dll" ||
        lower == L"clr.dll" ||
        lower == L"clrjit.dll" ||
        lower == L"system.ni.dll" ||
        lower == L"mscorlib.ni.dll";
}

static bool IsLowSignalTemporalImagePatch(const std::wstring& module_name, const ModuleIntegrityInfo& integrity) {
    const std::wstring lower = ToLower(BasenameOf(module_name));
    const bool tiny_patch =
        integrity.modified_bytes <= 16 &&
        integrity.executable_modified_bytes <= 16 &&
        integrity.unwind_modified_bytes == 0;
    if (!tiny_patch) {
        return false;
    }

    return lower == L"combase.dll" ||
        lower == L"bcryptprimitives.dll" ||
        lower == L"shell32.dll" ||
        lower == L"gdi32.dll" ||
        lower == L"msctf.dll";
}

static bool IsLowSignalTemporalImageEvent(const std::wstring& module_name, const MonitorEvent& event) {
    if (!EqualsInsensitive(event.event_name, L"image_module_temporally_stomped")) {
        return false;
    }
    const std::wstring lower = ToLower(BasenameOf(module_name));
    const bool small_window = event.event_flags > 0 && event.event_flags <= 512;
    if (!small_window) {
        return false;
    }
    return lower == L"combase.dll" ||
        lower == L"bcryptprimitives.dll" ||
        lower == L"shell32.dll" ||
        lower == L"gdi32.dll" ||
        lower == L"msctf.dll";
}

static bool HasRecentTemporalImageEvidence(const ProcessState& process_state, uint64_t event_index) {
    constexpr uint64_t kTemporalCorrelationEvents = 12;
    for (auto it = process_state.memory_audit_findings.rbegin();
        it != process_state.memory_audit_findings.rend(); ++it) {
        if (!it->alert || !IsTemporalImageRule(it->rule) || it->event_index == 0) {
            continue;
        }
        if (event_index >= it->event_index && event_index - it->event_index <= kTemporalCorrelationEvents) {
            return true;
        }
        if (event_index > it->event_index + kTemporalCorrelationEvents) {
            break;
        }
    }
    return false;
}

static void AddTemporalImageFinding(RunState& state, ProcessState& process_state,
    const std::wstring& rule, const ModuleInfo& module, const MonitorEvent& event,
    const FrameInfo* event_value_frame, const std::wstring& detail,
    int score, const std::wstring& confidence, const std::wstring& dump_path = L"") {
    std::wostringstream key;
    key << rule << L"|" << std::hex << std::uppercase << module.base;
    if (!process_state.temporal_image_keys.insert(key.str()).second) {
        return;
    }

    MemoryAuditFinding finding;
    finding.event_index = state.events_total;
    finding.alert = true;
    finding.score = score;
    finding.rule = rule;
    finding.confidence = confidence;
    finding.module_name = module.name;
    finding.module_path = module.path;
    finding.address = event.event_value ? event.event_value : module.base;
    finding.region_base = event_value_frame ? event_value_frame->region_base : module.base;
    finding.region_size = event_value_frame ? event_value_frame->region_size : module.size;
    finding.allocation_base = event_value_frame ? event_value_frame->allocation_base : module.base;
    finding.allocation_size = event_value_frame ? event_value_frame->allocation_size : module.size;
    finding.state = event_value_frame ? event_value_frame->state : MEM_COMMIT;
    finding.protect = event_value_frame ? event_value_frame->protect : 0;
    finding.type = event_value_frame ? event_value_frame->type : MEM_IMAGE;
    finding.detail = detail;
    if (!dump_path.empty()) {
        finding.dumped = true;
        finding.dump_path = dump_path;
    }
    AddMemoryAuditFinding(state, process_state, std::move(finding));
}

static void CollectTemporalImageIntegrity(RunState& state, ProcessState& process_state,
    const std::vector<ModuleInfo>& modules, const MonitorEvent& event,
    const FrameInfo* event_value_frame) {
    if (!state.rules.memory_audit || event.event_type != kMonitorEventMemoryApi || event.event_value == 0) {
        return;
    }

    if (IsTemporalImageRule(event.event_name)) {
        ModuleInfo module{};
        const uint64_t module_hint = event.callback_address ? event.callback_address : event.event_value;
        if (const ModuleInfo* found = FindModuleForAddress(modules, module_hint)) {
            module = *found;
        } else {
            module.base = module_hint;
            module.size = event_value_frame && event_value_frame->allocation_size
                ? event_value_frame->allocation_size
                : event_value_frame ? event_value_frame->region_size : 0;
            module.path = event.target_name;
            module.name = BasenameOf(module.path);
        }
        if (module.name.empty()) {
            module.name = BasenameOf(event.target_name);
        }
        if (module.path.empty()) {
            module.path = event.target_name;
        }

        if (IsLowSignalTemporalImageEvent(module.name, event)) {
            return;
        }

        TemporalImageState& temporal = process_state.temporal_image_states[module.base];
        if (temporal.module_base == 0) {
            temporal.module_base = module.base;
            temporal.module_size = module.size;
            temporal.module_name = module.name;
            temporal.module_path = module.path;
        }

        int score = 90;
        std::wstring confidence = L"proof";
        std::wostringstream detail;
        if (EqualsInsensitive(event.event_name, L"image_module_temporally_stomped")) {
            temporal.dirty_seen = true;
            temporal.dirty_event_index = state.events_total;
            temporal.dirty_address = event.event_value ? event.event_value : module.base;
            temporal.dirty_modified_bytes = event.event_flags;
            detail << L"monitor-side temporal snapshot caught live image bytes diverging from disk before the target resumed";
            if (event.event_flags) {
                detail << L"; modified_bytes_in_window=" << event.event_flags;
            }
        } else if (EqualsInsensitive(event.event_name, L"image_module_restored_after_temporal_stomp")) {
            temporal.restored_seen = true;
            temporal.restored_event_index = state.events_total;
            confidence = L"high";
            detail << L"monitor-side temporal snapshot saw the image return to disk-clean bytes after a prior dirty state";
        } else {
            temporal.unmap_seen = true;
            confidence = L"high";
            score = 85;
            detail << L"image module previously observed modified was unmapped, consistent with remap/sleep-mask cleanup";
        }

        AddTemporalImageFinding(
            state,
            process_state,
            event.event_name,
            module,
            event,
            event_value_frame,
            detail.str(),
            score,
            confidence);
        return;
    }

    const bool interesting_api =
        EqualsInsensitive(event.event_name, L"NtProtectVirtualMemory") ||
        EqualsInsensitive(event.event_name, L"NtMapViewOfSection") ||
        EqualsInsensitive(event.event_name, L"NtUnmapViewOfSection") ||
        EqualsInsensitive(event.event_name, L"NtWriteVirtualMemory");
    if (!interesting_api) {
        return;
    }

    HANDLE process = process_state.handle ? process_state.handle : state.process;
    if (!process) {
        return;
    }

    const ModuleInfo* module = FindModuleForAddress(modules, event.event_value);
    if (!module) {
        if (EqualsInsensitive(event.event_name, L"NtUnmapViewOfSection")) {
            if (TemporalImageState* prior = FindTemporalImageStateForAddress(process_state, event.event_value)) {
                prior->unmap_seen = true;
            }
        }
        return;
    }
    if (module->path.empty() ||
        IsModuleIntegrityAllowed(state.rules, module->name) ||
        IsTemporalImageAuditAllowedModule(module->name)) {
        return;
    }

    TemporalImageState& temporal = process_state.temporal_image_states[module->base];
    if (temporal.module_base == 0) {
        temporal.module_base = module->base;
        temporal.module_size = module->size;
        temporal.module_name = module->name;
        temporal.module_path = module->path;
    }

    if (EqualsInsensitive(event.event_name, L"NtUnmapViewOfSection")) {
        temporal.unmap_seen = true;
        if (temporal.dirty_seen) {
            AddTemporalImageFinding(
                state,
                process_state,
                L"modified_image_unmapped_after_temporal_stomp",
                *module,
                event,
                event_value_frame,
                L"an image module previously observed modified was unmapped during the same run, matching sleep-mask/module-stomping cleanup behavior",
                85,
                L"high",
                temporal.dirty_dump_path);
        }
        return;
    }

    ModuleIntegrityInfo integrity = AnalyzeModuleIntegrity(process, *module);
    if (integrity.scan_error || !integrity.scanned) {
        return;
    }

    if (IsLowSignalTemporalImagePatch(module->name, integrity)) {
        return;
    }
    if (IsCommonWindowsHotpatchNoise(*module, integrity)) {
        return;
    }
    if (IsManagedRuntimeIntegrityNoiseModule(*module, ModuleListHasManagedRuntime(modules), integrity)) {
        return;
    }

    if (integrity.executable_modified || integrity.unwind_modified) {
        temporal.dirty_seen = true;
        temporal.dirty_event_index = state.events_total;
        temporal.dirty_address = !integrity.patches.empty()
            ? module->base + integrity.patches.front().rva
            : (event.event_value ? event.event_value : module->base);
        temporal.dirty_modified_bytes = integrity.modified_bytes;
        std::wstring dump_path;
        if (state.rules.dump_suspicious_regions) {
            DumpModifiedModule(process, ModifiedModuleDumpDirectory(state, process_state, *module), *module, integrity, dump_path);
            temporal.dirty_dump_path = dump_path;
        }

        std::wostringstream detail;
        detail << L"live memory API event " << event.event_name
            << L" observed executable/unwind bytes in " << module->name
            << L" diverging from disk; modified_bytes=" << integrity.modified_bytes
            << L" exec_modified=" << integrity.executable_modified_bytes
            << L" unwind_modified=" << integrity.unwind_modified_bytes;
        AddTemporalImageFinding(
            state,
            process_state,
            L"image_module_temporally_stomped",
            *module,
            event,
            event_value_frame,
            detail.str(),
            90,
            L"proof",
            dump_path);
        return;
    }

    if (temporal.dirty_seen && !temporal.restored_seen) {
        temporal.restored_seen = true;
        temporal.restored_event_index = state.events_total;
        std::wstring rule = L"image_module_restored_after_temporal_stomp";
        std::wstring detail = L"module bytes now match disk after the same module was observed modified earlier; this is consistent with temporal stomp cleanup/sleep masking";
        if (temporal.unmap_seen || EqualsInsensitive(event.event_name, L"NtMapViewOfSection")) {
            detail = L"module bytes match disk after prior dirty state and map/unmap activity at the same image base, consistent with clean remap sleep masking";
        }
        AddTemporalImageFinding(
            state,
            process_state,
            rule,
            *module,
            event,
            event_value_frame,
            detail,
            90,
            L"high",
            temporal.dirty_dump_path);
    }
}

static bool IsLikelyManagedRuntimePresent(const std::vector<ModuleInfo>& modules) {
    for (const auto& module : modules) {
        if (IsManagedModuleName(module.name)) {
            return true;
        }
    }
    return false;
}

static void AuditExecutableNonImageRegion(RunState& state, ProcessState& process_state, HANDLE process,
    const MEMORY_BASIC_INFORMATION& mbi, bool managed_runtime_present) {
    const uint64_t region_base = reinterpret_cast<uint64_t>(mbi.BaseAddress);
    const uint64_t region_size = static_cast<uint64_t>(mbi.RegionSize);
    const uint64_t allocation_base = reinterpret_cast<uint64_t>(mbi.AllocationBase);
    if (region_base == 0 || region_size == 0 || !IsExecutableProtect(mbi.Protect)) {
        return;
    }

    bool starts_with_mz = false;
    const bool contains_mz = RemoteRangeContainsMz(process, region_base, region_size, 64ull * 1024ull, starts_with_mz);
    const bool rwx = (mbi.Protect & ~(PAGE_GUARD | PAGE_NOCACHE | PAGE_WRITECOMBINE)) == PAGE_EXECUTE_READWRITE;

    MemoryAuditFinding finding;
    finding.address = region_base;
    finding.region_base = region_base;
    finding.region_size = region_size;
    finding.allocation_base = allocation_base;
    finding.allocation_size = CalculateAllocationSize(process, allocation_base);
    finding.state = mbi.State;
    finding.protect = mbi.Protect;
    finding.type = mbi.Type;

    if (contains_mz) {
        finding.alert = true;
        finding.score = starts_with_mz ? 90 : 85;
        finding.rule = starts_with_mz ? L"private_executable_pe_image" : L"private_executable_region_contains_pe_header";
        finding.confidence = L"proof";
        finding.detail = starts_with_mz
            ? L"executable private/mapped memory begins with an MZ header"
            : L"executable private/mapped memory contains an embedded MZ header near the region start";
    } else if (mbi.Type == MEM_MAPPED && TryGetMappedFileNameForAddress(process, region_base).empty()) {
        finding.alert = true;
        finding.score = 75;
        finding.rule = L"mapped_executable_region_without_file_name";
        finding.confidence = L"strong_correlation";
        finding.detail = L"executable MEM_MAPPED region has no queryable mapped file name";
    } else if (rwx && !managed_runtime_present) {
        finding.alert = false;
        finding.score = 50;
        finding.rule = L"private_executable_rwx_region";
        finding.confidence = L"hunting";
        finding.detail = L"RWX executable private memory was observed; kept as hunting context unless PE content or a stronger owner anomaly is present";
    } else {
        finding.alert = false;
        finding.score = 35;
        finding.rule = L"private_or_mapped_executable_region";
        finding.confidence = L"hunting";
        finding.detail = managed_runtime_present
            ? L"executable private/mapped memory observed while a managed runtime is present"
            : L"executable private/mapped memory observed without a PE signature";
    }

    if (finding.alert) {
        DumpMemoryAuditRange(process, process_state.out_dir / L"memory_audit",
            process_state.memory_audit_findings.size(), finding, state.rules.max_dump_bytes);
    }
    AddMemoryAuditFinding(state, process_state, std::move(finding));
}

static void AuditImageRegion(RunState& state, ProcessState& process_state, HANDLE process,
    const std::vector<ModuleInfo>& modules, uint64_t image_base) {
    MEMORY_BASIC_INFORMATION base_mbi{};
    if (VirtualQueryEx(process, reinterpret_cast<void*>(image_base), &base_mbi, sizeof(base_mbi)) != sizeof(base_mbi) ||
        base_mbi.State != MEM_COMMIT ||
        base_mbi.Type != MEM_IMAGE) {
        return;
    }

    const ModuleInfo* module = FindModuleForImageBase(modules, image_base);
    const uint64_t image_size = module && module->size ? module->size : CalculateAllocationSize(process, image_base);
    const std::wstring mapped_path_raw = TryGetMappedFileNameForAddress(process, image_base);
    const std::wstring mapped_path = NormalizeMappedDevicePath(mapped_path_raw);
    const std::wstring mapped_basename = BasenameOf(mapped_path.empty() ? mapped_path_raw : mapped_path);
    if ((module && EqualsInsensitive(module->name, L"CallstackMonitor.dll")) ||
        EqualsInsensitive(mapped_basename, L"CallstackMonitor.dll")) {
        return;
    }
    const bool allowed_module = module && IsModuleIntegrityAllowed(state.rules, module->name);
    const bool escalate_image_mutation = ShouldEscalateImageMutation(process_state, module);
    if (!module && IsManagedSatelliteResourceImagePath(mapped_path.empty() ? mapped_path_raw : mapped_path)) {
        return;
    }

    auto base_finding = [&](std::wstring rule, int score, bool alert, std::wstring detail) {
        MemoryAuditFinding finding;
        finding.alert = alert;
        finding.score = score;
        finding.rule = std::move(rule);
        finding.confidence = alert ? L"proof" : L"hunting";
        finding.detail = std::move(detail);
        finding.address = image_base;
        finding.region_base = image_base;
        finding.region_size = image_size;
        finding.allocation_base = image_base;
        finding.allocation_size = image_size;
        finding.state = base_mbi.State;
        finding.protect = base_mbi.Protect;
        finding.type = base_mbi.Type;
        if (module) {
            finding.module_name = module->name;
            finding.module_path = module->path;
        }
        finding.mapped_path = mapped_path.empty() ? mapped_path_raw : mapped_path;
        return finding;
    };

    if (!module) {
        const bool loaderless_windows_image = IsWindowsPath(mapped_path.empty() ? mapped_path_raw : mapped_path);
        auto finding = base_finding(L"image_missing_peb_loader_entry",
            loaderless_windows_image ? 45 : 85,
            !loaderless_windows_image,
            loaderless_windows_image
                ? L"MEM_IMAGE allocation is present without a loader entry but is backed by a Windows image; reported as context"
                : L"MEM_IMAGE allocation is present but no matching module exists in the loader/module list");
        AddMemoryAuditFinding(state, process_state, std::move(finding));
    }

    if (mapped_path_raw.empty()) {
        auto finding = base_finding(L"image_mapped_file_name_unavailable", 75, true,
            L"MEM_IMAGE allocation has no queryable mapped file name");
        AddMemoryAuditFinding(state, process_state, std::move(finding));
    } else if (module && !module->path.empty() &&
        !EqualsInsensitive(BasenameOf(mapped_path), BasenameOf(module->path))) {
        auto finding = base_finding(L"image_peb_path_mismatch", 75, true,
            L"PEB module path/name does not match the mapped file object name");
        AddMemoryAuditFinding(state, process_state, std::move(finding));
    }

    if (module && !allowed_module) {
        uint64_t header_diff = 0;
        bool mz_missing = false;
        if (RemoteHeaderDiffersFromDisk(process, image_base, module->path, header_diff, mz_missing) &&
            (mz_missing || header_diff > 32)) {
            auto finding = base_finding(mz_missing ? L"image_header_mz_missing_or_wiped" : L"image_header_modified",
                mz_missing ? 85 : 65,
                mz_missing && escalate_image_mutation,
                mz_missing
                    ? L"image header no longer starts with MZ"
                    : L"image header differs from disk; reported as context unless the PE header is wiped");
            finding.private_pages = header_diff;
            AddMemoryAuditFinding(state, process_state, std::move(finding));
        }

        auto& integrity_cache = process_state.module_integrity_cache;
        auto cached = integrity_cache.find(module->base);
        if (escalate_image_mutation && cached == integrity_cache.end()) {
            cached = integrity_cache.emplace(module->base, AnalyzeModuleIntegrity(process, *module)).first;
        }
        if (escalate_image_mutation && cached != integrity_cache.end() && cached->second.executable_modified &&
            !IsLowSignalSystemImagePatch(*module, cached->second)) {
            ModuleIntegrityInfo& integrity = cached->second;
            if (integrity.dump_path.empty()) {
                DumpModifiedModule(process, ModifiedModuleDumpDirectory(state, process_state, *module), *module, integrity, integrity.dump_path);
            }
            auto finding = base_finding(L"image_executable_section_modified", 85, true,
                L"executable image bytes differ from the backing file on disk");
            finding.private_pages = integrity.modified_bytes;
            finding.executable_private_pages = integrity.executable_modified_bytes;
            finding.dumped = !integrity.dump_path.empty();
            finding.dump_path = integrity.dump_path;
            AddMemoryAuditFinding(state, process_state, std::move(finding));
        }
    }

    std::vector<uint8_t> file_bytes;
    std::vector<PeSectionInfo> sections;
    if (module && !module->path.empty() && ReadFileBytes(module->path, file_bytes)) {
        ParsePeSections(file_bytes, sections);
    }

    if (!sections.empty() && escalate_image_mutation) {
        std::set<uint64_t> reported_section_permission_regions;
        for (const auto& section : sections) {
            if ((section.characteristics & IMAGE_SCN_MEM_EXECUTE) != 0) {
                continue;
            }
            const uint64_t section_size = std::max<uint32_t>(section.virtual_size, section.raw_size);
            if (section_size == 0) {
                continue;
            }
            const uint64_t section_address = image_base + section.virtual_address;
            MEMORY_BASIC_INFORMATION section_mbi{};
            if (VirtualQueryEx(process, reinterpret_cast<void*>(section_address), &section_mbi, sizeof(section_mbi)) != sizeof(section_mbi) ||
                section_mbi.State != MEM_COMMIT ||
                !IsExecutableProtect(section_mbi.Protect)) {
                continue;
            }
            const uint64_t section_region_base = reinterpret_cast<uint64_t>(section_mbi.BaseAddress);
            if (!reported_section_permission_regions.insert(section_region_base).second) {
                continue;
            }
            MemoryAuditFinding finding = base_finding(L"image_section_permission_mismatch", 75, true,
                L"non-executable PE section is executable in memory");
            finding.address = section_address;
            finding.region_base = section_region_base;
            finding.region_size = static_cast<uint64_t>(section_mbi.RegionSize);
            finding.protect = section_mbi.Protect;
            AddMemoryAuditFinding(state, process_state, std::move(finding));
        }
    }

    uint64_t cursor = image_base;
    const uint64_t end = image_base + image_size;
    while (cursor < end) {
        MEMORY_BASIC_INFORMATION mbi{};
        if (VirtualQueryEx(process, reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)) != sizeof(mbi)) {
            break;
        }
        const uint64_t region_base = reinterpret_cast<uint64_t>(mbi.BaseAddress);
        const uint64_t region_size = static_cast<uint64_t>(mbi.RegionSize);
        const uint64_t region_end = region_base + region_size;
        if (region_end <= cursor) {
            break;
        }

        const bool executable_region = mbi.State == MEM_COMMIT && IsExecutableProtect(mbi.Protect);
        if (executable_region) {
            const auto stats = QueryPrivateWorkingSetPages(process, region_base, region_size);
            if (stats.private_pages > 0 && !allowed_module) {
                const bool alert_private_image = escalate_image_mutation &&
                    (stats.private_pages >= 2 || EqualsInsensitive(module ? module->name : L"", process_state.main_module_name));
                MemoryAuditFinding finding = base_finding(L"image_private_executable_pages", 80, true,
                    L"executable MEM_IMAGE pages are private, indicating copy-on-write modifications");
                finding.alert = alert_private_image;
                finding.score = alert_private_image ? 80 : 45;
                finding.confidence = alert_private_image ? L"proof" : L"hunting";
                if (!alert_private_image) {
                    finding.detail = L"executable MEM_IMAGE pages are private; reported as hunting context for Windows/allowlisted image noise control";
                }
                finding.address = region_base;
                finding.region_base = region_base;
                finding.region_size = region_size;
                finding.protect = mbi.Protect;
                finding.private_pages = stats.private_pages;
                finding.executable_private_pages = stats.private_pages;
                AddMemoryAuditFinding(state, process_state, std::move(finding));
            }

            if (!sections.empty()) {
                const uint64_t rva = region_base >= image_base ? region_base - image_base : 0;
                for (const auto& section : sections) {
                    if (!SectionContainsRva(section, rva)) {
                        continue;
                    }
                    if ((section.characteristics & IMAGE_SCN_MEM_EXECUTE) == 0 && !allowed_module) {
                        MemoryAuditFinding finding = base_finding(L"image_section_permission_mismatch", 75, true,
                            L"non-executable PE section is executable in memory");
                        finding.address = region_base;
                        finding.region_base = region_base;
                        finding.region_size = region_size;
                        finding.protect = mbi.Protect;
                        AddMemoryAuditFinding(state, process_state, std::move(finding));
                    }
                    break;
                }
            }
        }
        cursor = region_end;
    }
}

static void RunMemoryAudit(RunState& state) {
    if (!state.rules.memory_audit) {
        return;
    }

    std::lock_guard<std::mutex> lock(state.event_mutex);
    for (auto& item : state.processes) {
        ProcessState& process_state = item.second;
        if (process_state.memory_audit_completed || !process_state.handle) {
            continue;
        }

        DWORD exit_code = 0;
        if (!GetExitCodeProcess(process_state.handle, &exit_code) || exit_code != STILL_ACTIVE) {
            continue;
        }

        process_state.memory_audit_completed = true;
        const std::vector<ModuleInfo> modules = EnumerateModules(process_state.pid);
        const bool managed_runtime_present = IsLikelyManagedRuntimePresent(modules);

        std::set<uint64_t> audited_images;
        std::set<uint64_t> audited_non_image_allocations;
        uint64_t cursor = 0;
        constexpr uint64_t kUserModeCeiling = 0x0000800000000000ull;
        while (cursor < kUserModeCeiling) {
            MEMORY_BASIC_INFORMATION mbi{};
            if (VirtualQueryEx(process_state.handle, reinterpret_cast<void*>(cursor), &mbi, sizeof(mbi)) != sizeof(mbi)) {
                break;
            }
            const uint64_t region_base = reinterpret_cast<uint64_t>(mbi.BaseAddress);
            const uint64_t region_size = static_cast<uint64_t>(mbi.RegionSize);
            const uint64_t region_end = region_base + region_size;
            if (region_end <= cursor) {
                break;
            }

            if (mbi.State == MEM_COMMIT) {
                const uint64_t allocation_base = reinterpret_cast<uint64_t>(mbi.AllocationBase);
                if (mbi.Type == MEM_IMAGE && allocation_base != 0) {
                    if (audited_images.insert(allocation_base).second) {
                        AuditImageRegion(state, process_state, process_state.handle, modules, allocation_base);
                    }
                } else if ((mbi.Type == MEM_PRIVATE || mbi.Type == MEM_MAPPED) &&
                    IsExecutableProtect(mbi.Protect) &&
                    allocation_base != 0 &&
                    audited_non_image_allocations.insert(allocation_base).second) {
                    AuditExecutableNonImageRegion(state, process_state, process_state.handle, mbi, managed_runtime_present);
                }
            }
            cursor = region_end;
        }
    }
}

static void WriteFrameJson(std::ofstream& output, const FrameInfo& frame) {
    output
        << "{"
        << "\"address\":\"" << Hex64(frame.address) << "\","
        << "\"label\":" << JsonString(frame.symbol_label) << ","
        << "\"summary_name\":" << JsonString(frame.summary_name) << ","
        << "\"state\":" << JsonString(StateToString(frame.state)) << ","
        << "\"protect\":" << JsonString(ProtectToString(frame.protect)) << ","
        << "\"type\":" << JsonString(TypeToString(frame.type)) << ","
        << "\"executable\":" << (frame.executable ? "true" : "false") << ","
        << "\"suspicious\":" << (frame.suspicious ? "true" : "false") << ","
        << "\"unbacked_executable\":" << (frame.unbacked_executable ? "true" : "false") << ","
        << "\"backed_modified\":" << (frame.backed_modified ? "true" : "false") << ","
        << "\"module_modified\":" << (frame.module_modified ? "true" : "false") << ","
        << "\"jit_managed\":" << (frame.jit_managed ? "true" : "false") << ","
        << "\"suspicious_gadget_frame\":" << (frame.suspicious_gadget_frame ? "true" : "false") << ","
        << "\"return_address_without_call\":" << (frame.return_address_without_call ? "true" : "false") << ","
        << "\"tail_call_proxy\":" << (frame.tail_call_proxy ? "true" : "false") << ","
        << "\"forward_proxy_frame\":" << (frame.forward_proxy_frame ? "true" : "false") << ","
        << "\"unwind_metadata_tampered\":" << (frame.unwind_metadata_tampered ? "true" : "false") << ","
        << "\"captured_context_modified\":" << (frame.captured_context_modified ? "true" : "false");
    if (frame.region_base) {
        output << ",\"region_base\":\"" << Hex64(frame.region_base) << "\""
            << ",\"region_size\":" << frame.region_size;
    }
    if (frame.allocation_base) {
        output << ",\"allocation_base\":\"" << Hex64(frame.allocation_base) << "\""
            << ",\"allocation_size\":" << frame.allocation_size
            << ",\"allocation_protect\":" << JsonString(ProtectToString(frame.allocation_protect));
    }
    if (frame.module_modified_bytes) {
        output << ",\"module_modified_bytes\":" << frame.module_modified_bytes;
    }
    if (frame.unwind_modified_bytes) {
        output << ",\"unwind_modified_bytes\":" << frame.unwind_modified_bytes;
    }
    if (frame.captured_context_modified_bytes) {
        output << ",\"captured_context_modified_bytes\":" << frame.captured_context_modified_bytes;
    }
    if (!frame.module_path.empty()) {
        output << ",\"module_path\":" << JsonString(frame.module_path);
    }
    output << "}";
}

