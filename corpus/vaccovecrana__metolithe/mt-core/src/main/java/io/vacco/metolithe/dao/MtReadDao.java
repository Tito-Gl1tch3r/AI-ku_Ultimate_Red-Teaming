package io.vacco.metolithe.dao;

import io.vacco.metolithe.core.MtDescriptor;
import io.vacco.metolithe.core.MtFieldDescriptor;
import io.vacco.metolithe.id.MtIdFn;
import io.vacco.metolithe.query.MtJdbc;
import io.vacco.metolithe.util.MtPage1;
import io.vacco.metolithe.util.MtPage2;

import java.util.*;

import static io.vacco.metolithe.core.MtCaseFormat.propNamesCsv;
import static io.vacco.metolithe.core.MtErr.badId;
import static io.vacco.metolithe.core.MtErr.badPageAccess;
import static java.lang.String.format;
import static java.util.stream.Collectors.groupingBy;
import static java.util.stream.Collectors.joining;

public class MtReadDao<T, K> extends MtDao<T, K> {

  public MtReadDao(String schemaName, MtJdbc jdbc, MtDescriptor<T> d, MtIdFn<K> idFn) {
    super(schemaName, jdbc, d, idFn);
  }

  protected String getSelectWhereEqQuery(String field) {
    var fn = dsc.getFormat().of(field);
    var qk = "selectWhereEq" + fn;
    return getQueryCache().computeIfAbsent(qk, k -> {
      var alias = dsc.getAlias();
      var pNames = propNamesCsv(dsc, true, alias);
      return format(
        "select %s from %s %s where %s.%s = :%s",
        pNames, getTableName(), alias, alias, fn, fn
      );
    });
  }

  public Optional<T> load(K id) {
    var pkf = dsc.getPkField();
    if (pkf.isPresent()) {
      var q = getSelectWhereEqQuery(pkf.get().getFieldName());
      var fn = pkf.get().getFieldName();
      return sql()
        .select(q)
        .param(fn, id)
        .one(mapToDefault());
    }
    return Optional.empty();
  }

  public List<T> loadWhereEq(String field, Object value) {
    return sql()
      .select(getSelectWhereEqQuery(field))
      .param(dsc.getFormat().of(field), value)
      .list(mapToDefault());
  }

  private List<String> paramLabels(int valueCount, String label) {
    var out = new ArrayList<String>();
    for (int i = 0; i < valueCount; i++) {
      out.add(format("%s%s", label, i));
    }
    return out;
  }

  public String toNamedParams(List<String> labels) {
    return labels.stream()
      .map(param -> format(":%s", param))
      .collect(joining(", "));
  }

  @SafeVarargs
  @SuppressWarnings("varargs")
  public final <V> List<T> listWhereIn(String field, V... values) {
    if (values == null || values.length == 0) {
      return Collections.emptyList();
    }
    var fd = dsc.getField(field);
    var alias = dsc.getAlias();
    var labels = paramLabels(values.length, fd.getFieldName());
    var query = String.format(
      "select %s from %s %s where %s in (%s)",
      propNamesCsv(dsc, true, alias), getTableName(),
      alias, fd.getFieldName(), toNamedParams(labels)
    );
    var select = sql().select(query);
    for (int i = 0; i < values.length; i++) {
      select.param(labels.get(i), values[i]);
    }
    return select.list(mapToDefault());
  }

  public final <V> List<T> listWhereIn(String field, List<V> values) {
    if (values == null || values.isEmpty()) {
      return Collections.emptyList();
    }
    @SuppressWarnings("unchecked")
    V[] arr = (V[]) values.toArray();
    return listWhereIn(field, arr);
  }

  @SafeVarargs
  @SuppressWarnings("varargs")
  public final <V> Map<V, List<T>> loadWhereIn(String field, V... values) {
    var fd = dsc.getField(field);
    return listWhereIn(field, values).stream().collect(groupingBy(fd::getValue));
  }

  public final <V> Map<V, List<T>> loadWhereIn(String field, List<V> values) {
    if (values == null || values.isEmpty()) {
      return Collections.emptyMap();
    }
    @SuppressWarnings("unchecked")
    V[] arr = (V[]) values.toArray();
    return loadWhereIn(field, arr);
  }

  public T loadExisting(K id) {
    var record = load(id);
    if (record.isEmpty()) {
      throw badId(id);
    }
    return record.get();
  }

  public List<T> loadPageItems(MtQuery query) {
    try {
      var sql = query.render();
      var q = sql().select(sql);
      for (var e : query.getParams().entrySet()) {
        q = q.param(e.getKey(), e.getValue());
      }
      return q.list(mapToDefault());
    } catch (Exception e) {
      throw badPageAccess(null, null, dsc, e);
    }
  }

  public MtQuery query() {
    return MtQuery.create(this.schema, this.dsc);
  }

  private MtQuery setQuery(MtQuery filter, String[] nxFields, Object[] nxValues) {
    var fields = new MtFieldDescriptor[nxFields.length];
    for (int i = 0; i < nxFields.length; i++) {
      fields[i] = dsc.getField(nxFields[i]);
    }
    if (filter == null) {
      filter = query();
    }
    return filter.seek(fields, nxValues);
  }

  public <K1> MtPage1<T, K1> loadPage1(MtQuery filter, String nx1Fld, K1 nx1) {
    var query = setQuery(filter, new String[]{nx1Fld}, new Object[]{nx1});
    var page = new MtPage1<T, K1>();
    var items = loadPageItems(query);
    page.items = items;
    if (query.limit != null && items.size() > query.limit) {
      var next = items.remove(items.size() - 1);
      page.nx1 = dsc.getField(nx1Fld).getValue(next);
    }
    page.size = items.size();
    return page;
  }

  public <K1, K2> MtPage2<T, K1, K2> loadPage2(MtQuery filter,
                                               String nx1Fld, K1 nx1,
                                               String nx2Fld, K2 nx2) {
    var query = setQuery(filter, new String[]{nx1Fld, nx2Fld}, new Object[]{nx1, nx2});
    var page = new MtPage2<T, K1, K2>();
    var items = loadPageItems(query);
    page.items = items;
    if (query.limit != null && items.size() > query.limit) {
      var next = items.remove(items.size() - 1);
      page.nx1 = dsc.getField(nx1Fld).getValue(next);
      page.nx2 = dsc.getField(nx2Fld).getValue(next);
    }
    page.size = items.size();
    return page;
  }

}
