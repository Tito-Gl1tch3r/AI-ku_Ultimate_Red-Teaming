package io.vacco.metolithe.core;

import io.vacco.metolithe.dao.MtPredicate;

import java.io.File;
import java.util.Arrays;
import java.util.List;

import static java.lang.String.format;

public class MtErr {

  public static IllegalStateException badField(String field, MtDescriptor<?> descriptor) {
    return new IllegalStateException(
      format("Missing field [%s] in descriptor [%s]", field, descriptor.getType().getCanonicalName())
    );
  }

  public static IllegalStateException badPageAccess(String[] sortFields, Object[] indexKeys, MtDescriptor<?> descriptor, Exception e) {
    return new IllegalStateException(
      format(
        "Page access error for descriptor [%s], sort fields %s, index keys %s",
        descriptor.getType().getCanonicalName(), Arrays.toString(sortFields), Arrays.toString(indexKeys)
      ), e
    );
  }

  public static IllegalStateException badForeignKey(String src, String srcField, String srcFieldType,
                                                    String dst, String dstField, String dstFieldType) {
    return new IllegalStateException(
      format(
        "Foreign key mismatch between entities: source [%s.%s:%s] to destination [%s.%s:%s]. Check @MtFk annotations and PK types on both classes.",
        src, srcField, srcFieldType, dst, dstField, dstFieldType
      )
    );
  }

  public static IllegalStateException badPkDefinitions(List<MtFieldDescriptor> keys) {
    return new IllegalStateException(
      format("Multiple primary key definitions found: %s", keys)
    );
  }

  public static IllegalStateException badPkComponent(Object src, MtFieldDescriptor componentField) {
    return new IllegalStateException(
      format("Missing primary key for object [%s] in field [%s]", src, componentField.getFieldName())
    );
  }

  public static IllegalStateException badIdGenerator(String targetClass, String pkFieldType, String idGenType) {
    return new IllegalStateException(
      format(
        "ID generator mismatch for class [%s]: pk type [%s], generator type [%s]",
        targetClass, pkFieldType, idGenType
      )
    );
  }

  public static IllegalStateException badSqlTypeMapping(MtFieldDescriptor descriptor) {
    return new IllegalStateException(
      format(
        "Invalid SQL type mapping for field [%s] in [%s]",
        descriptor.getFieldName(), descriptor.getType().getCanonicalName())
    );
  }

  public static IllegalStateException badId(Object field) {
    return new IllegalStateException(format("Missing ID: [%s]", field));
  }

  public static IllegalStateException badFieldAccess(Object target, Object value, Exception e) {
    return new IllegalStateException(
      format(
        "Field access error for target [%s], value [%s]",
        target != null ? target.getClass().getCanonicalName() : "unknown", value
      ), e
    );
  }

  public static IllegalStateException badDaoMapping(File outDir, String outPackage,
                                                    Class<?>[] schemaClasses, Exception e) {
    return new IllegalStateException(
      format(
        "DAO mapping error: outDir [%s], package [%s], classes %s",
        outDir.getAbsolutePath(), outPackage, Arrays.toString(schemaClasses)
      ), e
    );
  }

  public static IllegalStateException badConstructor(MtDescriptor<?> d, Exception e) {
    return new IllegalStateException(
      format("No no-arg constructor found for [%s]", d.getType()), e
    );

  }

  public static IllegalStateException badExtraction(MtDescriptor<?> d, Exception e) {
    return new IllegalStateException(
      format("Extraction failed for [%s]", d), e
    );
  }

  public static IllegalStateException badSql(boolean queryOrUpdate, String sql, Exception e) {
    return new IllegalStateException(
      format("Bad %s: %s", queryOrUpdate ? "query" : "update", sql), e
    );
  }

  public static IllegalArgumentException badOperator(MtPredicate.Operator test, MtPredicate.Operator[] options) {
    return new IllegalArgumentException(
      format("Operator [%s] is not one of %s", test, Arrays.toString(options))
    );
  }

  public static IllegalArgumentException badSeek() {
    return new IllegalArgumentException("Fields and values must have the same length");
  }

  public static IllegalStateException badLogic() {
    return new IllegalStateException("Cannot add logical operators after seek predicates");
  }

  public static IllegalArgumentException badArg(String msg) {
    return new IllegalArgumentException(msg);
  }

  public static IllegalStateException generalError(String msg, Exception e) {
    return new IllegalStateException(msg, e);
  }

  public static IllegalStateException generalError(String msg) {
    return new IllegalStateException(msg);
  }

}