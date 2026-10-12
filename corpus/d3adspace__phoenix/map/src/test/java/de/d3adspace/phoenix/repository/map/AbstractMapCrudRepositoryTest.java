package de.d3adspace.phoenix.repository.map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class AbstractMapCrudRepositoryTest {

  private static final Integer TEST_KEY = 1;
  private static final String TEST_VALUE = "test";

  private Map<Integer, String> TEST_STORAGE;
  private AbstractMapCrudRepository<String, Integer> abstractRepository;

  @BeforeEach
  void setUp() {
    TEST_STORAGE = new HashMap<>() {{
      put(TEST_KEY, TEST_VALUE);
    }};
    abstractRepository = new AbstractMapCrudRepository<>(String.class, TEST_STORAGE) {
      @Override
      public String save(String entity) {
        throw new IllegalStateException();
      }

      @Override
      protected Integer nextId() {
        return -1;
      }
    };
  }

  @Test
  void getStorage() {

    Map<Integer, String> storage = abstractRepository.getStorage();
    assertEquals(TEST_STORAGE, storage, "Storage should still be the same.");
  }

  @Test
  void find() {

    String result = abstractRepository.find(TEST_KEY).orElseThrow();
    assertEquals(TEST_VALUE, result, "Looked up value should match inserted one.");
  }

  @Test
  void findAll() {

    List<String> all = abstractRepository.findAll();
    assertEquals(TEST_STORAGE.size(), all.size(), "Size has to be 1.");
    assertTrue(all.contains(TEST_VALUE), "Our only object should be in all scope.");
  }

  @Test
  void deleteAll() {

    abstractRepository.deleteAll();
    assertEquals(0, abstractRepository.count(), "Size has to be 0.");
    assertFalse(abstractRepository.findAll().contains(TEST_VALUE),
        "Our only object should not be in all scope anymore.");
  }

  @Test
  void delete() {

    abstractRepository.delete(TEST_VALUE);
    assertEquals(0, abstractRepository.count(), "Size has to be 0.");
    assertFalse(abstractRepository.findAll().contains(TEST_VALUE),
        "Our only object should not be in all scope anymore.");
  }

  @Test
  void deleteNoNExistent() {

    abstractRepository.delete(TEST_VALUE + 1);
    assertEquals(1, abstractRepository.count(), "Size has to be 1.");
    assertTrue(abstractRepository.findAll().contains(TEST_VALUE),
        "Our only object should be in all scope.");
  }

  @Test
  void count() {

    long count = abstractRepository.count();
    assertEquals(1, count, "There should be one object.");
  }
}
