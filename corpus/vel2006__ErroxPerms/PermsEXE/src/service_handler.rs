use super::filesystem_handler::CanEditDirectory;
use windows::{core::PCWSTR, Win32::System::Services::*};

pub fn CheckServices(known_services: &Vec<(String, String, String)>) -> Vec<(String, String, String)>
{
    let mut vulnerable_services: Vec<(String, String, String)> = Vec::default();
    let known_protected_paths: Vec<String> = [
        "C:\\Windows".to_string(), "C:\\Users\\Public".to_string(), "C:\\PerfLogs".to_string()
    ].to_vec();
    for entry in known_services
    {
        let (binary_path, service_display, service_start) = entry;
        for protected_path in known_protected_paths.iter()
        {
            if !binary_path.contains(protected_path)
            {
                if CanEditDirectory(&binary_path)
                {
                    vulnerable_services.push((binary_path.to_owned(), service_display.to_owned(), service_start.to_owned()));
                }
            }
        }
    }
    return vulnerable_services;
}

pub fn GetServices() -> Vec<(String, String, String)>
{
    let mut services: Vec<(String, String, String)> = Vec::new();
    unsafe
    {
        if let Ok(service_manager) = OpenSCManagerW(PCWSTR::null(), SERVICES_ACTIVE_DATABASE, SC_MANAGER_ENUMERATE_SERVICE)
        {
            let buffer: u32;
            let mut buffer_size: u32 = 0;
            let mut services_returned: u32 = 0;
            let mut resume_handle: u32 = 0;
            // Getting the buffer size needed for EnumServicesStatusA
            _ = EnumServicesStatusA(service_manager, SERVICE_WIN32, SERVICE_STATE_ALL, None, 0, &mut buffer_size, &mut services_returned, Some(&mut resume_handle));
            buffer = buffer_size;
            let mut service_buffer: Vec<u8> = vec![0u8; buffer_size as usize];
            // Capturing the output of EnumServicesStatusA for enumerating services on this device
            if let Ok(_) = EnumServicesStatusA(service_manager, SERVICE_WIN32, SERVICE_STATE_ALL, Some(service_buffer.as_mut_ptr() as *mut ENUM_SERVICE_STATUSA), buffer, &mut buffer_size, &mut services_returned, Some(&mut resume_handle))
            {
                let service_pointer: *const ENUM_SERVICE_STATUSA = service_buffer.as_ptr() as *const ENUM_SERVICE_STATUSA;
                for i in 0..services_returned
                {
                    let service: ENUM_SERVICE_STATUSA = *service_pointer.add(i as usize);
                    // Opening up the service
                    if let Ok (service_handle) = OpenServiceA(service_manager, service.lpServiceName, SERVICE_QUERY_CONFIG)
                    {
                        let mut path_buffer: u32 = 0;
                        // Getting the buffer size needed for the service's information
                        _ = QueryServiceConfigA(service_handle, None, 0, &mut path_buffer);
                        let mut config_buffer: Vec<u8> = vec![0u8; path_buffer as usize];
                        let path_output: *mut QUERY_SERVICE_CONFIGA = config_buffer.as_mut_ptr() as *mut QUERY_SERVICE_CONFIGA;
                        // Getting the service's information
                        if let Ok(_) = QueryServiceConfigA(service_handle, Some(path_output), path_buffer, &mut path_buffer)
                        {
                            let config: &QUERY_SERVICE_CONFIGA = &*path_output;
                            if config.dwStartType == SERVICE_AUTO_START
                            {
                                services.push((config.lpBinaryPathName.to_string().unwrap(), config.lpDisplayName.to_string().unwrap(), config.lpServiceStartName.to_string().unwrap()));
                            }
                        }
                        _ = CloseServiceHandle(service_handle);
                    }
                }
            }
            _ = CloseServiceHandle(service_manager);
        }
    };
    return services;
}