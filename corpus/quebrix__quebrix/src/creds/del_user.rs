use super::{
    cred_manager::{self, ACLResult, User},
    remove_user_from_cred_file::RemoveUserFromCredFile,
};
use crate::Logger;
use std::io;

pub trait DeletUser {
    fn delete_user(&mut self, username: &str, current_user: Option<&User>) -> ACLResult;
}

impl DeletUser for cred_manager::CredsManager {
    fn delete_user(&mut self, username: &str, current_user: Option<&User>) -> ACLResult {
        if current_user.is_some() {
            if !current_user.unwrap().role.can_manage_users() {
                if self.enable_log {
                    let message = "developer wants to delete profile : Access denied";
                    let set_log = Logger::log_warn(message);
                    set_log.write_log_to_file();
                }
                return ACLResult::faild(
                    "Access denied:your role do not have access to run this command.",
                );
            }
        }

        if self.users.remove(username).is_none() {
            return ACLResult::faild("User not found");
        }

        let remove_result = self.remove_user_from_file(username);
        if !remove_result.is_success {
            return ACLResult::faild("can not remove from file");
        }

        if self.enable_log {
            let message = &format!("user deleted: {:?}", username);
            let set_log = Logger::log_info_data(message);
            set_log.write_log_to_file();
        }

        return ACLResult::ok("user deleted");
    }
}
