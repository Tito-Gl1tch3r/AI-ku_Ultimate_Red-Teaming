package de.d3adspace.phoenix.repository.map;

import de.d3adspace.phoenix.repository.crud.AbstractCrudRepository;
import de.d3adspace.phoenix.repository.helper.EntityIdHelper;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

/**
 * A map based crud repository that can store entities in an arbitrary {@link Map} implementation.
 *
 * @param <EntityType> The generic type of the entity.
 * @param <EntityIdType> The generic type of the entity id.
 */
public abstract class AbstractMapCrudRepository<EntityType, EntityIdType> extends
    AbstractCrudRepository<EntityType, EntityIdType> {

  /**
   * The actual storage map.
   */
  private final Map<EntityIdType, EntityType> storage;

  /**
   * Create a new repository by the class of the entity it should store and the actual storage.
   *
   * @param entityClass The entities class.
   * @param storage The map storage.
   */
  protected AbstractMapCrudRepository(Class<EntityType> entityClass,
      Map<EntityIdType, EntityType> storage) {
    super(entityClass);

    Objects.requireNonNull(storage, "Storage map cannot be null.");

    this.storage = storage;
  }

  /**
   * Get the underlying storage map.
   *
   * @return The underlying storage map.
   */
  protected Map<EntityIdType, EntityType> getStorage() {
    return storage;
  }

  @Override
  public EntityType save(EntityType entity) {

    Objects.requireNonNull(entity, "Entity cannot be null.");

    EntityIdType entityId = EntityIdHelper.getId(entity);
    if (entityId == null) {

      EntityIdHelper.setId(entity, nextId());
    }

    storage.put(entityId, entity);
    return entity;
  }

  /**
   * Generate the next available id.
   *
   * @return The entity id.
   */
  protected abstract EntityIdType nextId();

  @Override
  public Optional<EntityType> find(EntityIdType id) {

    Objects.requireNonNull(id, "Entity id cannot be null.");

    return Optional.ofNullable(storage.get(id));
  }

  @Override
  public List<EntityType> findAll() {

    return new ArrayList<>(storage.values());
  }

  @Override
  public void delete(EntityType entity) {

    Objects.requireNonNull(entity, "Entity cannot be null.");

    storage.values().remove(entity);
  }

  @Override
  public void deleteAll() {

    storage.clear();
  }

  @Override
  public long count() {

    return storage.size();
  }
}
