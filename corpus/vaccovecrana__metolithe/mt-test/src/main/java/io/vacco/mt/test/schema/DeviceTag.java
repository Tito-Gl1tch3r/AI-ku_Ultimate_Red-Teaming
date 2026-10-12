package io.vacco.mt.test.schema;

import io.vacco.metolithe.annotations.*;
import io.vacco.mt.test.annotations.St64;

@MtEntity public class DeviceTag {

  @MtPk public long tid;

  @MtFk(Phone.class)
  @MtPk(idx = 0)
  @MtUnique(idx = 0)
  public int pid;

  @MtFk(Device.class)
  @MtPk(idx = 1)
  @MtUnique(idx = 0)
  public long did;

  @MtCol public long claimTimeUtcMs;

  @St64
  public String smsCodeSignature;

}
