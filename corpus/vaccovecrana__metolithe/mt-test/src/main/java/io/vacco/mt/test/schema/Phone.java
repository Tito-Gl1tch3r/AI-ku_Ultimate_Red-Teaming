package io.vacco.mt.test.schema;

import io.vacco.metolithe.annotations.*;
import io.vacco.mt.test.annotations.St16;

@MtEntity public class Phone {

  @MtPk public int pid;

  @MtCol @MtNotNull @MtIndex
  @MtDao(loadEq = true, listIn = true)
  @MtPk(idx = 0)
  @MtUnique(idx = 0)
  public int countryCode;

  @St16
  @MtDao
  @MtPk(idx = 1)
  @MtUnique(idx = 0)
  public String number;

  @MtCol @MtDao
  public int smsVerificationCode;

}
