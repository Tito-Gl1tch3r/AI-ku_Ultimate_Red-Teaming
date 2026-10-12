package de.d3adspace.phoenix.repository.helper;

import de.d3adspace.phoenix.annotations.Id;
import java.lang.reflect.Field;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class EntityIdHelper {

  private static final Map<Class<?>, EntityIdMeta> ENTITY_META = new ConcurrentHashMap<>();

  /**
   * Get the id of an entity.
   *
   * @param entity The entity.
   * @param <EntityType> The type of the entity.
   * @param <EntityIdType> The type of the entities id.
   * @return The entity id or null.
   */
  public static <EntityType, EntityIdType> EntityIdType getId(EntityType entity) {

    Class<?> entityClass = entity.getClass();
    EntityIdMeta entityIdMeta = getEntityIdMeta(entityClass);

    return (EntityIdType) entityIdMeta.get(entity);
  }

  public static <EntityType, EntityIdType> void setId(EntityType entity, EntityIdType nextId) {

    Class<?> entityClass = entity.getClass();
    EntityIdMeta entityIdMeta = getEntityIdMeta(entityClass);
    entityIdMeta.set(entity, nextId);
  }

  private static EntityIdMeta getEntityIdMeta(Class<?> entityClass) {

    if (ENTITY_META.containsKey(entityClass)) {
      return ENTITY_META.get(entityClass);
    }

    EntityIdMeta meta = readEntityIdMeta(entityClass);
    ENTITY_META.put(entityClass, meta);
    return meta;
  }

  private static EntityIdMeta readEntityIdMeta(Class<?> entityClass) {

    Field[] declaredFields = entityClass.getDeclaredFields();
    for (Field declaredField : declaredFields) {

      if (!declaredField.isAnnotationPresent(Id.class)) {
        continue;
      }

      return new EntityIdMeta(declaredField);
    }

    throw new IllegalStateException("Couldn't find id field. Are you sure there is a @Id field?");
  }

  private static class EntityIdMeta {

    private final Field field;

    private EntityIdMeta(Field field) {
      this.field = field;
      ensureAccessibleProperty();
    }

    private void ensureAccessibleProperty() {
      field.setAccessible(true);
    }

    public Object get(Object entity) {

      try {
        return field.get(entity);
      } catch (IllegalAccessException e) {
        e.printStackTrace();
      }

      return null;
    }

    public void set(Object entity, Object value) {

      try {
        field.set(entity, value);
      } catch (IllegalAccessException e) {
        e.printStackTrace();
      }
    }
  }
}
