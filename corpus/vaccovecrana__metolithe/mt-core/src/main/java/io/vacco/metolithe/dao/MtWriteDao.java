package io.vacco.metolithe.dao;

import io.vacco.metolithe.core.MtDescriptor;
import io.vacco.metolithe.core.MtFieldDescriptor;
import io.vacco.metolithe.id.MtIdFn;
import io.vacco.metolithe.query.MtJdbc;
import io.vacco.metolithe.query.MtResult;

import java.util.Optional;
import java.util.function.BiFunction;

import static io.vacco.metolithe.core.MtCaseFormat.*;
import static io.vacco.metolithe.core.MtErr.generalError;
import static io.vacco.metolithe.query.MtResult.result;
import static java.lang.String.format;

public class MtWriteDao<T, K> extends MtReadDao<T, K> {

  public MtWriteDao(String schemaName, MtJdbc jdbc, MtDescriptor<T> d, MtIdFn<K> idFn) {
    super(schemaName, jdbc, d, idFn);
  }

  @SuppressWarnings("unchecked")
  public <V> V withId(T rec, BiFunction<MtFieldDescriptor, K, V> bfn) {
    var opk = dsc.getPkField();
    var pkVals = dsc.getPkValues(rec);
    if (opk.isPresent()) {
      K id = pkVals.length == 0 ? (K) opk.get().getValue(rec) : idFn.apply(pkVals);
      opk.get().setValue(rec, id);
      return bfn.apply(opk.get(), id);
    } else {
      return bfn.apply(null, null);
    }
  }

  public Optional<K> idOf(T test) {
    return withId(test, (fd, id) -> id == null
      ? Optional.empty()
      : Optional.of(id)
    );
  }

  public MtResult<T> save(T rec) {
    return withId(rec, (fd, pk) -> {
      var query = getQueryCache().computeIfAbsent("insert", k ->
        format("insert into %s (%s) values (%s)",
          getTableName(),
          propNamesCsv(dsc, true, ""),
          placeholderCsv(dsc, true)
        )
      );
      var upd = sql().update(query);
      dsc.forEach(true, rec, upd::param);
      return result(rec, sql().inTx() ? upd : upd.execute());
    });
  }

  public MtResult<T> update(T rec) {
    return withId(rec, (fd, pk) -> {
      var queryAssignments = placeHolderAssignmentCsv(dsc, false);
      var query = getQueryCache().computeIfAbsent("update",
        k -> format("update %s set %s where %s = :%s", getTableName(), queryAssignments,
          fd.getFieldName(), fd.getFieldName())
      );
      var upd = sql().update(query);
      dsc.forEach(false, rec, upd::param);
      upd.param(fd.getFieldName(), pk);
      return result(rec, sql().inTx() ? upd : upd.execute());
    });
  }

  public MtResult<T> upsert(T rec) {
    return withId(rec, (fd, pk) -> load(pk).isEmpty()
      ? save(rec)
      : update(rec));
  }

  public MtResult<T> delete(T rec) {
    return withId(rec, (fd, pk) -> {
      var query = getQueryCache().computeIfAbsent("delete",
        k -> format("delete from %s where %s = :%s", getTableName(), fd.getFieldName(), fd.getFieldName())
      );
      var del = sql().update(query).param(fd.getFieldName(), pk);
      return result(rec, sql().inTx() ? del : del.execute());
    });
  }

  public MtResult<T> deleteWhereEq(String field, Object value) {
    var fn = dsc.getFormat().of(field);
    var query = getQueryCache().computeIfAbsent("deleteWhereEq" + fn,
      k -> format("delete from %s where %s = :%s", getTableName(), fn, fn)
    );
    var del = sql().update(query).param(fn, value);
    return result(null, sql().inTx() ? del : del.execute());
  }

  public MtResult<T> deleteWhereIdEq(K id) {
    return dsc.getPkField()
      .map(mtFieldDescriptor -> deleteWhereEq(mtFieldDescriptor.getFieldName(), id))
      .orElseThrow(() -> generalError(format("Type [%s] has no primary key", dsc)));
  }

}
