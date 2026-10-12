package org.unixlibre.persistence.impl.jpa.tests;

import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;
import org.unixlibre.persistence.CommandManager;
import org.unixlibre.persistence.impl.jpa.JPACommandManager;
import org.unixlibre.persistence.impl.jpa.QueryParams;
import org.unixlibre.persistence.impl.jpa.tests.model.Author;

import javax.persistence.EntityManager;
import javax.persistence.TypedQuery;

import java.util.HashMap;
import java.util.Map;

import static org.testng.Assert.*;

/**
 * Created by antoniovl on 19/05/17.
 */
public class QueryParamsTest extends BaseTest {

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
    public void testSetParameters() throws Exception {
        Author author = commandManager.execute(executorContext -> {
            EntityManager entityManager = getEntityManager(executorContext);
            TypedQuery<Author> q = entityManager
                    .createQuery("SELECT a FROM Author a WHERE a.id = :id ", Author.class);
            Map<String, Object> params = new HashMap<>();
            params.put("id", new Long(1));
            return QueryParams.setParameters(q, params)
                    .getSingleResult();
        });
        assertEquals(author.getId(), new Long(1));
    }

}