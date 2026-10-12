package io.vacco.metolithe.core;

import java.util.Objects;
import java.util.function.BiConsumer;

public class MtLog {

  public static BiConsumer<String, Object[]> infoFn, debugFn, warnFn;

  public static void setInfoLogger(BiConsumer<String, Object[]> logFn) {
    MtLog.infoFn = Objects.requireNonNull(logFn);
  }

  public static void setWarnLogger(BiConsumer<String, Object[]> logFn) {
    MtLog.warnFn = Objects.requireNonNull(logFn);
  }

  public static void setDebugLogger(BiConsumer<String, Object[]> logFn) {
    MtLog.debugFn = Objects.requireNonNull(logFn);
  }

  public static void info(String fmt, Object... args) {
    if (infoFn != null) {
      infoFn.accept(fmt, args);
    }
  }

  public static void warn(String fmt, Object... args) {
    if (warnFn != null) {
      warnFn.accept(fmt, args);
    }
  }

  public static void debug(String fmt, Object... args) {
    if (debugFn != null) {
      debugFn.accept(fmt, args);
    }
  }

}
