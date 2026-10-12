use std::{
    collections::HashMap,
    time::{Duration, Instant},
};

use crate::{logger::logger_manager::Logger, persistent::persistent_Manager};

use super::{cache::CacheType, Cache};

pub trait Set {
    fn set(
        &mut self,
        cluster: String,
        key: String,
        value: Vec<u8>,
        ttl: Option<Duration>,
        ignore_persistent: bool,
    ) -> bool;
}

impl Set for Cache {
    fn set(
        &mut self,
        cluster: String,
        key: String,
        value: Vec<u8>,
        ttl: Option<Duration>,
        ignore_persistent: bool,
    ) -> bool {
        let memory_usage = std::mem::size_of_val(&value);

        // Check if the memory limit is reached
        let over_limit = {
            let memory_handler = self.memory_handler.lock().unwrap();
            memory_handler.is_memory_limit_finished()
        };

        if over_limit {
            println!("Memory limit exceeded. Evicting entries...");
            self.evict_entries();
            if self.enable_log {
                let memory_handler_log =
                    Logger::log_warn("Memory limit exceeded. Evicting entries");
                memory_handler_log.write_log_to_file();
            }
        }

        // Acquire memory handler lock once for both the check and memory addition
        let mut memory_handler = self.memory_handler.lock().unwrap();
        if !memory_handler.is_memory_limit_finished()
        {
            let mut store = self.store.lock().unwrap();
            let cluster_store = store.entry(cluster.clone()).or_insert_with(HashMap::new);
            let expiration_time = ttl.map(|duration| Instant::now() + duration);
            cluster_store.insert(
                key.clone(),
                (value.clone(), expiration_time, ttl, CacheType::Str),
            );
            memory_handler.add_memory(memory_usage);

            if self.enable_log {
                let set_log = Logger::log_info("Set value in cluster");
                set_log.write_log_to_file();
            }
            if self.persistent && !ignore_persistent && ttl.is_none() {
                let command = format!("SET {} {} {:?}", cluster, key, value);
                persistent_Manager::write_to_persistent_file(&command);
            }
            return true;
        } else {
            println!("Failed to set value: Memory usage has exceeded the configured limit. Update your configuration JSON file.");
            if self.enable_log {
                let error_set_log = Logger::log_info("Failed to set value: Memory usage has exceeded the configured limit. Update your configuration JSON file.");
                error_set_log.write_log_to_file();
            }
            return false;
        }
    }
}
