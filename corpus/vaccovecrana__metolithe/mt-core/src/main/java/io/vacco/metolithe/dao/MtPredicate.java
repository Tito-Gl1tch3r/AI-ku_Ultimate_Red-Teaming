package io.vacco.metolithe.dao;

import io.vacco.metolithe.core.MtFieldDescriptor;

import java.util.Map;

import static io.vacco.metolithe.core.MtErr.badOperator;
import static java.lang.String.format;
import static java.util.Objects.requireNonNull;

public class MtPredicate {

  public enum Operator {
    IS_NULL(" IS NULL"), IS_NOT_NULL(" IS NOT NULL"),
    EQ_FIELD("%s = %s"),
    EQ(" = :%s"), NEQ(" != :%s"),
    LT(" < :%s"), LTE(" <= :%s"),
    GT(" > :%s"), GTE(" >= :%s"),
    LIKE(" LIKE :%s");

    public final String sqlTemplate;

    Operator(String sqlTemplate) {
      this.sqlTemplate = sqlTemplate;
    }
  }

  private final Operator operator;
  private final Object value;

  public final MtFieldDescriptor field0, field1;
  public final String paramName;
  public final boolean isSeek;

  private static void oneOf(Operator test, Operator... options) {
    var ok = false;
    for (var op : options) {
      if (test == op) {
        ok = true;
        break;
      }
    }
    if (!ok) {
      throw badOperator(test, options);
    }
  }

  /**
   * Constructor for single parameter operators
   */
  private MtPredicate(MtFieldDescriptor field0, Operator operator, Object value, String paramName, boolean isSeek) {
    this.field0 = requireNonNull(field0);
    this.field1 = null;
    this.operator = operator;
    this.value = value;
    this.paramName = paramName;
    this.isSeek = isSeek;
  }

  /**
   * Constructor for null/not null operators
   */
  private MtPredicate(MtFieldDescriptor field0, Operator operator) {
    this.field0 = requireNonNull(field0);
    this.field1 = null;
    this.operator = requireNonNull(operator);
    this.value = null;
    this.paramName = null;
    this.isSeek = false;
  }

  /**
   * Constructor for join field operator
   */
  private MtPredicate(MtFieldDescriptor field0, MtFieldDescriptor field1) {
    this.field0 = requireNonNull(field0);
    this.field1 = requireNonNull(field1);
    this.operator = Operator.EQ_FIELD;
    this.value = null;
    this.paramName = null;
    this.isSeek = false;
  }

  public static MtPredicate filter(MtFieldDescriptor field, Operator operator, Object value, String paramName) {
    oneOf(
      requireNonNull(operator),
      Operator.EQ, Operator.NEQ,
      Operator.LT, Operator.LTE,
      Operator.GT, Operator.GTE, Operator.LIKE
    );
    return new MtPredicate(field, operator, value, paramName, false);
  }

  public static MtPredicate filter(MtFieldDescriptor field, Operator operator) {
    oneOf(requireNonNull(operator), Operator.IS_NULL, Operator.IS_NOT_NULL);
    return new MtPredicate(field, operator);
  }

  public static MtPredicate seek(MtFieldDescriptor field, Operator operator, Object value, String paramName) {
    oneOf(requireNonNull(operator), Operator.GT, Operator.GTE, Operator.LT, Operator.LTE);
    return new MtPredicate(field, operator, value, paramName, true);
  }

  public static MtPredicate join(MtFieldDescriptor leftField, MtFieldDescriptor rightField) {
    return new MtPredicate(leftField, rightField);
  }

  public String render() {
    switch (this.operator) {
      case IS_NULL:
      case IS_NOT_NULL:
        return field0.getFieldNameAliased() + operator.sqlTemplate;
      case EQ_FIELD:
        return format(
          operator.sqlTemplate,
          field0.getFieldNameAliased(),
          requireNonNull(field1).getFieldNameAliased()
        );
      default:
        return field0.getFieldNameAliased() + format(operator.sqlTemplate, paramName);
    }
  }

  public void applyParams(Map<String, Object> params) {
    if (paramName != null && value != null) {
      params.put(paramName, value);
    }
  }

  @Override
  public String toString() {
    return String.format("(%s): %s", isSeek ? "skp" : "flp", this.render());
  }

  @Override
  public boolean equals(Object obj) {
    return obj instanceof MtPredicate
      && ((MtPredicate) obj).render().equals(this.render());
  }

  @Override
  public int hashCode() {
    return this.render().hashCode();
  }

}
