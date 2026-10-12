use std::collections::HashMap;

use crate::logger::logger_manager::Logger;

use super::Cache;

pub trait SetCluster {
    fn set_cluster(&self, cluster: String);
}

impl SetCluster for Cache {
    fn set_cluster(&self, cluster: String) {
        let mut store = self.store.lock().unwrap();
        store.entry(cluster).or_insert_with(HashMap::new);
        if self.enable_log == true {
            let set_cluster_log = Logger::log_info("cluster set ");
            set_cluster_log.write_log_to_file();
        }
    }
}
