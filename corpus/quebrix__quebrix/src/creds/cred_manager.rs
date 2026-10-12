use crate::known_directories::KNOWN_DIRECTORIES;
use crate::logger::logger_manager::Logger;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{self, OpenOptions};
use std::io::{self, BufRead, BufReader, Write};
use std::path::PathBuf;
use std::str::FromStr;

use super::acl_add_user::IAddUser;
use super::del_user::DeletUser;
use super::load_user_from_file::LoadUserFromFile;
use super::role_manager::IRoleManager;
use crate::crypto::crypto_service::Encryptor;

#[derive(Clone, Debug, Serialize)]
pub struct User {
    pub username: String,
    pub password: Vec<u8>,
    pub role: RoleManagement,
}

#[derive(Clone, Debug, Serialize)]
pub struct ACLResult<'a> {
    pub is_success: bool,
    pub message: &'a str,
}

impl<'a> ACLResult<'a> {
    pub fn ok(message: &'a str) -> Self {
        ACLResult {
            is_success: true,
            message: message,
        }
    }

    pub fn faild(message: &'a str) -> Self {
        ACLResult {
            is_success: false,
            message: message,
        }
    }
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
pub enum RoleManagement {
    Admin = 0,
    Developer = 1,
}

impl FromStr for RoleManagement {
    type Err = ParseUserRoleError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.to_lowercase().as_str() {
            "admin" => Ok(RoleManagement::Admin),
            "developer" => Ok(RoleManagement::Developer),
            _ => Err(ParseUserRoleError),
        }
    }
}

impl RoleManagement {
    fn as_str(&self) -> &str {
        match self {
            RoleManagement::Admin => "Admin",
            RoleManagement::Developer => "Developer",
        }
    }

    pub fn can_manage_users(&self) -> bool {
        *self == RoleManagement::Admin
    }

    pub fn can_manage_cache(&self) -> bool {
        *self == RoleManagement::Admin || *self == RoleManagement::Developer
    }
}

#[derive(Debug)]
pub struct ParseUserRoleError;

impl std::fmt::Display for ParseUserRoleError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "Invalid user role")
    }
}

impl std::error::Error for ParseUserRoleError {}

pub struct CredsManager {
    pub users: HashMap<String, User>,
    pub enable_log: bool,
}

pub const ENCRYPT_KEY: &str = "QWERTYUIOPASdfgCBxzjfndeuAQwudhAsd";
pub const IV_PATTERN: [u8; 16] = [2, 2, 5, 8, 5, 1, 3, 5, 6, 7, 9, 1, 6, 4, 1, 9];

impl CredsManager {
    pub fn new(enable_log: bool) -> Self {
        let mut creds_manager = CredsManager {
            users: HashMap::new(),
            enable_log: enable_log,
        };
        creds_manager.load_users_from_file();
        if creds_manager.enable_log == true {
            let message = &format!("Users loaded : {:?}", creds_manager.users);
            let set_log = Logger::log_info_data(message);
            set_log.write_log_to_file();
        }
        creds_manager
    }

    pub fn get_user(&self, username: &str) -> User {
        self.users.get(username).unwrap().clone()
    }

    pub fn create_admin(&mut self) {
        let kn_dir = &KNOWN_DIRECTORIES;

        let users_file = PathBuf::from(&kn_dir.creds_directory).join("users.txt");

        if !users_file.exists() {
            fs::File::create(&users_file).unwrap();
            self.add_user(
                "admin".to_string(),
                "123456".to_string(),
                RoleManagement::Admin,
                None,
            );
        }
    }

    // Write a new user to the file
    pub fn write_user_to_file(&self, username: &str) -> io::Result<()> {
        let kn_dir = &KNOWN_DIRECTORIES;

        let users_file = PathBuf::from(&kn_dir.creds_directory).join("users.txt");

        if !users_file.exists() {
            fs::File::create(&users_file)?;
        }

        let user = self.users.get(username).unwrap();
        let mut file = OpenOptions::new().append(true).open(users_file)?;
        writeln!(
            file,
            "{}:{:?}:{}",
            user.username,
            user.password,
            user.role.as_str()
        )?;
        Ok(())
    }
}
