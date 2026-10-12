package io.vacco.mt.test.schema;

import io.vacco.metolithe.annotations.*;
import io.vacco.mt.test.annotations.*;

@MtEntity public class DbUser {

  @MtPk public int uid;

  @St32 public String pw;
  @St64 @MtDao(loadEq = true)
  public String alias;

  @St128
  @MtPk(idx = 0)
  @MtUnique()
  @MtDao(loadEq = true, loadIn = true)
  public String email;

  @MtDao(loadIn = true)
  @MtFk(DeviceTag.class)
  public long tid;

  @St64Opt
  public String tagSignature;

  @St16 @MtFk(DbUserRole.class)
  public String rid;

}
