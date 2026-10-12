use std::{
    env::args,
    process::exit
};

use windows::{
    Win32::{System::Threading::{CREATE_NEW_CONSOLE, CreateProcessA, PROCESS_INFORMATION, STARTUPINFOA}}, core::PSTR
};


#[used]
#[unsafe(link_section = ".run_tar")]
static TARGET_COMMAND: [u8; 620] = [0x00; 620];

fn main()
{
    let command: String;
    let mut full_command: String;
    let collected_arguments: Vec<String> = args().collect();
    if let Ok(string) = String::from_utf8(TARGET_COMMAND.to_ascii_lowercase())
    {
        command = string;
    } else if let Ok(string) = String::from_utf8(TARGET_COMMAND.to_vec()) {
        command = string;
    } else {
        exit(1);
    }
    full_command = command.replace("\0", "");
    for i in 0..collected_arguments.len()
    {
        if i != 0
        {
            full_command = format!("{} {}", full_command, collected_arguments[i].clone());
        }
    }
    println!("Running command: {:?}", full_command);
    unsafe
    {
        let command_line: PSTR = PSTR::from_raw(full_command.as_mut_ptr());
        let startup_information: STARTUPINFOA = STARTUPINFOA::default();
        let mut cmd_information: PROCESS_INFORMATION = PROCESS_INFORMATION::default();
        if let Err(error) = CreateProcessA(PSTR::null(), Some(PSTR::from_raw("C:\\Windows\\System32\\cmd.exe".to_string().as_mut_ptr())), None, None, false, CREATE_NEW_CONSOLE, None, PSTR::null(), &startup_information, &mut cmd_information)
        {
            println!("Error when starting cmd.exe:\n{:?}", error);
            exit(1);
        }
        let mut process_information: PROCESS_INFORMATION = PROCESS_INFORMATION::default();
        if let Err(error) = CreateProcessA(PSTR::null(), Some(command_line), None, None, false, CREATE_NEW_CONSOLE, None, PSTR::null(), &startup_information, &mut process_information)
        {
            println!("Error when starting command:\n{:?}", error);
            exit(1);
        }
    }
    exit(0);
}