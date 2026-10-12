package io.vacco.metolithe.changeset;

import java.util.ArrayList;
import java.util.List;

public class MtUnq {

  public String name;
  public List<String> columns = new ArrayList<>();

  @Override
  public String toString() {
    return String.format("%s %s", name, columns);
  }

}
