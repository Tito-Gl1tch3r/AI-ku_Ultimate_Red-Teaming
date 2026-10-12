package de.d3adspace.phoenix.repository.yaml;

import de.d3adspace.phoenix.annotations.Id;
import de.d3adspace.phoenix.repository.yaml.exception.PhoenixYamlIOException;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.StringJoiner;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class YamlCrudRepositoryTest {

  private static final String DATA_CONTENT = "lisa:\n"
      + "  name: lisa\n"
      + "  id: lisa\n"
      + "";

  private static final TestModel DATA_MODEL = new TestModel("lisa", "lisa");
  private static final Path DATA_PATH = Paths.get("src/test/resources/data.yaml");

  private YamlCrudRepository<TestModel> repository;

  @BeforeEach
  void setUp() {
    repository = new YamlCrudRepository<>(TestModel.class, DATA_PATH);
  }

  @Test
  void load() throws PhoenixYamlIOException {
    repository.load();

    TestModel lisa = repository.find("lisa").orElseThrow();
    Assertions.assertEquals(DATA_MODEL, lisa);
  }

  @Test
  void save() throws PhoenixYamlIOException {

    repository.save(DATA_MODEL);
    repository.save();

    try {
      String s = Files.readString(DATA_PATH);
      Assertions.assertEquals(DATA_CONTENT, s);
    } catch (IOException e) {
      Assertions.fail(e);
    }
  }

  public static final class TestModel {

    @Id
    private String id;

    private String name;

    public TestModel() {
    }

    public TestModel(String id, String name) {
      this.id = id;
      this.name = name;
    }

    public TestModel(String name) {
      this.name = name;
    }

    public String getName() {
      return name;
    }

    @Override
    public String toString() {
      return new StringJoiner(", ", TestModel.class.getSimpleName() + "[", "]")
          .add("id='" + id + "'")
          .add("name='" + name + "'")
          .toString();
    }

    @Override
    public boolean equals(Object o) {
      if (this == o) {
        return true;
      }
      if (o == null || getClass() != o.getClass()) {
        return false;
      }

      TestModel testModel = (TestModel) o;

      if (id != null ? !id.equals(testModel.id) : testModel.id != null) {
        return false;
      }
      return name != null ? name.equals(testModel.name) : testModel.name == null;
    }

    @Override
    public int hashCode() {
      int result = id != null ? id.hashCode() : 0;
      result = 31 * result + (name != null ? name.hashCode() : 0);
      return result;
    }
  }
}
