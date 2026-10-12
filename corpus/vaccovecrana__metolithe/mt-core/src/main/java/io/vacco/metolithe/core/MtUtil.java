package io.vacco.metolithe.core;

import io.vacco.metolithe.annotations.MtVarchar;

import java.util.Objects;
import java.util.Optional;
import java.util.function.Function;

import static io.vacco.metolithe.core.MtErr.badSqlTypeMapping;
import static java.lang.String.format;
import static java.util.Arrays.copyOf;
import static java.util.Arrays.stream;

public class MtUtil {

  public static final int ENUM_VARCHAR_LENGTH = 64;

  public static Class<?> toWrapperClass(Class<?> type) {
    if (!type.isPrimitive()) return type;
    else if (int.class.equals(type)) {
      return Integer.class;
    } else if (double.class.equals(type)) {
      return Double.class;
    } else if (char.class.equals(type)) {
      return Character.class;
    } else if (boolean.class.equals(type)) {
      return Boolean.class;
    } else if (long.class.equals(type)) {
      return Long.class;
    } else if (float.class.equals(type)) {
      return Float.class;
    } else if (short.class.equals(type)) {
      return Short.class;
    } else if (byte.class.equals(type)) {
      return Byte.class;
    }
    return type;
  }

  public static String sqlTypeOf(MtFieldDescriptor fd) {
    Class<?> wt0 = MtUtil.toWrapperClass(fd.getType());
    if (wt0 == Boolean.class) {
      return "boolean";
    }
    if (wt0 == String.class) {
      var maxSize = fd.get(MtVarchar.class);
      return format("varchar(%s)", maxSize.get().value());
    }
    if (wt0 == Integer.class) {
      return "integer";
    }
    if (wt0 == Long.class) {
      return "bigint";
    }
    if (wt0 == Double.class) {
      return "double";
    }
    if (wt0 == Float.class) {
      return "float";
    }
    if (wt0 == java.math.BigDecimal.class) {
      return "decimal";
    }
    if (Enum.class.isAssignableFrom(fd.getType())) {
      return format("varchar(%s)", ENUM_VARCHAR_LENGTH);
    }
    throw badSqlTypeMapping(fd);
  }

  public static byte[] concat(byte[] first, byte[] second) {
    byte[] result = copyOf(first, first.length + second.length);
    System.arraycopy(second, 0, result, first.length, second.length);
    return result;
  }

  public static Optional<byte[]> fnConcat(Function<Object, String> idFn, Object... values) {
    return stream(values)
      .filter(Objects::nonNull)
      .map(idFn)
      .map(String::getBytes)
      .reduce(MtUtil::concat);
  }

  public static Optional<byte[]> toStringConcat(Object... values) {
    return fnConcat(Object::toString, values);
  }

}
