package io.vacco.mt.test.dao;

import io.vacco.metolithe.core.MtCaseFormat;
import io.vacco.metolithe.core.MtDescriptor;
import io.vacco.metolithe.core.MtFieldDescriptor;
import io.vacco.metolithe.id.MtIdFn;
import io.vacco.metolithe.dao.MtWriteDao;
import io.vacco.metolithe.query.MtJdbc;
import io.vacco.metolithe.query.MtResult;

import java.util.List;
import java.util.Map;

/**************************************************
 * Generated source file. Do not modify directly. *
 **************************************************/
public class NamespaceDao extends MtWriteDao<io.vacco.mt.test.schema.Namespace, java.lang.Integer> {

  public static final String fld_name = "name";
  public static final String fld_createdAtUtcMs = "createdAtUtcMs";

  public NamespaceDao(String schema, MtCaseFormat fmt, MtJdbc jdbc, MtIdFn<java.lang.Integer> idFn) {
    super(schema, jdbc, new MtDescriptor<>(io.vacco.mt.test.schema.Namespace.class, fmt), idFn);
  }

  public MtFieldDescriptor fld_name() {
    return this.dsc.getField(fld_name);
  }

  public MtFieldDescriptor fld_createdAtUtcMs() {
    return this.dsc.getField(fld_createdAtUtcMs);
  }

}