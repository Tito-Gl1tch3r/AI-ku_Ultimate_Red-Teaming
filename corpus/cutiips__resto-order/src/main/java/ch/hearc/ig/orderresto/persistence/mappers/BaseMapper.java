package ch.hearc.ig.orderresto.persistence.mappers;

import ch.hearc.ig.orderresto.persistence.IdentityMap;

import java.util.Optional;

/**
 * 🌐 BaseMapper - Abstract class providing basic caching operations for persistence mappers.
 * <p>
 * Manages caching of entities by ID to improve performance and reduce redundant database access.
 * Utilizes an {@link IdentityMap} to store and retrieve cached objects.
 *
 * @param <T> The type of entity managed by the mapper.
 */
public abstract class BaseMapper<T> {
    protected final IdentityMap<T> identityMap = new IdentityMap<>();

    /**
     * 🔍 Finds an entity in the cache.
     *
     * @param id The ID of the entity to find.
     * @return An {@link Optional} containing the entity if found, or empty if not in cache.
     */
    protected Optional<T> findInCache(Long id) {
        return Optional.ofNullable(identityMap.get(id));
    }

    /**
     * 💾 Adds an entity to the cache.
     *
     * @param id     The ID of the entity.
     * @param entity The entity to add to the cache.
     */
    protected void addToCache(Long id, T entity) {
        identityMap.put(id, entity);
    }

    /**
     * 🔄 Updates an entity in the cache.
     *
     * @param id     The ID of the entity.
     * @param entity The entity to update in the cache.
     */
    protected void updateInCache(Long id, T entity) {
        identityMap.put(id, entity);
    }

    /**
     * 🗑️ Removes an entity from the cache.
     *
     * @param id The ID of the entity to remove from the cache.
     */
    protected void removeFromCache(Long id) {
        identityMap.remove(id);
    }
}

