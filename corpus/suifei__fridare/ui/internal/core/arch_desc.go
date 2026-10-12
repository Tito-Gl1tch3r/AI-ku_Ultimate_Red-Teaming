package core

import (
	"debug/elf"
	"debug/macho"
	"debug/pe"
	"encoding/binary"
	"fmt"
	"strings"
)

// describeArch returns a detailed description of the file architecture
func describeArch(file interface{}, format ExecutableFormat) string {
	switch format {
	case MachO:
		switch f := file.(type) {
		case *macho.File:
			return describeMachOArch(f)
		case *macho.FatFile:
			return "MachO Fat Binary (Multiple Architectures)"
		}
	case ELF:
		if f, ok := file.(*elf.File); ok {
			return describeELFArch(f)
		}
	case PE:
		if f, ok := file.(*pe.File); ok {
			return describePEArch(f)
		}
	}
	return "Unknown Architecture"
}

// cpuTypeToString converts MachO CPU type to string
func cpuTypeToString(cpu macho.Cpu) string {
	switch cpu {
	case macho.Cpu386:
		return "x86"
	case macho.CpuAmd64:
		return "x86_64"
	case macho.CpuArm:
		return "ARM"
	case macho.CpuArm64:
		return "ARM64"
	case macho.CpuPpc:
		return "PowerPC"
	case macho.CpuPpc64:
		return "PowerPC 64"
	default:
		return fmt.Sprintf("Unknown CPU type: %d", cpu)
	}
}

// describeMachOArch describes MachO file architecture
func describeMachOArch(f *macho.File) string {
	cpu := cpuTypeToString(f.Cpu)
	byteOrder := "Little Endian"
	if f.ByteOrder == binary.BigEndian {
		byteOrder = "Big Endian"
	}
	return fmt.Sprintf("MachO: CPU: %s, Byte Order: %s, File Type: %s", cpu, byteOrder, f.Type.String())
}

// describeELFArch describes ELF file architecture
func describeELFArch(f *elf.File) string {
	var details []string
	details = append(details, fmt.Sprintf("Machine: %s", f.Machine.String()))
	details = append(details, fmt.Sprintf("Class: %s", f.Class.String()))
	details = append(details, fmt.Sprintf("Data: %s", f.Data.String()))
	details = append(details, fmt.Sprintf("OSABI: %s", describeOSABI(f.OSABI)))
	details = append(details, fmt.Sprintf("ABI Version: %d", f.ABIVersion))
	details = append(details, fmt.Sprintf("Type: %s", f.Type.String()))
	details = append(details, fmt.Sprintf("Entry: 0x%x", f.Entry))

	if len(f.Progs) > 0 {
		details = append(details, fmt.Sprintf("Program Headers: %d", len(f.Progs)))
		for _, prog := range f.Progs {
			details = append(details, fmt.Sprintf("  Type: %s, Flags: %s, VAddr: 0x%x, Memsz: 0x%x",
				prog.Type.String(), describeProgramFlags(prog.Flags), prog.Vaddr, prog.Memsz))
		}
	}

	if len(f.Sections) > 0 {
		details = append(details, fmt.Sprintf("Section Headers: %d", len(f.Sections)))
		for _, section := range f.Sections {
			details = append(details, fmt.Sprintf("  Name: %s, Type: %s, Flags: %s, Addr: 0x%x, Size: 0x%x",
				section.Name, section.Type.String(), describeSectionFlags(section.Flags), section.Addr, section.Size))
		}
	}

	if syms, err := f.DynamicSymbols(); err == nil {
		details = append(details, fmt.Sprintf("Dynamic Symbols: %d", len(syms)))
	}

	if libs, err := f.ImportedLibraries(); err == nil && len(libs) > 0 {
		details = append(details, fmt.Sprintf("Imported Libraries: %s", strings.Join(libs, ", ")))
	}

	return strings.Join(details, "\n")
}

// describeOSABI describes ELF OS/ABI
func describeOSABI(osabi elf.OSABI) string {
	switch osabi {
	case elf.ELFOSABI_NONE:
		return "UNIX System V ABI"
	case elf.ELFOSABI_HPUX:
		return "HP-UX"
	case elf.ELFOSABI_NETBSD:
		return "NetBSD"
	case elf.ELFOSABI_LINUX:
		return "Linux"
	case elf.ELFOSABI_SOLARIS:
		return "Sun Solaris"
	case elf.ELFOSABI_AIX:
		return "IBM AIX"
	case elf.ELFOSABI_IRIX:
		return "SGI Irix"
	case elf.ELFOSABI_FREEBSD:
		return "FreeBSD"
	case elf.ELFOSABI_TRU64:
		return "Compaq TRU64 UNIX"
	case elf.ELFOSABI_MODESTO:
		return "Novell Modesto"
	case elf.ELFOSABI_OPENBSD:
		return "OpenBSD"
	case elf.ELFOSABI_ARM:
		return "ARM"
	case elf.ELFOSABI_STANDALONE:
		return "Standalone (embedded) application"
	default:
		return fmt.Sprintf("Unknown OSABI (%d)", osabi)
	}
}

// describeProgramFlags describes ELF program flags
func describeProgramFlags(flags elf.ProgFlag) string {
	var s []string
	if flags&elf.PF_X != 0 {
		s = append(s, "X")
	}
	if flags&elf.PF_W != 0 {
		s = append(s, "W")
	}
	if flags&elf.PF_R != 0 {
		s = append(s, "R")
	}
	return strings.Join(s, "+")
}

// describeSectionFlags describes ELF section flags
func describeSectionFlags(flags elf.SectionFlag) string {
	var s []string
	if flags&elf.SHF_WRITE != 0 {
		s = append(s, "W")
	}
	if flags&elf.SHF_ALLOC != 0 {
		s = append(s, "A")
	}
	if flags&elf.SHF_EXECINSTR != 0 {
		s = append(s, "X")
	}
	return strings.Join(s, "+")
}

// describePEArch describes PE file architecture
func describePEArch(f *pe.File) string {
	var details []string
	details = append(details, fmt.Sprintf("Machine: %d", f.Machine))

	characteristics := describeCharacteristics(f.Characteristics)
	if len(characteristics) > 0 {
		details = append(details, fmt.Sprintf("Characteristics: %s", strings.Join(characteristics, ", ")))
	}

	if f.OptionalHeader != nil {
		switch oh := f.OptionalHeader.(type) {
		case *pe.OptionalHeader32:
			details = append(details, "Format: PE32")
			details = append(details, fmt.Sprintf("Subsystem: %s", describeSubsystem(oh.Subsystem)))
			details = append(details, fmt.Sprintf("BaseOfCode: 0x%X", oh.BaseOfCode))
			details = append(details, fmt.Sprintf("BaseOfData: 0x%X", oh.BaseOfData))
		case *pe.OptionalHeader64:
			details = append(details, "Format: PE32+")
			details = append(details, fmt.Sprintf("Subsystem: %s", describeSubsystem(oh.Subsystem)))
			details = append(details, fmt.Sprintf("BaseOfCode: 0x%X", oh.BaseOfCode))
		}
	}

	details = append(details, fmt.Sprintf("Number of Sections: %d", len(f.Sections)))
	for i, s := range f.Sections {
		details = append(details, fmt.Sprintf("  Section %d: %s", i, describePESection(s)))
	}

	details = append(details, fmt.Sprintf("Number of Symbols: %d", len(f.Symbols)))

	return strings.Join(details, "\n")
}

// describePESection describes a PE section
func describePESection(s *pe.Section) string {
	return fmt.Sprintf("Name: %s, Address: 0x%X, Size: 0x%X", s.Name, s.VirtualAddress, s.Size)
}

// describeCharacteristics describes PE characteristics
func describeCharacteristics(characteristics uint16) []string {
	var chars []string
	if characteristics&pe.IMAGE_FILE_EXECUTABLE_IMAGE != 0 {
		chars = append(chars, "Executable")
	}
	if characteristics&pe.IMAGE_FILE_LARGE_ADDRESS_AWARE != 0 {
		chars = append(chars, "Large Address Aware")
	}
	if characteristics&pe.IMAGE_FILE_DLL != 0 {
		chars = append(chars, "DLL")
	}
	if characteristics&pe.IMAGE_FILE_32BIT_MACHINE != 0 {
		chars = append(chars, "32-bit")
	}
	if characteristics&pe.IMAGE_FILE_SYSTEM != 0 {
		chars = append(chars, "System")
	}
	if characteristics&pe.IMAGE_FILE_DEBUG_STRIPPED != 0 {
		chars = append(chars, "Debug Stripped")
	}
	return chars
}

// describeSubsystem describes PE subsystem
func describeSubsystem(subsystem uint16) string {
	switch subsystem {
	case pe.IMAGE_SUBSYSTEM_WINDOWS_GUI:
		return "Windows GUI"
	case pe.IMAGE_SUBSYSTEM_WINDOWS_CUI:
		return "Windows Console"
	case pe.IMAGE_SUBSYSTEM_EFI_APPLICATION:
		return "EFI Application"
	case pe.IMAGE_SUBSYSTEM_EFI_BOOT_SERVICE_DRIVER:
		return "EFI Boot Service Driver"
	case pe.IMAGE_SUBSYSTEM_EFI_RUNTIME_DRIVER:
		return "EFI Runtime Driver"
	case pe.IMAGE_SUBSYSTEM_NATIVE:
		return "Native"
	case pe.IMAGE_SUBSYSTEM_POSIX_CUI:
		return "POSIX Console"
	default:
		return fmt.Sprintf("Unknown (%d)", subsystem)
	}
}
