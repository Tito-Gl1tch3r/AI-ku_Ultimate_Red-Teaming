use crate::{logger::logger_manager::Logger, persistent::persistent_Manager};

use super::Cache;

pub trait ClearCluster {
    fn clear_cluster(&self, cluster: &str, ignore_persistent: bool);
}

impl ClearCluster for Cache {
    fn clear_cluster(&self, cluster: &str, ignore_persistent: bool) {
        let mut store = self.store.lock().unwrap();
        if let Some(cluster_store) = store.remove(cluster) {
            let mut memory_handler = self.memory_handler.lock().unwrap();
            let total_size: usize = cluster_store
                .values()
                .map(|(v, _, _, _)| std::mem::size_of_val(v))
                .sum();
            memory_handler.delete_memory(total_size);
            if self.enable_log == true {
                let clear_cluster_log = Logger::log_info("cluster cleared ");
                clear_cluster_log.write_log_to_file();
                if self.persistent && !ignore_persistent {
                    let command = format!("CLEAR_CLUSTER {}", cluster.clone());
                    persistent_Manager::write_to_persistent_file(&command);
                }
            }
        }
    }
}
