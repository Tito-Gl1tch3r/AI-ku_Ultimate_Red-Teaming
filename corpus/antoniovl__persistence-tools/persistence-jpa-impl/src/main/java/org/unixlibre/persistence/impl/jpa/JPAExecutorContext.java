package org.unixlibre.persistence.impl.jpa;

import org.unixlibre.persistence.ExecutorContext;

import javax.persistence.EntityManager;

/**
 * Created by antoniovl on 12/05/17.
 */
public class JPAExecutorContext extends ExecutorContext {

    private EntityManager entityManager;

    public JPAExecutorContext() {
    }

    public JPAExecutorContext(EntityManager entityManager) {
        this.entityManager = entityManager;
    }

    public EntityManager getEntityManager() {
        return entityManager;
    }

    public void setEntityManager(EntityManager entityManager) {
        this.entityManager = entityManager;
    }

    public static Builder newBuilder() {
        return new Builder();
    }

    public static class Builder {
        private EntityManager entityManager;
        private Boolean supportsNestedTransactions;
        private Boolean rollbackOnApplicationException;

        public Builder setEntityManager(EntityManager entityManager) {
            this.entityManager = entityManager;
            return this;
        }

        public Builder setSupportsNestedTransactions(Boolean supportsNestedTransactions) {
            this.supportsNestedTransactions = supportsNestedTransactions;
            return this;
        }

        public Builder setRollbackOnApplicationException(Boolean rollbackOnApplicationException) {
            this.rollbackOnApplicationException = rollbackOnApplicationException;
            return this;
        }

        public JPAExecutorContext build() {
            JPAExecutorContext ctx = new JPAExecutorContext(entityManager);
            if (supportsNestedTransactions != null) {
                ctx.setSupportsNestedTransaction(supportsNestedTransactions);
            }
            if (rollbackOnApplicationException != null) {
                ctx.setRollbackOnApplicationException(rollbackOnApplicationException);
            }
            return ctx;
        }
    }

    public static JPAExecutorContext instance(ExecutorContext executorContext) {
        if (executorContext instanceof JPAExecutorContext) {
            return (JPAExecutorContext)executorContext;
        }
        return null;
    }
}
