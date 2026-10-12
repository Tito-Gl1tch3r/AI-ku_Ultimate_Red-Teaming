package io.vacco.mt.test.schema;

import io.vacco.metolithe.annotations.*;
import io.vacco.mt.test.annotations.St128;

import java.util.Objects;

@MtEntity public class Namespace {

  @MtPk public Integer nsId;

  @St128 @MtDao
  public String name;

  @St128 @MtPk(idx = 0) @MtUnique
  public String path;

  @MtCol @MtNotNull @MtDao
  public long createdAtUtcMs;

  public static Namespace of(String name, String path) {
    var ns = new Namespace();
    ns.name = Objects.requireNonNull(name);
    ns.path = Objects.requireNonNull(path);
    ns.createdAtUtcMs = System.currentTimeMillis();
    return ns;
  }

}
