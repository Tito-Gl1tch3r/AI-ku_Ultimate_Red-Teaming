#pragma once
#ifdef __cplusplus
#ifdef BUILD_OBJECTS_ONLY
#define DFR(module, function) \
	DECLSPEC_IMPORT decltype(function) module##$##function;

template<typename T>
struct StdcallPointer;

template<typename Ret, typename... Args>
struct StdcallPointer<Ret(Args...)> {
	using type = Ret(__stdcall*)(Args...);
};

#define DFR_WINAPI(module, function) \
	DECLSPEC_IMPORT StdcallPointer<decltype(function)>::type module##$##function;

#define DFR_LOCAL(module, function) \
	DECLSPEC_IMPORT decltype(function) module##$##function; \
	decltype(module##$##function) * function = module##$##function;

// Explicit type
#define DFR_TYPE(module, function, type) \
        DECLSPEC_IMPORT type module##$##function

    // Explicit type + value (ignored in release)
#define DFR_VALUE(module, function, type, value) \
        DECLSPEC_IMPORT type module##$##function

#define DFR_ALIAS(module, imported_name, local_name)           \
    DECLSPEC_IMPORT decltype(local_name)                    \
        module##$##imported_name;                              \
    decltype(module##$##imported_name)* local_name =           \
        module##$##imported_name

#else
#define DFR_LOCAL(module, function)
#define DFR(module, function) \
	decltype(function) *module##$##function = function;
// Explicit type
#define DFR_TYPE(module, function, type) \
        type module##$##function = function

	// Explicit type + explicit debug value
#define DFR_VALUE(module, function, type, value) \
        type module##$##function = value

#define DFR_ALIAS(module, imported_name, local_name)           \
    decltype(&::local_name)                    \
        local_name = ::local_name;
#endif // end of _DEBUG
#endif // end of __cplusplus