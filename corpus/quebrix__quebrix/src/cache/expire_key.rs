use super::Cache;
use std::collections::HashMap;
use std::time::Instant;

pub trait ExpireKey {
    fn expire_key(&mut self, cluster: &String, key: &String, new_ttl: &u64) -> bool;
}

impl ExpireKey for Cache {
    fn expire_key(&mut self, cluster: &String, key: &String, new_ttl: &u64) -> bool {
        let mut store = self.store.lock().unwrap();
        let cluster_store = store.entry(cluster.clone()).or_insert_with(HashMap::new);
        let duration = Option::Some(std::time::Duration::from_millis(*new_ttl));
        let expiration_time = duration.map(|dr| Instant::now() + dr);
        if let Some((value, expite_time, ttl, _)) = cluster_store.get_mut(key) {
            *expite_time = expiration_time;
            *ttl = Option::Some(std::time::Duration::from_millis(*new_ttl));
            true
        } else {
            false
        }
    }
}
