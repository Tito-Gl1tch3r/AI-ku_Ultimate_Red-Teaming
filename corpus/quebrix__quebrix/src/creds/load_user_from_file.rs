use super::cred_manager::{ACLResult, CredsManager, RoleManagement, User};
use super::cred_manager::{ENCRYPT_KEY, IV_PATTERN};
use crate::crypto::crypto_service::Encryptor;
use crate::known_directories::KNOWN_DIRECTORIES;
use crate::logger::logger_manager::Logger;
use std::collections::HashMap;
use std::fs::OpenOptions;
use std::io::{self, BufRead, BufReader, Write};
use std::path::PathBuf;
pub trait LoadUserFromFile {
    fn load_users_from_file(&mut self) -> ACLResult;
}

impl LoadUserFromFile for CredsManager {
    fn load_users_from_file(&mut self) -> ACLResult {
        self.create_admin();

        if self.enable_log {
            let message = "default user recognized";
            Logger::log_info(message).write_log_to_file();
        }

        let encryptor = Encryptor::new(ENCRYPT_KEY, IV_PATTERN);

        if self.users.is_empty() {
            self.users = HashMap::new();
        }

        let kn_dir = &KNOWN_DIRECTORIES;
        let file_path = PathBuf::from(&kn_dir.creds_directory).join("users.txt");

        let open_file_result = OpenOptions::new().read(true).open(&file_path);
        let file = match open_file_result {
            Ok(file) => file,
            Err(_) => {
                if self.enable_log {
                    let message = "Failed to open users file path";
                    Logger::log_info(message).write_log_to_file();
                }
                eprintln!("Failed to open users file");
                return ACLResult::faild("failed to load user file");
            }
        };

        let reader = BufReader::new(file);
        for line in reader.lines() {
            let line = match line {
                Ok(line) => line,
                Err(_) => {
                    if self.enable_log {
                        let message = "Failed to read line from users file";
                        Logger::log_error(&message).write_log_to_file();
                    }
                    return ACLResult::faild("failed to read user file");
                }
            };

            // Split the line into parts (username, password, role)
            let parts: Vec<&str> = line.split(':').collect();
            if parts.len() == 3 {
                // Parse the password into a Vec<u8>
                let trimmed_input = parts[1].trim_matches(|c| c == '[' || c == ']');
                let vec_u8: Vec<u8> = trimmed_input
                    .split(", ")
                    .map(|s| {
                        s.parse().unwrap_or_else(|_| {
                            if self.enable_log {
                                let message = format!("Invalid byte format in line: {}", line);
                                Logger::log_error_data(&message).write_log_to_file();
                            }
                            eprintln!("Invalid byte format: {}", line);
                            0u8 // Return a default value or handle it gracefully
                        })
                    })
                    .collect();

                self.users.insert(
                    parts[0].to_string(),
                    User {
                        username: parts[0].to_string(),
                        password: vec_u8,
                        role: match parts[2].parse::<RoleManagement>() {
                            Ok(role) => role,
                            Err(_) => {
                                if self.enable_log {
                                    let message = format!("Invalid role format in line: {}", line);
                                    Logger::log_error_data(&message).write_log_to_file();
                                }
                                eprintln!("Invalid role format: {}", line);
                                return ACLResult::faild("invalid role format");
                            }
                        },
                    },
                );
            } else {
                if self.enable_log {
                    let message = format!("Invalid line format: {}", line);
                    Logger::log_error_data(&message).write_log_to_file();
                }
                eprintln!("Invalid line format: {}", line);
                return ACLResult::faild("invalid line format");
            }
        }

        ACLResult::ok("Users loaded successfully")
    }
}
