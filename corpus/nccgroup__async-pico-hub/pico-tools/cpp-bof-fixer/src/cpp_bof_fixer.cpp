// COFFIBOFFixer.cpp : This file contains the 'main' function. Program execution begins and ends there.
//

#include <iostream>
#include <coffi/coffi.hpp>
#include <unordered_map>
#include <vector>
#include <unordered_set>

using namespace COFFI;

bool IsBeaconApiFunction(const std::string& name)
{
	static const std::unordered_set<std::string> kBeaconApis = {
		"BeaconDataExtract",
		"BeaconDataInt",
		"BeaconDataLength",
		"BeaconDataParse",
		"BeaconDataPtr",
		"BeaconDataShort",

		"BeaconPrintf",
		"BeaconOutput",
		"BeaconDownload",

		"BeaconFormatAlloc",
		"BeaconFormatAppend",
		"BeaconFormatFree",
		"BeaconFormatInt",
		"BeaconFormatPrintf",
		"BeaconFormatReset",
		"BeaconFormatToString",

		"BeaconUseToken",
		"BeaconRevertToken",
		"BeaconIsAdmin",
		"BeaconGetSpawnTo",
		"BeaconSpawnTemporaryProcess",
		"BeaconInjectProcess",
		"BeaconInjectTemporaryProcess",
		"BeaconCleanupProcess",

		"BeaconDataStoreGetItem",
		"BeaconDataStoreProtectItem",
		"BeaconDataStoreUnprotectItem",
		"BeaconDataStoreMaxEntries",

		"toWideChar",
		"BeaconInformation",

		"BeaconAddValue",
		"BeaconGetValue",
		"BeaconRemoveValue",

		"BeaconGetCustomUserData",

		"BeaconGetSyscallInformation",

		"BeaconVirtualAlloc",
		"BeaconVirtualAllocEx",
		"BeaconVirtualProtect",
		"BeaconVirtualProtectEx",
		"BeaconVirtualFree",
		"BeaconGetThreadContext",
		"BeaconSetThreadContext",
		"BeaconResumeThread",
		"BeaconOpenProcess",
		"BeaconOpenThread",
		"BeaconCloseHandle",
		"BeaconUnmapViewOfFile",
		"BeaconVirtualQuery",
		"BeaconDuplicateHandle",
		"BeaconReadProcessMemory",
		"BeaconWriteProcessMemory",

		"BeaconDisableBeaconGate",
		"BeaconEnableBeaconGate",

		"go",
		"_go",
		"sleep_mask"
	};

	return kBeaconApis.find(name) != kBeaconApis.end();
}




struct section_data {
	std::vector<char> data;
	uint32_t virtual_address;
	size_t virtual_size;
	uint32_t flags;
	std::vector<COFFI::relocation> relocations;
};

constexpr int align_up(int n, int align) {
	return (n + (align - 1)) & ~(align - 1);
}


void move_element(COFFI::sections& vec, const std::string& target, const std::string& prefix) {
	// Find the element containing `target`
	auto it = std::find_if(vec.begin(), vec.end(), [&](section* s) {
		return s->get_name() == (target);
		});
	if (it == vec.end()) return; // Not found

	// Find the first element that exactly matches `prefix`
	auto pos = std::find_if(vec.begin(), vec.end(), [&](section* s) {return s->get_name().find(prefix) != std::string::npos; });

	if (pos != vec.end() && it != pos) {
		// Move `target` before `prefix`
		section* temp = std::move(*it);
		vec.erase(it);
		vec.insert(pos, std::move(temp));
	}
}

void deduplicate_symbols(
	std::vector<size_t> remap,
	std::vector<COFFI::relocation>& relocs)
{
	//
	// Rewrite relocations
	//
	size_t i = 0;
	for (auto& reloc : relocs) {

		if (reloc.get_symbol_table_index() < remap.size()) {
			auto index = reloc.get_symbol_table_index();
			if (remap[index] != index) {
				reloc.set_symbol(remap[reloc.get_symbol_table_index()]);
			}
			else {
				reloc.set_symbol(remap[reloc.get_symbol_table_index()]);
			}
			i++;
		}
	}

	
}

int main(int argc, char** argv)
{
	// Create an coffi reader
	coffi reader;
	coffi reader_output;

	// Load COFF data
	if (!reader.load(argv[1])) {
		std::cout << "Can't find or process COFF file " << argv[1] << std::endl;
		return 2;
	}

	if (!reader_output.load(argv[1])) {
		std::cout << "Can't find or process COFF file " << argv[1] << std::endl;
		return 2;
	}

	std::string filename_output = "bof_changed.x64.o";

	if (argc > 2) {
		filename_output = argv[2];
	}

	std::unordered_map < std::string, section* > sections;
	std::unordered_map<uint16_t, uint16_t> oldSectionIndexToNewSectionIndex;
	std::unordered_map<uint16_t, uint32_t> oldSectionIndexToNewSectionOffset;
	std::unordered_map<uint16_t, uint32_t> sectionSizeWithAlignment;
	auto syms = reader_output.get_symbols();
	auto symbols = reader.get_symbols();
	reader_output.get_sections().clean();

	unsigned counter = 1;

	auto& before_sections = reader.get_sections();
	move_element(before_sections, ".text$A", ".text");
	auto& after_sections = reader.get_sections();

	for (auto& section : before_sections) {

		auto section_name = section->get_name();

		if (section_name.find("text") != std::string::npos) section_name = ".text";

		if (section_name.find("bss") != std::string::npos) {
			section_name = section_name;
		}

		if (sections.count(section_name)) {
			auto sec = sections[section_name];

			oldSectionIndexToNewSectionOffset[section->get_index()] = (sec->get_data_size());
			auto sec_data = section->get_data();
			if (!sec_data) {
				//std::cout << "Section Data is NULL. Skipping...\n";
				sec_data = new char[section->get_data_size()];
			}
			sec->append_data(sec_data, section->get_data_size());

			auto diff = align_up(section->get_data_size(), 0x10) - section->get_data_size();
			auto padding = 0;
			if (section_name == ".text") {
				padding = 0x90;
			}
			std::vector<char> t(diff, padding);
			sec->append_data(t.data(), t.size());

			sectionSizeWithAlignment[sec->get_index()] = sectionSizeWithAlignment[sec->get_index()] + align_up(section->get_data_size(), 0x10);

			oldSectionIndexToNewSectionIndex[section->get_index()] = sec->get_index();

		}
		else {
			auto section_name = section->get_name();

			if (section_name.find("text") != std::string::npos) section_name = ".text";

			COFFI::section* sec = reader_output.add_section(section_name);
			sec->set_name(section_name);
			sec->set_index(counter - 1);
			auto sec_data = section->get_data();
			if (!sec_data) {
				sec_data = new char[section->get_data_size()];
			}
			sec->set_data(sec_data, section->get_data_size());
			sec->set_data_offset(section->get_data_offset());
			sec->set_alignment(section->get_alignment());
			sec->set_virtual_size(section->get_virtual_size());
			sec->set_virtual_address(section->get_virtual_address());
			sec->set_flags(section->get_flags());
			sec->set_alignment(section->get_alignment());

			sections[section_name] = sec;
			oldSectionIndexToNewSectionOffset[section->get_index()];
			sectionSizeWithAlignment[sec->get_index()] = align_up(sec->get_data_size(), 0x10);
			oldSectionIndexToNewSectionIndex[section->get_index()] = sec->get_index();
			oldSectionIndexToNewSectionOffset[section->get_index()] = 0;
			counter++;
		}

	}

	std::unordered_map<uint16_t, uint32_t> sectionIndexToAccumulatedSizeOriginal;
	std::unordered_map<uint16_t, uint32_t> sectionIndexToAccumulatedSizeModified;

	{
		unsigned accum = 0;
		for (auto& section : reader.get_sections()) {
			sectionIndexToAccumulatedSizeOriginal[section->get_index()] = accum;
			accum += section->get_data_size();
			accum = align_up(accum, 0x10);
		}
	}

	{
		unsigned accum = 0;
		for (auto& section : reader_output.get_sections()) {
			sectionIndexToAccumulatedSizeModified[section->get_index()] = accum;
			accum += sectionSizeWithAlignment[section->get_index()];
			accum = align_up(accum, 0x10);
		}
	}

	auto test = align_up(0x10, 0x10);

	// new chkstk fix
	auto symbol_chkstk = reader_output.get_symbol("__chkstk");
	if (symbol_chkstk) {
		auto symbol_chkstk_impl = reader_output.get_symbol("chkstk_impl");
		if (!symbol_chkstk_impl) {
			std::cout << "Could not find symbol chkstk_impl needed to find reference to existing __chkstk. Did you forget to implement chkstk_impl?\n";
			return -1;
		}
		symbol_chkstk->set_type(symbol_chkstk_impl->get_type());
		symbol_chkstk->set_section_number(symbol_chkstk_impl->get_section_number());
		symbol_chkstk->set_value(symbol_chkstk_impl->get_value());
		symbol_chkstk->set_storage_class(symbol_chkstk_impl->get_storage_class());
	}
	// end
	// new ??3@YAXPEAX_K@Z fix
	{
		auto symbol_free = reader_output.get_symbol("??3@YAXPEAX_K@Z");
		if (symbol_free) {
			auto symbol_free_impl = reader_output.get_symbol("free_impl");
			if (!symbol_free_impl) {
				std::cout << "Could not find symbol free_impl needed to find reference to existing ??3@YAXPEAX_K@Z. Did you forget to implement free_impl?\n";
				return -1;
			}
			symbol_free->set_type(symbol_free_impl->get_type());
			symbol_free->set_section_number(symbol_free_impl->get_section_number());
			symbol_free->set_value(symbol_free_impl->get_value());
			symbol_free->set_storage_class(symbol_free_impl->get_storage_class());
		}
	}
	// end
	// new ??3@YAXPEAX_K@Z fix
	{
		auto symbol_free = reader_output.get_symbol("??3@YAXPEAX@Z");
		if (symbol_free) {
			auto symbol_free_impl = reader_output.get_symbol("free_impl");
			if (!symbol_free_impl) {
				std::cout << "Could not find symbol free_impl needed to find reference to existing ??3@YAXPEAX@Z. Did you forget to implement free_impl?\n";
				return -1;
			}
			symbol_free->set_type(symbol_free_impl->get_type());
			symbol_free->set_section_number(symbol_free_impl->get_section_number());
			symbol_free->set_value(symbol_free_impl->get_value());
			symbol_free->set_storage_class(symbol_free_impl->get_storage_class());
		}
	}
	// end

	size_t symbol_counter = 0;
	for (auto& symbol : *reader_output.get_symbols()) {
		auto symbol_name = symbol.get_name();
		if (symbol.get_name().find("HRESULT") != std::string::npos) {
			//std::cout << "hash found";
		}

		if (symbol_name.find(".text") != std::string::npos)
			symbol.set_name(".text");

		if (symbol_name.find("__imp") == std::string::npos && symbol_name.find(".") == std::string::npos && !IsBeaconApiFunction(symbol_name) && symbol_name != "go")
			symbol.set_name(symbol.get_name() + "S" + std::to_string(symbol_counter));

		
			

		auto storage_class = symbol.get_storage_class();
		auto oldSectionNumber = symbol.get_section_number();
		if (oldSectionNumber) { // Section 0 is special, leave as is.
			symbol.set_section_number(oldSectionIndexToNewSectionIndex[oldSectionNumber - 1] + 1);
		}
		auto symbol_value = symbol.get_value();
		auto offset = oldSectionIndexToNewSectionOffset[oldSectionNumber - 1];
		symbol.set_value(symbol.get_value() + offset);
		if (symbol.get_storage_class() == 0x3 && symbol_name.find(".text") != std::string::npos && offset > 0) {
			//std::cout << "do something";
		}

		if (symbol_name.find(".") != std::string::npos && symbol.get_value() != 0) {
			symbol.set_name(symbol.get_name() + "A" + std::to_string(symbol_counter));
			symbol.set_storage_class(0x6);
			symbol.set_section_number(0x1);
			symbol.set_value(0);
		}

		++symbol_counter;
	}

	for (auto& section : reader.get_sections()) {
		auto relocations = section->get_relocations();
		for (auto& reloc : section->get_relocations()) {
			for (auto& outputSection : reader_output.get_sections()) {
				if (oldSectionIndexToNewSectionIndex[section->get_index()] == outputSection->get_index()) {
					rel_entry_generic entry = { reloc.get_virtual_address() + oldSectionIndexToNewSectionOffset[section->get_index()],reloc.get_symbol_table_index(),reloc.get_type(),0 };
					outputSection->add_relocation_entry(&entry);
				}
			}

		}
	}

	{
		std::vector<COFFI::symbol>& symbolsx = reader_output.get_symbols_ref();
		//
		// symbol index -> canonical index
		//
		std::vector<size_t> remap((symbolsx.end() - 1)->get_index() + 1);

		//
		// first symbol occurrence
		//
		std::unordered_map<std::string, size_t> firstSeen;



		//
		// Build remap table
		//
		for (size_t i = 0; i < remap.size(); ++i) {

			const auto itname = std::find_if(symbolsx.begin(), symbolsx.end(), [&](COFFI::symbol& symb) {return symb.get_index() == i;});
			std::string name;
			if (itname != symbolsx.end())
				name = (*itname).get_name();
			else
				continue;

			auto it = firstSeen.find(name);

			//
			// First occurrence
			//
			if (it == firstSeen.end() || ((*itname).get_storage_class() != 0x2 || (*itname).get_section_number() != 0)) {

				firstSeen[name] = i;
				remap[i] = i;
			}
			//
			// Duplicate
			//
			else {

				remap[i] = it->second;
			}
		}

		const auto freeimpl = std::find_if(symbolsx.begin(), symbolsx.end(), [&](COFFI::symbol& symb) {return symb.get_name().find("free_impl") != std::string::npos;});
		if (freeimpl != symbolsx.end()) {
			firstSeen[freeimpl->get_name()] = freeimpl->get_index();
		}
		// ??3@YAXPEAX@Z

		const auto yaxpeax = std::find_if(symbolsx.begin(), symbolsx.end(), [&](COFFI::symbol& symb) {return symb.get_name().find("??3@YAXPEAX@Z") != std::string::npos;});
		if (yaxpeax != symbolsx.end()) {
			remap[yaxpeax->get_index()] = freeimpl->get_index();
		}

		// "??3@YAXPEAX_K@Z"

		{
			const auto yaxpeax = std::find_if(symbolsx.begin(), symbolsx.end(), [&](COFFI::symbol& symb) {return symb.get_name().find("??3@YAXPEAX_K@Z") != std::string::npos;});
			if (yaxpeax != symbolsx.end()) {
				remap[yaxpeax->get_index()] = freeimpl->get_index();
			}
		}

		// __chkstk

		const auto chkstkimpl = std::find_if(symbolsx.begin(), symbolsx.end(), [&](COFFI::symbol& symb) {return symb.get_name().find("chkstk_impl") != std::string::npos;});
		if (freeimpl != symbolsx.end()) {
			firstSeen[freeimpl->get_name()] = freeimpl->get_index();
		}

		{
			const auto yaxpeax = std::find_if(symbolsx.begin(), symbolsx.end(), [&](COFFI::symbol& symb) {return symb.get_name().find("__chkstk") != std::string::npos;});
			if (yaxpeax != symbolsx.end()) {
				remap[yaxpeax->get_index()] = chkstkimpl->get_index();
			}
		}


		for (auto& section : reader_output.get_sections())
			deduplicate_symbols(remap, section->get_relocations());

		//
	// Zero duplicate symbols
	//
		for (size_t i = 0; i < remap.size(); ++i) {
			const auto itname = std::find_if(symbolsx.begin(), symbolsx.end(), [&](COFFI::symbol& symb) {return symb.get_index() == i;});

			if (itname == symbolsx.end())
				continue;

			//
			// Skip canonical symbols
			//
			if (remap[i] == (*itname).get_index())
				continue;

			itname->set_name("__removed__");

			itname->set_value(0);
			itname->set_section_number(1);
			itname->set_type(0);
			itname->set_storage_class(0x6);
		}
	}
	reader_output.save(filename_output);

}