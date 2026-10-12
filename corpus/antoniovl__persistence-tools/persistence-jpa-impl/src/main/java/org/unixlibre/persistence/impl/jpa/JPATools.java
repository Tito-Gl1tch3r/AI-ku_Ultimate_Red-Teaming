package org.unixlibre.persistence.impl.jpa;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.persistence.*;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

/**
 * Created by antoniovl on 13/05/17.
 */
public class JPATools {

    private static final Logger logger = LoggerFactory.getLogger(JPATools.class);
    private static final Map<String, EntityManagerFactory> factories =
            new HashMap<>();

    public static class PKLoadResult {

        private boolean found = true;
        private Object pk;
        private String message;

        public PKLoadResult(boolean found, Object pk) {
            this.found = found;
            this.pk = pk;
        }

        public PKLoadResult(boolean found, String message) {
            this.found = found;
            this.message = message;
        }

        public boolean found() {
            return found;
        }

        public Object getPk() {
            return this.pk;
        }

        public String getMessage() {
            return message;
        }
    }

    public static EntityManager getEntityManager(String persistenceUnit, Map overwrite) {

        EntityManagerFactory emf;

        synchronized (factories) {
            emf = factories.get(persistenceUnit);
            if (emf == null) {
                emf = Persistence.createEntityManagerFactory(persistenceUnit, overwrite);
                factories.put(persistenceUnit, emf);
            }
        }

        EntityManager entityManager = emf.createEntityManager();
        entityManager.setFlushMode(FlushModeType.AUTO);

        return entityManager;
    }

    public static EntityManager getEntityManager(String persistenceUnit) {
        return getEntityManager(persistenceUnit, new HashMap());
    }

    public static void closeEntityManagerFactories() {
        synchronized(factories) {
            factories.forEach((key, value) -> factories.get(key).close());
            factories.clear();
        }
    }

    public static <T> Optional<T> getSingleResult(Query query) {
        try {
            @SuppressWarnings("unchecked")
            T result = (T)query.getSingleResult();
            return Optional.of(result);
        } catch (NoResultException nre) {
            return Optional.empty();
        }
    }

    public static <T> Optional<T> getSingleResult(TypedQuery<T> q) {
        try {
            return Optional.of(q.getSingleResult());
        } catch (NoResultException e) {
            return Optional.empty();
        }
    }

    public static PKLoadResult loadPK(Object entity) {

        String id = null;
        StringBuilder s = new StringBuilder("get");

        Field[] fields = entity.getClass().getDeclaredFields();
        int k = fields.length;

        for (int i = 0; i < k; i++) {
            Field field = fields[i];
            if (field.isAnnotationPresent(javax.persistence.Id.class) ||
                    field.isAnnotationPresent(javax.persistence.EmbeddedId.class)) {
                id = field.getName();
                i = k + 1;
            }
        }

        if (id == null) {
            return new PKLoadResult(false,
                    "No property annotated with @Id or @EmbeddedId could be found");
        }

        String tmp = id.substring(0, 1).toUpperCase();
        s.append(tmp).append(id.substring(1));
        logger.debug("{} will be used for loading the Id", s.toString());

        try {
            Method method = entity.getClass().getMethod(s.toString(),
                    new Class[]{});
            Object pk = method.invoke(entity, new Object[]{});

            return new PKLoadResult(true, pk);

        } catch (NoSuchMethodException nsme) {
            logger.error("Exception found in JPATools.loadPK()", nsme);
            return new PKLoadResult(false,
                    nsme.getMessage());
        } catch (IllegalAccessException iae) {
            logger.error("Exception found in JPATools.loadPK()", iae);
            return new PKLoadResult(false,
                    iae.getMessage());
        } catch (InvocationTargetException ite) {
            logger.error("Exception found in JPATools.loadPK()", ite);
            return new PKLoadResult(false, ite.getMessage());
        }
    }


    public static <T> T getCurrentEntity(final Object entity,
                                         final Class<T> klass,
                                         final EntityManager entityManager) {

        StringBuilder sb = new StringBuilder("JPATools.getCurrentEntity(): ");

        if (entity == null) {
            throw new IllegalArgumentException("Null valued entity provided");
        }

        Object pk;
        PKLoadResult declaredId = loadPK(entity);

        if (!declaredId.found()) {
            String msg = (declaredId.getMessage() == null)
                    ? "@Id not found"
                    : declaredId.getMessage();
            throw new PersistenceException(msg);
        } else {
            pk = declaredId.getPk();
        }

        if (pk == null) {
            throw new PersistenceException("The @Id has a null value");
        }

        T currentEntity = entityManager.find(klass, pk);

        if (currentEntity == null) {
            sb.append("Entity of class ");
            sb.append(klass.getSimpleName());
            sb.append(" could not be found");
            throw new PersistenceException(sb.toString());
        }

        return currentEntity;

    }
}
