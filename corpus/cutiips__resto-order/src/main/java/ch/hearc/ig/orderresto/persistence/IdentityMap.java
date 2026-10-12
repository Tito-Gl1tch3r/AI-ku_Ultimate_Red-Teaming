package ch.hearc.ig.orderresto.persistence;

import java.util.HashMap;
import java.util.Map;

/**
 * 🗃️ IdentityMap - Cache for storing and retrieving entities by their ID.
 * <p>
 * Provides a local in-memory cache to improve performance and avoid redundant database queries.
 *
 * @param <T> The type of entities stored in the cache.
 */
public class IdentityMap<T> {
    private final Map<Long, T> cache = new HashMap<>();

    /**
     * 🔍 Retrieves an entity from the cache by its ID.
     *
     * @param id The ID of the entity to retrieve.
     * @return The entity associated with the given ID, or {@code null} if not present in cache.
     */
    public T get(Long id) {
        return cache.get(id);
    }

    /**
     * 💾 Adds a new entity to the cache.
     *
     * @param id     The ID of the entity.
     * @param entity The entity to add to the cache.
     */
    public void put(Long id, T entity) {
        cache.put(id, entity);
    }

    /**
     * 🗑️ Removes an entity from the cache by its ID.
     *
     * @param id The ID of the entity to remove.
     */
    public void remove(Long id) {
        cache.remove(id);
    }

    /**
     * ❓ Checks if an entity is present in the cache.
     *
     * @param id The ID of the entity to check.
     * @return {@code true} if the entity is in the cache, {@code false} otherwise.
     */
    public boolean contains(Long id) {
        return cache.containsKey(id);
    }
}
