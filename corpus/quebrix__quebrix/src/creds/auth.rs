use crate::{crypto::crypto_service::Encryptor, logger::logger_manager::Logger};

use super::cred_manager::{CredsManager, ENCRYPT_KEY, IV_PATTERN};

pub trait Authenticator {
    fn authenticate(&self, username: &str, password: &str) -> bool;
}

impl Authenticator for CredsManager {
    fn authenticate(&self, username: &str, password: &str) -> bool {
        let encryptor = Encryptor::new(ENCRYPT_KEY, IV_PATTERN);

        if let Some(user) = self.users.get(username) {
            match encryptor.decrypt(&user.password) {
                Some(decrypted_password) => {
                    if decrypted_password == password {
                        return true;
                    } else {
                        if self.enable_log == true {
                            let message =
                                &format!("password not match with user : {:?}", username.clone());
                            let set_log = Logger::log_warn_data(message);
                            set_log.write_log_to_file();
                        }
                        println!("Passwords do not match for user: {}", username);
                        return false;
                    }
                }
                None => {
                    if self.enable_log == true {
                        let message = "Failed to decrypt password for login";
                        let set_log = Logger::log_error(message);
                        set_log.write_log_to_file();
                    }
                    println!("Failed to decrypt password for user: {}", username);
                    return false;
                }
            }
        } else {
            if self.enable_log == true {
                let message = &format!(
                    "Users [{}] with password:[{:?}] not found in login",
                    username, password
                );
                let set_log = Logger::log_info_data(message);
                set_log.write_log_to_file();
            }
            println!("User not found: {}:{:?}", username, password);
        }
        false
    }
}
