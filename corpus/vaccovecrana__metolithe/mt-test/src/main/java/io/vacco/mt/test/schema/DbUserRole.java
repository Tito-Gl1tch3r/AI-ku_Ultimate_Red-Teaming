package io.vacco.mt.test.schema;

import io.vacco.metolithe.annotations.*;
import io.vacco.mt.test.annotations.St16;

@MtEntity
public class DbUserRole {

  @MtPk @St16
  public String rid;

  @MtCol
  public long createdUtcMs;

}
