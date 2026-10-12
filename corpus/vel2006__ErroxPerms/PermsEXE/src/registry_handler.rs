use std::ptr;
use windows::{
    Win32::{
        Foundation::WIN32_ERROR,
        System::Registry::{HKEY, HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE, RegCloseKey, RegOpenKeyA, RegQueryValueExA}
    }, core::PCSTR
};

pub fn CheckInstallRegistry() -> bool
{
    unsafe
    {
        // Opening the registrys
        let mut registry_path: Vec<u8> = "SOFTWARE\\Policies\\Microsoft\\Windowsregistry_path".as_bytes().to_vec();
        registry_path.push(0);
        let mut local_registry_handle: HKEY = HKEY::default();
        let mut user_registry_handle: HKEY = HKEY::default();
        let local_open_result: WIN32_ERROR = RegOpenKeyA(HKEY_LOCAL_MACHINE, PCSTR(registry_path.as_ptr()), &mut local_registry_handle);
        let user_open_result: WIN32_ERROR = RegOpenKeyA(HKEY_CURRENT_USER, PCSTR(registry_path.as_ptr()), &mut user_registry_handle);
        if local_open_result != WIN32_ERROR(0)
        {
            if user_open_result == WIN32_ERROR(0)
            {
                _ = RegCloseKey(user_registry_handle);
            }
            return false;
        }
        if user_open_result != WIN32_ERROR(0)
        {
            _ = RegCloseKey(local_registry_handle);
            return false;
        }
        // Checking the value inside of the registrys
        let mut registry_data: Vec<u8> = "".as_bytes().to_vec();
        registry_data.push(0);
        let mut local_registry_output: u8 = 0;
        let mut user_registry_output: u8 = 0;
        let local_query_result: WIN32_ERROR = RegQueryValueExA(local_registry_handle, PCSTR(registry_data.as_ptr()), None, None, Some(&mut local_registry_output), None);
        let user_query_result: WIN32_ERROR = RegQueryValueExA(user_registry_handle, PCSTR(registry_data.as_ptr()), None, None, Some(&mut user_registry_output), None);
        _ = RegCloseKey(local_registry_handle);
        _ = RegCloseKey(user_registry_handle);
        if local_query_result != WIN32_ERROR(0)
        {
            return false;
        }
        if user_query_result != WIN32_ERROR(0)
        {
            return false;
        }
        if local_registry_output == 0 && user_registry_output == 0
        {
            return true;
        }
        return false;
    };
}

pub fn CheckUACSecurity() -> bool
{
    unsafe
    {
        // Getting the base path and handle to registries
        let base_registry_path: &str = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System";
        let mut consent_registry_path: Vec<u8> = format!("{}\\ConsentPromptBehaviorAdmin", base_registry_path).as_bytes().to_vec();
        let mut signed_registry_path: Vec<u8> = format!("{}\\ValidateAdminCodeSignatures", base_registry_path).as_bytes().to_vec();
        let mut consent_registry_handle: HKEY = HKEY::default();
        let mut signed_registry_handle: HKEY = HKEY::default();
        let consent_handle_output: WIN32_ERROR = RegOpenKeyA(HKEY_LOCAL_MACHINE, PCSTR(consent_registry_path.as_ptr()), &mut consent_registry_handle);
        let signed_handle_output: WIN32_ERROR = RegOpenKeyA(HKEY_LOCAL_MACHINE, PCSTR(signed_registry_path.as_ptr()), &mut consent_registry_handle);
        if consent_handle_output != WIN32_ERROR(0)
        {
            if signed_handle_output == WIN32_ERROR(0)
            {
                _ = RegCloseKey(signed_registry_handle);
            }
            return false;
        }
        if signed_handle_output != WIN32_ERROR(0)
        {
            _ = RegCloseKey(consent_registry_handle);
            return false;
        }
        // Getting the contents of the registries
        let mut consent_registry_output: u8 = 0;
        let mut signed_registry_output: u8 = 0;
        let consent_regitry_result: WIN32_ERROR = RegQueryValueExA(consent_registry_handle, PCSTR(ptr::null()), None, None, Some(&mut consent_registry_output), None);
        let signed_registry_result: WIN32_ERROR = RegQueryValueExA(signed_registry_handle, PCSTR(ptr::null()), None, None, Some(&mut signed_registry_output), None);
        _ = RegCloseKey(consent_registry_handle);
        _ = RegCloseKey(signed_registry_handle);
        if consent_regitry_result != WIN32_ERROR(0)
        {
            return false;
        }
        if signed_registry_result != WIN32_ERROR(0)
        {
            return false;
        }
        if consent_registry_output == 0 && signed_registry_output == 0
        {
            return true;
        }
        return false;
    }
}