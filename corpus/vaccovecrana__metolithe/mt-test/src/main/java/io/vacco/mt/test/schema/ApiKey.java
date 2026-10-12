package io.vacco.mt.test.schema;

import io.vacco.metolithe.annotations.*;
import io.vacco.mt.test.annotations.St64;

import java.util.Objects;

@MtEntity public class ApiKey {

  @MtPk public Integer kid;

  @MtFk(ApiKey.class)
  public Integer pKid;

  @MtFk(DbUser.class)
  public int uid;

  @St64 @MtPk(idx = 0)
  public String name;

  @St64 public String hash; // SHA256 hash of the key

  public static ApiKey of(int uid, Integer pKid, String name, String hash) {
    var k = new ApiKey();
    k.uid = uid;
    k.pKid = pKid;
    k.name = Objects.requireNonNull(name);
    k.hash = Objects.requireNonNull(hash);
    return k;
  }

}
