use crate::{logger::logger_manager::Logger, persistent::persistent_Manager};

use super::Cache;

pub trait Delete {
    fn delete(&self, cluster: &str, key: &str, ignore_persistent: bool);
}

impl Delete for Cache {
    fn delete(&self, cluster: &str, key: &str, ignore_persistent: bool) {
        let mut store = self.store.lock().unwrap();
        if let Some(cluster_store) = store.get_mut(cluster) {
            if let Some((value, _, _, _)) = cluster_store.remove(key) {
                let mut memory_handler = self.memory_handler.lock().unwrap();
                let memory_usage = std::mem::size_of_val(&value);
                memory_handler.delete_memory(memory_usage);
                if self.enable_log == true {
                    let delete_log = Logger::log_info("value deleted ");
                    delete_log.write_log_to_file();
                    if self.persistent && !ignore_persistent {
                        let command = format!("DEL {} {}", cluster.clone(), key.clone());
                        persistent_Manager::write_to_persistent_file(&command);
                    }
                }
            }
        }
    }
}
