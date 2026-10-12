package org.unixlibre.persistence.impl.jpa.tests;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;
import org.unixlibre.persistence.CommandManager;
import org.unixlibre.persistence.TransactionTypesEnum;
import org.unixlibre.persistence.impl.jpa.JPACommand;
import org.unixlibre.persistence.impl.jpa.JPACommandManager;
import org.unixlibre.persistence.impl.jpa.JPATools;
import org.unixlibre.persistence.impl.jpa.tests.model.Author;

import javax.persistence.EntityManager;
import javax.persistence.TypedQuery;
import javax.persistence.criteria.CriteriaBuilder;
import javax.persistence.criteria.CriteriaQuery;
import javax.persistence.criteria.ParameterExpression;
import javax.persistence.criteria.Root;
import java.util.Date;
import java.util.Optional;

import static org.mockito.Mockito.spy;
import static org.mockito.Mockito.when;
import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertTrue;

/**
 * Created by antoniovl on 18/05/17.
 */
public class JPACommandTest extends BaseTest {

    private static final Logger logger = LoggerFactory.getLogger(JPACommandTest.class);

    private CommandManager commandManager;

    @BeforeClass
    public void beforeClass() throws Exception {
        commandManager = new JPACommandManager(new CommandExecutorImpl());
    }
    @BeforeMethod
    public void setUp() throws Exception {
    }

    @AfterMethod
    public void tearDown() throws Exception {
    }

    @Test
    public void testNullExecutorContext() throws Exception {
        JPACommand cmd = new JPACommand();

        try {
            cmd.setTransactionType(TransactionTypesEnum.LOCAL);
            cmd.runWithLocalTx(null);
        } catch (IllegalArgumentException e) {

        }

        try {
            cmd.setTransactionType(TransactionTypesEnum.USER);
            cmd.runWithUserTx(null);
        } catch (IllegalArgumentException e) {

        }
    }

    @Test
    public void testRunWithLocalTx() throws Exception {
        // Count authors
        long count = countAuthors();
        /*
         * Test Commit
         */
        commandManager.execute(executorContext -> {
            EntityManager entityManager = getEntityManager(executorContext);
            Author author = new Author(null, "Author XYZ", new Date(), "author_xyz@gmail.com");
            entityManager.persist(author);
            logger.info("author(id: {}, name: {})", author.getId(), author.getName());
            return author;
        });
        long newCount = countAuthors();
        assertEquals(newCount, count+1);
        /*
         * Test Rollback
         */
        count = newCount;
        try {
            commandManager.execute(executorContext -> {
                EntityManager entityManager = getEntityManager(executorContext);
                Author author = new Author(null, "Author XYZ", new Date(), "author_xyz@gmail.com");
                entityManager.persist(author);
                logger.info("author(id: {}, name: {}) <== will be rolledback", author.getId(), author.getName());
                if (1 == 1) {
                    throw new RuntimeException("Force Rollback");
                }
                return author;
            });
        } catch (RuntimeException re) {
            logger.info("RuntimeException catched");
        }
        newCount = countAuthors();
        assertEquals(newCount, count);
    }

    @Test(enabled = false)
    public void testRunWithUserTx() throws Exception {
    }

    @Test(expectedExceptions = {IllegalArgumentException.class})
    public void testExecutionContextWithWrongType() throws Exception {
        CommandExecutorImpl commandExecutorImpl = spy(CommandExecutorImpl.class);
        // set wrong class type
        when(commandExecutorImpl.getContext()).thenReturn(new OtherExecutorContext());
        JPACommandManager manager = new JPACommandManager(commandExecutorImpl);
        Optional<Author> authorOptional = manager.execute(executorContext -> {
            EntityManager entityManager = getEntityManager(executorContext);
            CriteriaBuilder builder = entityManager.getCriteriaBuilder();
            CriteriaQuery<Author> criteria = builder.createQuery(Author.class);
            Root<Author> authorRoot = criteria.from(Author.class);
            criteria.select(authorRoot)
                    .where(
                            builder.equal(authorRoot.get("id"), 1L)
                    );
            TypedQuery<Author> q = entityManager.createQuery(criteria);
            return JPATools.getSingleResult(q);
        });
        assertTrue(authorOptional.isPresent());
    }

    private Long countAuthors() {
        return commandManager.execute(executorContext -> {
            EntityManager entityManager = getEntityManager(executorContext);
            TypedQuery<Long> q = entityManager
                    .createQuery("SELECT COUNT(a) FROM Author a ", Long.class);
            return q.getSingleResult();
        });
    }

}