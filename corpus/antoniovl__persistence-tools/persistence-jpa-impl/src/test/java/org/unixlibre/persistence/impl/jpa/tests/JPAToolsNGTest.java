package org.unixlibre.persistence.impl.jpa.tests;

import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;
import org.unixlibre.persistence.impl.jpa.JPACommandManager;
import org.unixlibre.persistence.impl.jpa.JPAExecutorContext;
import org.unixlibre.persistence.impl.jpa.JPATools;
import org.unixlibre.persistence.impl.jpa.tests.model.Author;
import org.unixlibre.persistence.impl.jpa.tests.model.NoEntity;

import javax.persistence.EntityManager;
import javax.persistence.NonUniqueResultException;
import javax.persistence.PersistenceException;
import javax.persistence.TypedQuery;

import java.util.Optional;

import static org.testng.Assert.*;
import static org.unixlibre.persistence.impl.jpa.JPATools.PKLoadResult;

/**
 * Created by antoniovl on 13/05/17.
 */
public class JPAToolsNGTest extends BaseTest {

    private JPACommandManager commandManager;

    @BeforeClass
    public void setUp() throws Exception {
        commandManager = new JPACommandManager(new CommandExecutorImpl());
    }

    @AfterClass
    public void tearDown() throws Exception {
        JPATools.closeEntityManagerFactories();
    }

    @Test
    public void testLoadPK() throws Exception {
        NoEntity ne = new NoEntity();
        PKLoadResult pkLoadResult = JPATools.loadPK(ne);
        assertFalse(pkLoadResult.found());

        Author testAuthor = new Author(1L);
        pkLoadResult = JPATools.loadPK(testAuthor);
        assertTrue(pkLoadResult.found());
    }

    @Test(expectedExceptions = {PersistenceException.class})
    public void testGetCurrentEntity() throws Exception {
        Author author = new Author(1L);
        Author a2 = commandManager.execute(executorContext -> {
            JPAExecutorContext ctx = JPAExecutorContext.instance(executorContext);
            EntityManager entityManager = ctx.getEntityManager();
            return JPATools.getCurrentEntity(author, Author.class, entityManager);
        });
        assertEquals(author.getId(), a2.getId());

        commandManager.execute(executorContext -> {
            JPAExecutorContext ctx = JPAExecutorContext.instance(executorContext);
            EntityManager entityManager = ctx.getEntityManager();
            Author a3 = new Author(Long.MAX_VALUE - 100000000);
            return JPATools.getCurrentEntity(a3, Author.class, entityManager);
        });
    }

    @Test(expectedExceptions = {NonUniqueResultException.class})
    public void testGetSingleResult() throws Exception {
        final String query = "SELECT a FROM Author a WHERE a.id = :id ";
        /*
         * Test for existing entity
         */
        Optional<Author> authorOptional = commandManager.execute(executorContext -> {
            EntityManager entityManager = getEntityManager(executorContext);
            TypedQuery<Author> q = entityManager.createQuery(query, Author.class)
                    .setParameter("id", 1L);
            return JPATools.getSingleResult(q);
        });
        assertTrue(authorOptional.isPresent());
        assertEquals(authorOptional.get().getName(), "Author1");
        /*
         * Test for unexisting entity
         */
        authorOptional = commandManager.execute(executorContext -> {
            EntityManager entityManager = getEntityManager(executorContext);
            TypedQuery<Author> q = entityManager.createQuery(query, Author.class)
                    .setParameter("id", Long.MAX_VALUE - 100000000);
            return JPATools.getSingleResult(q);
        });
        assertFalse(authorOptional.isPresent());
        /*
         * Test for non unique result
         */
        commandManager.execute(executorContext -> {
            EntityManager entityManager = getEntityManager(executorContext);
            TypedQuery<Author> q = entityManager
                    .createQuery("SELECT a FROM Author a", Author.class);
            return JPATools.getSingleResult(q);
        });
    }


}
