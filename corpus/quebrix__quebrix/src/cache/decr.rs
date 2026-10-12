use std::collections::HashMap;

use crate::{
    convert::{i32_to_vec, vec_to_i32},
    logger::logger_manager::Logger,
    persistent::persistent_Manager,
};

use super::{cache::CacheType, get::Get, Cache};

pub trait Decr {
    fn decr(
        &mut self,
        cluster: String,
        key: String,
        value: Option<i32>,
        ignore_persistent: bool,
    ) -> bool;
}

impl Decr for Cache {
    fn decr(
        &mut self,
        cluster: String,
        key: String,
        value: Option<i32>,
        ignore_persistent: bool,
    ) -> bool {
        let mut deccrement_value: Option<Vec<u8>> = None;
        if value.is_some() {
            let main_value = Option::Some(value.as_ref().unwrap().to_le_bytes().to_vec());
            deccrement_value = main_value;
        } else {
            deccrement_value = Option::Some(i32_to_vec(1));
        }
        let memory_usage = std::mem::size_of_val(&deccrement_value);
        let get_cache = self.get(&cluster, &key);
        if get_cache.value.is_some() {
            // decrement logic
            let mut store = self.store.lock().unwrap();
            let cluster_store = store.entry(cluster.clone()).or_insert_with(HashMap::new);
            let current_value = cluster_store
                .entry(key.clone())
                .and_modify(|(existing_value, _, _, cache_type)| {
                    // Convert Vec<u8> to [u8; 4] and then to i32
                    let mut current_i32 =
                        i32::from_le_bytes(existing_value[..4].try_into().unwrap());
                    current_i32 -= vec_to_i32(deccrement_value.clone().unwrap()).unwrap();
                    // Update the value as Vec<u8>
                    *existing_value = current_i32.to_le_bytes().to_vec();
                })
                .or_insert((
                    deccrement_value.clone().unwrap(),
                    None,
                    None,
                    CacheType::Int,
                ))
                .0
                .clone();

            // Memory management
            let mut memory_handler = self.memory_handler.lock().unwrap();
            memory_handler.add_memory(memory_usage);

            // Persistence
            if self.enable_log {
                Logger::log_info(&format!(
                    "DECR in cluster {}: {} = {:?}",
                    cluster, key, current_value
                ))
                .write_log_to_file();
            }
            if self.persistent && !ignore_persistent {
                let command = format!("DECR {} {} {:?}", cluster, key, current_value);
                persistent_Manager::write_to_persistent_file(&command);
            }
            true
        } else {
            Logger::log_error(&format!(
                "DECR in cluster {}: {}  not set key not found",
                cluster, key
            ))
            .write_log_to_file();
            false
        }
    }
}
