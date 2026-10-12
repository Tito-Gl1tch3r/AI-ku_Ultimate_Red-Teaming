package io.vacco.metolithe.dao;

import io.vacco.metolithe.core.MtDescriptor;
import io.vacco.metolithe.core.MtFieldDescriptor;

import java.util.*;
import java.util.stream.Collectors;

import static io.vacco.metolithe.core.MtCaseFormat.propNamesCsv;
import static io.vacco.metolithe.core.MtErr.badLogic;
import static io.vacco.metolithe.core.MtErr.badSeek;
import static java.lang.String.format;
import static java.util.Objects.requireNonNull;

public class MtQuery {

  public enum LogicalOperator {AND, OR}

  private final Set<MtPredicate> predicates = new LinkedHashSet<>();
  private final List<LogicalOperator> operators = new ArrayList<>();
  private final Map<String, Object> params = new LinkedHashMap<>();
  private final List<MtFieldDescriptor> orderByFields = new ArrayList<>();
  private final List<MtJoin> joins = new ArrayList<>();
  private final String schema;

  public MtDescriptor<?> from, target;
  public Integer limit;
  public boolean orderByReverse;

  private MtQuery(String schema, MtDescriptor<?> target) {
    this.schema = Objects.requireNonNull(schema);
    this.target = Objects.requireNonNull(target);
  }

  public static MtQuery create(String schema, MtDescriptor<?> target) {
    return new MtQuery(schema, target);
  }

  private MtQuery addPredicate(MtPredicate predicate) {
    predicates.add(predicate);
    predicate.applyParams(params);
    return this;
  }

  private String nextParamName() {
    return "p" + params.size();
  }

  public MtQuery from(MtDescriptor<?> from) {
    this.from = requireNonNull(from);
    return this;
  }

  public MtQuery eq(MtFieldDescriptor field, Object value) {
    return addPredicate(MtPredicate.filter(field, MtPredicate.Operator.EQ, value, nextParamName()));
  }

  public MtQuery neq(MtFieldDescriptor field, Object value) {
    return addPredicate(MtPredicate.filter(field, MtPredicate.Operator.NEQ, value, nextParamName()));
  }

  public MtQuery isNull(MtFieldDescriptor field) {
    return addPredicate(MtPredicate.filter(field, MtPredicate.Operator.IS_NULL));
  }

  public MtQuery isNotNull(MtFieldDescriptor field) {
    return addPredicate(MtPredicate.filter(field, MtPredicate.Operator.IS_NOT_NULL));
  }

  public MtQuery lt(MtFieldDescriptor field, Object value) {
    return addPredicate(MtPredicate.filter(field, MtPredicate.Operator.LT, value, nextParamName()));
  }

  public MtQuery lte(MtFieldDescriptor field, Object value) {
    return addPredicate(MtPredicate.filter(field, MtPredicate.Operator.LTE, value, nextParamName()));
  }

  public MtQuery gt(MtFieldDescriptor field, Object value) {
    return addPredicate(MtPredicate.filter(field, MtPredicate.Operator.GT, value, nextParamName()));
  }

  public MtQuery gte(MtFieldDescriptor field, Object value) {
    return addPredicate(MtPredicate.filter(field, MtPredicate.Operator.GTE, value, nextParamName()));
  }

  public MtQuery like(MtFieldDescriptor field, String value) {
    return addPredicate(MtPredicate.filter(field, MtPredicate.Operator.LIKE, value, nextParamName()));
  }

  public MtQuery innerJoin(MtDescriptor<?> source, MtDescriptor<?> target) {
    joins.add(MtJoin.inner(this.schema, source, target));
    return this;
  }

  public MtQuery leftJoin(MtDescriptor<?> source, MtDescriptor<?> target) {
    joins.add(MtJoin.left(this.schema, source, target));
    return this;
  }

  public MtQuery seek(MtFieldDescriptor[] fields, Object[] values) {
    if (fields.length != values.length) {
      throw badSeek();
    }
    orderByFields.clear();
    orderByFields.addAll(Arrays.asList(fields));
    for (int i = 0; i < fields.length; i++) {
      if (values[i] != null) {
        var op = orderByReverse ? MtPredicate.Operator.LTE : MtPredicate.Operator.GTE;
        addPredicate(MtPredicate.seek(fields[i], op, values[i], "sk" + i));
      }
    }
    return this;
  }

  public MtQuery and() {
    if (!predicates.isEmpty() && predicates.iterator().next().isSeek) {
      throw badLogic();
    }
    operators.add(LogicalOperator.AND);
    return this;
  }

  public MtQuery or() {
    if (!predicates.isEmpty() && predicates.iterator().next().isSeek) {
      throw badLogic();
    }
    operators.add(LogicalOperator.OR);
    return this;
  }

  public MtQuery limit(Integer limit) {
    this.limit = Objects.requireNonNull(limit);
    return this;
  }

  public MtQuery reverse() {
    this.orderByReverse = !this.orderByReverse;
    return this;
  }

  public String renderFilter() {
    var filterPreds = predicates.stream()
      .filter(p -> !p.isSeek)
      .collect(Collectors.toList());
    if (filterPreds.isEmpty()) {
      return "";
    }
    var sb = new StringBuilder();
    for (int i = 0; i < filterPreds.size(); i++) {
      sb.append(filterPreds.get(i).render());
      if (i < Math.min(operators.size(), filterPreds.size() - 1)) {
        sb.append(" ").append(operators.get(i).name()).append(" ");
      }
    }
    return sb.toString();
  }

  public String renderSeek() {
    var seekPreds = predicates.stream()
      .filter(p -> p.isSeek)
      .collect(Collectors.toList());
    if (seekPreds.isEmpty()) {
      return "";
    }
    var fieldsCsv = seekPreds.stream()
      .map(p -> p.field0.getFieldNameAliased())
      .collect(Collectors.joining(", "));
    var paramsCsv = seekPreds.stream()
      .map(p -> ":" + p.paramName) // Only use parameter placeholder, e.g., :sk0
      .collect(Collectors.joining(", "));
    var op = orderByReverse ? "<=" : ">=";
    return String.format("and (%s) %s (%s)", fieldsCsv, op, paramsCsv);
  }

  public String renderOrderBy() {
    if (orderByFields.isEmpty()) {
      return "";
    }
    var fieldsCsv = orderByFields.stream()
      .map(fd -> String.format("%s %s", fd.getFieldNameAliased(), orderByReverse ? "desc" : "asc"))
      .collect(Collectors.joining(", "));
    return format("order by %s", fieldsCsv);
  }

  public String renderLimit() {
    if (limit == null) {
      return "";
    }
    return format("limit %d", limit + 1);
  }

  public String renderJoins() {
    return joins.stream()
      .map(MtJoin::render)
      .collect(Collectors.joining("\n"));
  }

  public String render() {
    var qFmt = String.join("\n",
      "select %s from %s %s", // props, table, alias
      "%s",                   // join clause(s)
      "where 1 = 1",
      "%s",                   // filter predicate
      "%s",                   // seek predicate
      "%s",                   // order by
      "%s"                    // limit
    );
    var joins = renderJoins();
    var filterP = renderFilter().isEmpty() ? "" : format("and (%s)", renderFilter());
    var seekP = renderSeek();
    var orderBy = renderOrderBy();
    var limit = renderLimit();
    var alias = (from != null ? from : target).getAlias();
    var table = (from != null ? from : target).getTableName(schema);
    return format(qFmt,
      propNamesCsv(target, true, target.getAlias()),
      table, alias,
      joins, filterP, seekP,
      orderBy, limit
    );
  }

  public Map<String, Object> getParams() {
    return params;
  }

}
