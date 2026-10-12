use crate::{crypto::crypto_service::Encryptor, logger::logger_manager::Logger};

use super::cred_manager::{ACLResult, CredsManager, RoleManagement, User, ENCRYPT_KEY, IV_PATTERN};

pub trait IAddUser {
    fn add_user(
        &mut self,
        username: String,
        password: String,
        role: RoleManagement,
        current_user: Option<&User>,
    ) -> ACLResult;
}

impl IAddUser for CredsManager {
    fn add_user(
        &mut self,
        username: String,
        password: String,
        role: RoleManagement,
        current_user: Option<&User>,
    ) -> ACLResult {
        if current_user.is_some() {
            if !current_user.unwrap().role.can_manage_users() {
                if self.enable_log == true {
                    let message = "developer wants to add new profile : Access denied";
                    let set_log = Logger::log_warn(message);
                    set_log.write_log_to_file();
                }
                return ACLResult::faild("Permission denied: Admin role required to add users");
            }
        }
        let encryptor = Encryptor::new(ENCRYPT_KEY, IV_PATTERN);
        let hashed_password = encryptor.encrypt(&password);
        let user = User {
            username: username.clone(),
            password: hashed_password,
            role,
        };
        self.users.insert(username.clone(), user);
        self.write_user_to_file(&username);
        if self.enable_log == true {
            let message = &format!("new user added : {:?}", username.clone());
            let set_log = Logger::log_info_data(message);
            set_log.write_log_to_file();
        }
        return ACLResult::ok("new user added");
    }
}
