package io.vacco.mt.test;

import io.vacco.metolithe.changeset.MtLevel;
import io.vacco.metolithe.core.MtCaseFormat;
import io.vacco.metolithe.core.MtLog;
import io.vacco.metolithe.id.MtXxHash;
import io.vacco.mt.test.schema.*;
import io.vacco.shax.logging.ShOption;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.nio.charset.StandardCharsets;

import static org.junit.Assert.assertEquals;

public abstract class MtTest {

  public enum MtDb {
    Sqlite("jdbc:sqlite:./build/db/sqlite/test.db", "main", MtLevel.TABLE_COMPACT),
    H2("jdbc:h2:file:./build/db/h2/test;DB_CLOSE_DELAY=-1", "public", MtLevel.TABLE_MAX);

    public final String url;
    public final String schema;
    public final MtLevel level;

    MtDb(String url, String schema, MtLevel level) {
      this.url = url;
      this.schema = schema;
      this.level = level;
    }
  }

  static {
    new File("./build/db/sqlite").mkdirs();
    ShOption.setSysProp(ShOption.IO_VACCO_SHAX_DEVMODE, "true");
    ShOption.setSysProp(ShOption.IO_VACCO_SHAX_PRETTYPRINT, "true");
  }

  protected static final Logger log = LoggerFactory.getLogger(MtTest.class);
  protected static final MtCaseFormat fmt = MtCaseFormat.KEEP_CASE;

  static {
    MtLog.setInfoLogger(log::info);
    MtLog.setDebugLogger(log::debug);
    MtLog.setWarnLogger(log::warn);
  }

  public static Class<?>[] testSchema = new Class<?>[]{
    Device.class, DeviceLocation.class, DeviceTag.class,
    Phone.class, DbUser.class, DbUserRole.class, UserFollow.class,
    ApiKey.class, Namespace.class, KeyNamespace.class
  };

  public static DbUser u0 = new DbUser();
  public static DbUser u1 = new DbUser();

  public static Phone p0 = new Phone();
  public static Phone p1 = new Phone();

  public static Device d0 = new Device();
  public static Device d1 = new Device();

  static {
    u0.alias = "Jane";
    u0.email = "jane@me.com";
    u0.pw = "0xAAABBBCCCDDDEEFFF";
    u0.uid = 112233;

    u1.alias = "Joe";
    u1.email = "joe@me.com";
    u1.pw = "0xEEEFFFDDDAAABBB";
    u1.uid = 224466;

    p0.countryCode = 1;
    p0.number = "5555555555";
    p0.smsVerificationCode = 1234;

    p1.countryCode = 1;
    p1.number = "4441116666";
    p1.smsVerificationCode = 4567;

    d0.type = Device.DType.ANDROID;
    d0.signingKey = "c29tZSBwdWJsaWMga2V5IGRhdGEgZm9yIGRldmljZSAw";

    d1.type = Device.DType.ANDROID;
    d1.signingKey = "c29tZSBwdWJsaWMga2V5IGRhdGEgZm9yIGRldmljZSAx";

    var d0b = d0.signingKey.getBytes(StandardCharsets.UTF_8);
    var h32 = MtXxHash.hash32(d0b, 0, d0b.length, 1234);
    var h64 = MtXxHash.hash64(d0b, 0, d0b.length, 1234);

    log.info("{}", h32);
    log.info("{}", h64);
    assertEquals(-2013497302, h32);
    assertEquals(-3973416690927799706L, h64);
  }

}
