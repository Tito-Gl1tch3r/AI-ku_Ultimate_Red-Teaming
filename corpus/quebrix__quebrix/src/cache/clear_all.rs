use crate::persistent::persistent_Manager;

use super::Cache;

pub trait ClearAll {
    fn clear_all(&self, ignore_persistent: bool);
}

impl ClearAll for Cache {
    fn clear_all(&self, ignore_persistent: bool) {
        let mut store = self.store.lock().unwrap();
        let mut memory_handler = self.memory_handler.lock().unwrap();
        let total_size: usize = store
            .values()
            .flat_map(|cluster_store| cluster_store.values())
            .map(|(v, _, _, _)| v.len())
            .sum();
        store.clear();
        memory_handler.delete_memory(total_size);
        if self.persistent && !ignore_persistent {
            let command = format!("CLEAR_ALL");
            persistent_Manager::write_to_persistent_file(&command);
        }
    }
}
