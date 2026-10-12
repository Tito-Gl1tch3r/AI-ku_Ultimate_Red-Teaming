package io.vacco.metolithe.changeset;

import java.util.ArrayList;
import java.util.List;

public class MtTable {

  public String name;
  public List<MtCol> columns = new ArrayList<>();
  public List<MtFkey> fKeys = new ArrayList<>();
  public List<MtUnq> unique = new ArrayList<>();
  public List<MtIdx> indices = new ArrayList<>();

  @Override
  public String toString() {
    return String.format(
      "%s [cols: %d, fk: %d, unq: %d, idx: %d]",
      name, columns.size(), fKeys.size(),
      unique.size(), indices.size()
    );
  }

}
