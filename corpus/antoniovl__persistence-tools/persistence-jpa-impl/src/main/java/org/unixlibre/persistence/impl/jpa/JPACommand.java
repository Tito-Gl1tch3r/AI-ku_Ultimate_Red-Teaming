package org.unixlibre.persistence.impl.jpa;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.unixlibre.persistence.Command;
import org.unixlibre.persistence.CommandException;
import org.unixlibre.persistence.ExecutorContext;

import javax.naming.InitialContext;
import javax.naming.NamingException;
import javax.persistence.EntityManager;
import javax.persistence.EntityTransaction;
import javax.transaction.*;
import java.util.function.Supplier;

/**
 * Created by antoniovl on 07/05/17.
 */
public class JPACommand<T> extends Command<T> {

    private static final Logger logger = LoggerFactory.getLogger(JPACommand.class);

    /**
     * UserTransaction Supplier.
     * The default implementation gets a transaction from JNDI.
     */
    private Supplier<UserTransaction> userTransactionSupplier = () -> {
        try {
            InitialContext initialContext = new InitialContext();
            UserTransaction utx = (UserTransaction)initialContext.lookup("java:comp/UserTransaction");
            // Don't think this case its going to happen
            if (utx == null) {
                logger.error("InitialContext.lookup() returned a null UserTransaction");
                throw new IllegalStateException("Got null UserTransaction");
            }
            return utx;
        } catch (NamingException ex) {
            // Error getting the transaction
            logger.error("Error found while getting the UserTransaction", ex);
            throw new CommandException(ex);
        }
    };

    @Override
    public void runWithLocalTx(ExecutorContext executorContext) {

        if (executorContext == null) {
            throw new IllegalArgumentException("Null executorContext provided");
        } else if (!(executorContext instanceof JPAExecutorContext)) {
            throw new IllegalArgumentException(("The ExecutorContext is not an instance of JPAExecutorContext"));
        }

        JPAExecutorContext ctx = (JPAExecutorContext)executorContext;

        EntityManager entityManager = ctx.getEntityManager();
        EntityTransaction tx = entityManager.getTransaction();
        boolean joinedTx = false;

        if (tx == null) {
            throw new IllegalStateException("getTransaction() returned null");
        }

        try {
            if (!tx.isActive()) {
                tx.begin();
            } else {
                joinedTx = true;
            }

            execute(executorContext);

            if (!joinedTx) {
                tx.commit();
            }

        } catch (Exception e) {
            boolean canRollback = e instanceof RuntimeException || ctx.isRollbackOnApplicationException();
            if (tx.isActive() && canRollback) {
                tx.rollback();
            }
            throw e;
        } finally {
            closeEntityManager(entityManager, joinedTx);
        }
    }

    @Override
    public void runWithUserTx(ExecutorContext executorContext) {
        if (executorContext == null) {
            throw new IllegalArgumentException("Null executorContext provided");
        }

        JPAExecutorContext ctx = (JPAExecutorContext)executorContext;
        EntityManager entityManager = ctx.getEntityManager();
        boolean joinedTx = false;

        UserTransaction utx  = getUserTransactionSupplier().get();

        try {
            joinedTx = (utx.getStatus() == Status.STATUS_ACTIVE);
        } catch (SystemException ex) {
            // Error getting the transaction
            logger.error("SystemException caught while getting the UserTransaction status", ex);
            throw new CommandException(ex);
        }
        /*
         * Process
         */
        try {
            if (ctx.isSupportsNestedTransaction() || !joinedTx) {
                utx.begin();
                joinedTx = true;
            }

            init();
            execute(executorContext);
            destroy();

            if (ctx.isSupportsNestedTransaction() || !joinedTx) {
                utx.commit();
            }
        } catch (RuntimeException re) {
            logger.error("RuntimeException instance caught", re);
            rollbackUserTransaction(utx);
        } catch (NotSupportedException nse) {
            logger.error("Transaction not supported", nse);
        } catch (SystemException ex) {
            logger.error("SystemException caught", ex);
            // Rollback if possible
            rollbackUserTransaction(utx);
        } catch (HeuristicRollbackException | HeuristicMixedException he) {
            // Thrown by UserTransaction.commit()
            logger.error("Transaction rolled back totally or partially by heuristics", he);
            // Rollback everything if possible.
            rollbackUserTransaction(utx);
        } catch (RollbackException rbe) {
            // Thrown by UserTransaction.commit()
            logger.error("The UserTransaction was rolled back", rbe);
        } finally {
            closeEntityManager(entityManager, joinedTx);
        }
    }

    private void rollbackUserTransaction(UserTransaction utx) {
        try {
            if (utx.getStatus() == Status.STATUS_ACTIVE) {
                utx.rollback();
                logger.debug("UserTransaction rolled back.");
            }
        } catch (SystemException ex) {
            logger.error("SystemException caught in UserTransaction.rollback()", ex);
            throw new CommandException(ex);
        }
    }

    private void closeEntityManager(EntityManager entityManager, boolean joinedTx) {
        if (entityManager != null && entityManager.isOpen() && !joinedTx) {
            entityManager.close();
        }
    }

    public Supplier<UserTransaction> getUserTransactionSupplier() {
        return userTransactionSupplier;
    }

    public void setUserTransactionSupplier(Supplier<UserTransaction> userTransactionSupplier) {
        if (userTransactionSupplier != null) {
            this.userTransactionSupplier = userTransactionSupplier;
        }
    }
}
