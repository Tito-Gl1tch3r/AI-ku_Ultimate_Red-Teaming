package io.vacco.metolithe.changeset;

import java.util.ArrayList;
import java.util.List;

public class MtChangeSet {

  public List<MtChange> changes = new ArrayList<>();

  public MtChangeSet withChanges(List<MtChange> changes) {
    this.changes.clear();
    this.changes.addAll(changes);
    return this;
  }

}
