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
public class DbUserDao extends MtWriteDao<io.vacco.mt.test.schema.DbUser, java.lang.Integer> {

  public static final String fld_alias = "alias";
  public static final String fld_email = "email";
  public static final String fld_tid = "tid";

  public DbUserDao(String schema, MtCaseFormat fmt, MtJdbc jdbc, MtIdFn<java.lang.Integer> idFn) {
    super(schema, jdbc, new MtDescriptor<>(io.vacco.mt.test.schema.DbUser.class, fmt), idFn);
  }

  public MtFieldDescriptor fld_alias() {
    return this.dsc.getField(fld_alias);
  }

  public List<io.vacco.mt.test.schema.DbUser> loadWhereAliasEq(java.lang.String alias) {
    return loadWhereEq(fld_alias, alias);
  }

  public MtFieldDescriptor fld_email() {
    return this.dsc.getField(fld_email);
  }

  public List<io.vacco.mt.test.schema.DbUser> loadWhereEmailEq(java.lang.String email) {
    return loadWhereEq(fld_email, email);
  }

  public final Map<java.lang.String, List<io.vacco.mt.test.schema.DbUser>> loadWhereEmailIn(java.lang.String ... values) {
    return loadWhereIn(fld_email, values);
  }
  public final Map<java.lang.String, List<io.vacco.mt.test.schema.DbUser>> loadWhereEmailIn(java.util.List<java.lang.String> values) {
    return loadWhereIn(fld_email, values);
  }

  public MtFieldDescriptor fld_tid() {
    return this.dsc.getField(fld_tid);
  }

  public final Map<java.lang.Long, List<io.vacco.mt.test.schema.DbUser>> loadWhereTidIn(java.lang.Long ... values) {
    return loadWhereIn(fld_tid, values);
  }
  public final Map<java.lang.Long, List<io.vacco.mt.test.schema.DbUser>> loadWhereTidIn(java.util.List<java.lang.Long> values) {
    return loadWhereIn(fld_tid, values);
  }

}