use crate::convert::vec_to_i32;
use crate::creds::cred_manager::CredsManager;
use crate::known_directories::KNOWN_DIRECTORIES;
use crate::logger::logger_manager::Logger;
use crate::memory_handling;
use chrono::prelude::*;
use core::str;
use rand::seq::SliceRandom;
use serde::Serialize;
use std::collections::HashMap;
use std::fs::OpenOptions;
use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use super::clear_all::ClearAll;
use super::clear_cluster::ClearCluster;
use super::decr::Decr;
use super::delete::Delete;
use super::incr::Incr;
use super::set::Set;

#[derive(Clone, Serialize, Debug)]
pub enum CacheType {
    Str = 1,
    Int = 2,
}

impl CacheType {
    pub fn as_i32(&self) -> &i32 {
        match self {
            CacheType::Int => &1,
            CacheType::Str => &2,
        }
    }
    pub fn as_str(&self) -> &str {
        match self {
            CacheType::Int => "integer",
            CacheType::Str => "string",
        }
    }
}

#[derive(Clone, Serialize)]
pub struct ResultValue {
    pub value: Option<Vec<u8>>,
    pub value_type: Option<CacheType>,
}

#[derive(Clone)]
pub struct Cache {
    pub evict_type: i32,
    pub store: Arc<
        Mutex<
            HashMap<
                String,
                HashMap<String, (Vec<u8>, Option<Instant>, Option<Duration>, CacheType)>,
            >,
        >,
    >,
    pub port: u16,
    pub memory_handler: Arc<Mutex<memory_handling::memory_handling::MemoryHandler>>,
    pub enable_log: bool,
    pub creds_manager: Arc<Mutex<CredsManager>>,
    pub persistent: bool,
}

impl Cache {
    pub fn new(
        port_number: u16,
        memory_handler: Arc<Mutex<memory_handling::memory_handling::MemoryHandler>>,
        evict_type: i32,
        enable_logs: bool,
        persistent: bool,
        creds: Arc<Mutex<CredsManager>>,
    ) -> Self {
        let mut cache = Cache {
            store: Arc::new(Mutex::new(HashMap::new())),
            port: port_number,
            memory_handler,
            evict_type,
            enable_log: enable_logs,
            persistent,
            creds_manager: creds,
        };

        if persistent {
            cache.initialize_from_commands();
        }

        cache
    }

    pub fn initialize_from_commands(&mut self) {
        let now: DateTime<Local> = Local::now();
        let kn_dirs = &KNOWN_DIRECTORIES;

        let persistent_file_name = format!(
            "{}/persistent_{}.qbx",
            &kn_dirs.persistent_directory.display(),
            now.format("%d-%m-%Y")
        );

        let open_file_result = OpenOptions::new().read(true).open(PathBuf::from(
            &kn_dirs.app_root_directory.join(persistent_file_name),
        ));

        if let Ok(file) = open_file_result {
            let reader = BufReader::new(file);

            for line in reader.lines() {
                if let Ok(command) = line {
                    let trimmed_command = command.trim_matches(|c| c == '\"');
                    let _ = self.execute_command(&trimmed_command);
                    let message = format!(
                        "from persistent => command:{:?} executed successfully",
                        &command
                    );
                    let log = Logger::log_info_data(&message);
                    log.write_log_to_file();
                }
            }
        } else {
            let log =
                Logger::log_warn("No persistent command file found, starting with empty cache.");
            log.write_log_to_file();
        }
    }

    fn parse_persistent_command(command: &str) -> Option<(String, String, Vec<u8>)> {
        let cleaned_input = command
            .trim_start_matches('[')
            .trim_end_matches(']')
            .trim_start_matches('"')
            .trim_end_matches('"');
        let (before_bracket, after_bracket) =
            cleaned_input.split_once('[').unwrap_or((cleaned_input, ""));
        let (inside_bracket, after_closing_bracket) =
            after_bracket.split_once(']').unwrap_or((after_bracket, ""));
        let inside_bracket_cleaned = inside_bracket.replace(" ", "");
        let normalized = format!(
            "{}[{}]{}",
            before_bracket, inside_bracket_cleaned, after_closing_bracket
        );

        let parts: Vec<&str> = normalized.split_whitespace().collect();
        if parts.len() == 4 {
            let trimmed = parts[3].trim_matches(|c| c == '[' || c == ']');
            let bytes: Vec<u8> = trimmed
                .split(",")
                .map(|s| s.parse().expect("Invalid byte"))
                .collect();
            Some((parts[1].to_string(), parts[2].to_string(), bytes))
        } else {
            None
        }
    }

    fn execute_command(&mut self, command: &str) {
        let parts: Vec<&str> = command.split_whitespace().collect();
        if parts.is_empty() {
            return;
        }
        match parts[0] {
            "SET" => {
                if let Some((cluster, key, value)) = Self::parse_persistent_command(command) {
                    self.set(cluster, key, value, None, true);
                }
            }
            "INCR" => {
                if let Some((cluster, key, value)) = Self::parse_persistent_command(command) {
                    let main_value = vec_to_i32(value);
                    self.incr(cluster, key, main_value, true);
                }
            }
            "DECR" => {
                if let Some((cluster, key, value)) = Self::parse_persistent_command(command) {
                    let main_value = vec_to_i32(value);
                    self.decr(cluster, key, main_value, true);
                }
            }
            "DEL" => {
                if parts.len() == 3 {
                    let cluster = parts[1].to_string();
                    let key = parts[2].to_string();
                    self.delete(&cluster.as_str(), &key.as_str(), true)
                }
            }
            "CLEAR_CLUSTER" => {
                if parts.len() == 2 {
                    let cluster = parts[1];
                    self.clear_cluster(cluster, true);
                }
            }
            "CLEAR_ALL" => self.clear_all(true),
            _ => println!("Unknown command: {}", command),
        }
    }

    pub fn configure_default_port(&mut self, port: u16) {
        self.port = port;
    }

    pub fn get_default_port(&self) -> u16 {
        self.port
    }

    // Eviction strategies
    pub fn evict_entries(&self) {
        let mut store = self.store.lock().unwrap();
        let mut memory_handler = self.memory_handler.lock().unwrap();
        let eviction_strategy = EvictionStrategy::from_i32(self.evict_type);
        match eviction_strategy.unwrap() {
            EvictionStrategy::VolatileLru => {
                self.evict_volatile_lru(&mut store, &mut memory_handler)
            }
            EvictionStrategy::AllKeysLru => self.evict_allkeys_lru(&mut store, &mut memory_handler),
            EvictionStrategy::AllKeysRandom => {
                self.evict_allkeys_random(&mut store, &mut memory_handler)
            }
            EvictionStrategy::VolatileTtl => {
                self.evict_volatile_ttl(&mut store, &mut memory_handler)
            }
        }
    }

    fn evict_volatile_lru(
        &self,
        store: &mut HashMap<
            String,
            HashMap<String, (Vec<u8>, Option<Instant>, Option<Duration>, CacheType)>,
        >,
        memory_handler: &mut memory_handling::memory_handling::MemoryHandler,
    ) {
        let mut lru_key: Option<(String, String)> = None;

        // Find the least recently used key among those with an expiration set
        for (cluster_key, cluster_store) in store.iter() {
            for (key, (_, expiration_time, _, _)) in cluster_store {
                if let Some(exp) = expiration_time {
                    if exp > &Instant::now() {
                        if lru_key.is_none() {
                            lru_key = Some((cluster_key.clone(), key.clone()));
                        }
                    }
                }
            }
        }

        // Evict the LRU key
        if let Some((cluster_key, key_to_evict)) = lru_key {
            if let Some(cluster_store) = store.get_mut(&cluster_key) {
                if let Some((value, _, _, _)) = cluster_store.remove(&key_to_evict) {
                    let memory_usage = std::mem::size_of_val(&value);
                    memory_handler.delete_memory(memory_usage);
                    println!(
                        "Evicted [{}] from cluster [{}] using volatile LRU strategy",
                        key_to_evict, cluster_key
                    );
                }
            }
        }
    }

    fn evict_volatile_ttl(
        &self,
        store: &mut HashMap<
            String,
            HashMap<String, (Vec<u8>, Option<Instant>, Option<Duration>, CacheType)>,
        >,
        memory_handler: &mut memory_handling::memory_handling::MemoryHandler,
    ) {
        let mut shortest_ttl_key: Option<(String, String, Instant)> = None;

        // Find the key with the shortest TTL among those with an expiration set
        for (cluster_key, cluster_store) in store.iter() {
            for (key, (_, expiration_time, _, _)) in cluster_store {
                if let Some(exp) = expiration_time {
                    if exp > &Instant::now() {
                        if shortest_ttl_key.is_none() {
                            shortest_ttl_key = Some((cluster_key.clone(), key.clone(), *exp));
                        }
                    }
                }
            }
        }

        // Evict the key with the shortest TTL
        if let Some((cluster_key, key_to_evict, _)) = shortest_ttl_key {
            if let Some(cluster_store) = store.get_mut(&cluster_key) {
                if let Some((value, _, _, _)) = cluster_store.remove(&key_to_evict) {
                    let memory_usage = std::mem::size_of_val(&value);
                    memory_handler.delete_memory(memory_usage);
                    println!(
                        "Evicted [{}] from cluster [{}] using volatile TTL strategy",
                        key_to_evict, cluster_key
                    );
                }
            }
        }
    }

    fn evict_allkeys_lru(
        &self,
        store: &mut HashMap<
            String,
            HashMap<String, (Vec<u8>, Option<Instant>, Option<Duration>, CacheType)>,
        >,
        memory_handler: &mut memory_handling::memory_handling::MemoryHandler,
    ) {
        let mut lru_key: Option<(String, String)> = None;

        // Find the least recently used key regardless of expiration
        for (cluster_key, cluster_store) in store.iter() {
            for (key, (_, _expiration_time, _, _)) in cluster_store {
                if lru_key.is_none() {
                    lru_key = Some((cluster_key.clone(), key.clone()));
                }
            }
        }

        // Evict the LRU key
        if let Some((cluster_key, key_to_evict)) = lru_key {
            if let Some(cluster_store) = store.get_mut(&cluster_key) {
                if let Some((value, _, _, _)) = cluster_store.remove(&key_to_evict) {
                    let memory_usage = std::mem::size_of_val(&value);
                    memory_handler.delete_memory(memory_usage);
                    println!(
                        "Evicted [{}] from cluster [{}] using allkeys LRU strategy",
                        key_to_evict, cluster_key
                    );
                }
            }
        }
    }

    fn evict_allkeys_random(
        &self,
        store: &mut HashMap<
            String,
            HashMap<String, (Vec<u8>, Option<Instant>, Option<Duration>, CacheType)>,
        >,
        memory_handler: &mut memory_handling::memory_handling::MemoryHandler,
    ) {
        let keys: Vec<(String, String)> = store
            .iter()
            .flat_map(|(cluster_key, cluster_store)| {
                cluster_store
                    .iter()
                    .map(|(key, (_value, _, _, _))| (cluster_key.clone(), key.clone()))
                    .collect::<Vec<_>>()
            })
            .collect();

        if let Some((cluster_key, key_to_evict)) = keys.choose(&mut rand::thread_rng()) {
            if let Some(cluster_store) = store.get_mut(cluster_key) {
                if let Some((value, _, _, _)) = cluster_store.remove(key_to_evict) {
                    let memory_usage = std::mem::size_of_val(&value);
                    memory_handler.delete_memory(memory_usage);
                    println!(
                        "Evicted [{}] from cluster [{}] using allkeys random strategy",
                        key_to_evict, cluster_key
                    );
                }
            }
        }
    }
}

//strategy
enum EvictionStrategy {
    VolatileLru,
    VolatileTtl,
    AllKeysLru,
    AllKeysRandom,
}
impl EvictionStrategy {
    pub fn from_i32(value: i32) -> Option<EvictionStrategy> {
        match value {
            0 => Some(EvictionStrategy::VolatileLru),
            1 => Some(EvictionStrategy::VolatileTtl),
            2 => Some(EvictionStrategy::AllKeysLru),
            3 => Some(EvictionStrategy::AllKeysRandom),
            _ => {
                println!("invalid EvictionStrategy passing in json");
                return None;
            }
        }
    }
}
