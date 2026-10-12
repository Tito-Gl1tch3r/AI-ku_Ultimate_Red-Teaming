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
public class KeyNamespaceDao extends MtWriteDao<io.vacco.mt.test.schema.KeyNamespace, java.lang.Integer> {

  public static final String fld_kid = "kid";

  public KeyNamespaceDao(String schema, MtCaseFormat fmt, MtJdbc jdbc, MtIdFn<java.lang.Integer> idFn) {
    super(schema, jdbc, new MtDescriptor<>(io.vacco.mt.test.schema.KeyNamespace.class, fmt), idFn);
  }

  public MtFieldDescriptor fld_kid() {
    return this.dsc.getField(fld_kid);
  }

}