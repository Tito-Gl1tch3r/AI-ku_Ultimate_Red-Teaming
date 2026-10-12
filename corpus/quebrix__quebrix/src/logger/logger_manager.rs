use chrono::prelude::*;
use std::{
    fs::{File, OpenOptions},
    io::{Read, Write},
    path::{Path, PathBuf},
};

use crate::known_directories::KNOWN_DIRECTORIES;
pub enum LogType {
    Information,
    Error,
    Warning,
}

pub struct Logger<'a> {
    message: &'a str,
    log_type: LogType,
}

impl<'a> Logger<'a> {
    pub fn log_info(message: &'a str) -> Self {
        Logger {
            message,
            log_type: LogType::Information,
        }
    }

    pub fn log_info_data(message: &'a String) -> Self {
        Logger {
            message,
            log_type: LogType::Information,
        }
    }

    pub fn log_error(message: &'a str) -> Self {
        Logger {
            message,
            log_type: LogType::Error,
        }
    }

    pub fn log_error_data(message: &'a String) -> Self {
        Logger {
            message,
            log_type: LogType::Error,
        }
    }

    pub fn log_warn(message: &'a str) -> Self {
        Logger {
            message,
            log_type: LogType::Warning,
        }
    }

    pub fn log_warn_data(message: &'a String) -> Self {
        Logger {
            message,
            log_type: LogType::Warning,
        }
    }

    pub fn write_log_to_file(&self) {
        let log_dir = &KNOWN_DIRECTORIES.log_directory;

        let now: DateTime<Local> = Local::now();
        let formatted_date = now.format("%d-%m-%Y %H:%M:%S %A").to_string();
        let log_file_name = format!("logger_{}.txt", now.format("%d-%m-%Y"));
        let log_file_path = PathBuf::from(log_dir).join(log_file_name);
        if !log_file_path.exists() {
            File::create(&log_file_path).expect("Failed to create logger file");
        }
        let mut file = OpenOptions::new()
            .append(true)
            .open(&log_file_path)
            .expect("Failed to open logger file");
        let formatted_message = match self.log_type {
            LogType::Information => format!("[INFO] at:{} => {}\n", formatted_date, self.message),
            LogType::Error => format!("[ERROR] at:{} =>  {}\n", formatted_date, self.message),
            LogType::Warning => format!("[WARNING] at:{} => {}\n", formatted_date, self.message),
        };
        file.write_all(formatted_message.as_bytes())
            .expect("Failed to write to logger file");
    }

    pub fn return_logs() -> String {
        let log_dir = &KNOWN_DIRECTORIES.log_directory;
        let now: DateTime<Local> = Local::now();
        let formatted_date = now.format("%d-%m-%Y %H:%M:%S %A").to_string();
        let log_file_name = format!("logger_{}.txt", now.format("%d-%m-%Y"));
        let log_file_path = PathBuf::from(log_dir).join(log_file_name);
        let mut file = OpenOptions::new()
            .read(true)
            .open(&log_file_path)
            .expect("Failed to open logger file");
        let mut content = String::new();
        file.read_to_string(&mut content)
            .expect("Failed to read logger file");
        content
    }
}
