use std::{fs, path::PathBuf};

use super::cred_manager::{ACLResult, CredsManager};
use crate::{known_directories::KNOWN_DIRECTORIES, logger::logger_manager::Logger};

pub trait RemoveUserFromCredFile {
    fn remove_user_from_file(&self, username: &str) -> ACLResult;
}

impl RemoveUserFromCredFile for CredsManager {
    fn remove_user_from_file(&self, username: &str) -> ACLResult {
        let kn_dir = &KNOWN_DIRECTORIES;
        let users_file = PathBuf::from(&kn_dir.creds_directory).join("users.txt");

        if !users_file.exists() {
            return ACLResult::faild("directory not found");
        }

        let file_content = fs::read_to_string(&users_file).unwrap();

        let updated_content: String = file_content
            .lines()
            .filter(|line| !line.starts_with(username))
            .map(|line| format!("{}\n", line))
            .collect();

        fs::write(&users_file, updated_content);

        if self.enable_log {
            let message = &format!("user removed from file: {:?}", username);
            let set_log = Logger::log_info_data(message);
            set_log.write_log_to_file();
        }

        return ACLResult::ok("user removed from file");
    }
}
