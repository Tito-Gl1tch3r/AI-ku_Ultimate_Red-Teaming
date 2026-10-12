#include "modules_enum.h"

#include <psapi.h>
#pragma comment(lib,"psapi.lib")

namespace {
	size_t _enum_modules(IN HANDLE hProcess, IN OUT HMODULE hMods[], DWORD hModsMax, IN DWORD filters) //throws exceptions
	{
		if (hProcess == nullptr) {
			return 0;
		}
		const char err_msg[] = "Could not enumerate modules. ";
		DWORD cbNeeded = 0;
#ifdef _WIN64
		if (!EnumProcessModulesEx(hProcess, hMods, hModsMax, &cbNeeded, filters)) {
			throw std::runtime_error(err_msg);
			return 0;
		}
#else
		/*
		Some old, 32-bit versions of Windows do not have EnumProcessModulesEx,
		but we can use EnumProcessModules for the 32-bit version: it will work the same and prevent the compatibility issues.
		*/
		if (!EnumProcessModules(hProcess, hMods, hModsMax, &cbNeeded)) {
			throw std::runtime_error(err_msg);
			return 0;
		}
#endif
		const size_t modules_count = cbNeeded / sizeof(HMODULE);
		return modules_count;
	}
};

size_t pesieve::util::enum_modules(IN HANDLE hProcess, IN OUT std::vector<HMODULE>& modules, IN DWORD filters) //throws exceptions
{
	if (hProcess == nullptr) {
		return 0;
	}
	const size_t max_count = 1024 * 3;
	size_t capacity = 1024;

	while (true) {
		modules.assign(capacity, nullptr);

		const size_t size_in_bytes = modules.size() * sizeof(HMODULE);
		if (size_in_bytes > MAXDWORD) {
			throw std::runtime_error("Module buffer too large.");
		}
		const size_t count = _enum_modules(
			hProcess,
			modules.data(),
			static_cast<DWORD>(size_in_bytes),
			filters
		);

		if (count <= modules.size()) {
			modules.resize(count);
			return count;
		}
		if (count > max_count) {
			throw std::runtime_error("Too many modules to enumerate safely.");
		}
		capacity = count;
	}
}
