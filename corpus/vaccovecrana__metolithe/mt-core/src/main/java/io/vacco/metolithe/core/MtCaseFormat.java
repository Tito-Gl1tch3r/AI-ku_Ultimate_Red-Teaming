package io.vacco.metolithe.core;

import java.util.ArrayList;
import java.util.List;

import static java.lang.String.format;
import static java.util.stream.Collectors.joining;

public enum MtCaseFormat {

  UPPER_CASE, LOWER_CASE, KEEP_CASE;

  public String of(String in) {
    if (in == null) return null;
    switch (this) {
      case LOWER_CASE:
        return in.toLowerCase();
      case UPPER_CASE:
        return in.toUpperCase();
    }
    return in;
  }

  public static final String COMMA_SPC = ", ";

  public static List<String> propNames(MtDescriptor<?> d, boolean withPk) {
    var out = new ArrayList<String>();
    for (var fd : d.getFields(withPk)) {
      out.add(fd.getFieldName());
    }
    return out;
  }

  public static String propNamesCsv(MtDescriptor<?> dsc, boolean withPk, String tableAlias) {
    var ta = tableAlias.isEmpty() ? tableAlias : format("%s.", tableAlias);
    var out = new ArrayList<String>();
    for (var fd : dsc.getFields(withPk)) {
      out.add(format("%s%s", ta, fd.getFieldName()));
    }
    return String.join(COMMA_SPC, out);
  }

  public static String placeholderCsv(MtDescriptor<?> d, boolean withPk) {
    return propNames(d, withPk).stream().map(k -> format(":%s", k)).collect(joining(COMMA_SPC));
  }

  public static String placeHolderAssignmentCsv(MtDescriptor<?> d, boolean withPk) {
    return propNames(d, withPk).stream().map(k -> format("%s = :%s", k, k)).collect(joining(COMMA_SPC));
  }

}
