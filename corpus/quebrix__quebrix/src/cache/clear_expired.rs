use std::time::Instant;

use super::Cache;

pub trait ClearExpired {
    fn clear_expired(&self);
}

impl ClearExpired for Cache {
    fn clear_expired(&self) {
        let mut store = self.store.lock().unwrap();

        for cluster_store in store.values_mut() {
            cluster_store.retain(|_, (_, expiration_time, _, _)| {
                if let Some(exp) = expiration_time {
                    exp > &mut Instant::now()
                } else {
                    true
                }
            });
        }
    }
}
