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
public class DeviceDao extends MtWriteDao<io.vacco.mt.test.schema.Device, java.lang.Long> {

  public static final String fld_disabled = "disabled";

  public DeviceDao(String schema, MtCaseFormat fmt, MtJdbc jdbc, MtIdFn<java.lang.Long> idFn) {
    super(schema, jdbc, new MtDescriptor<>(io.vacco.mt.test.schema.Device.class, fmt), idFn);
  }

  public MtFieldDescriptor fld_disabled() {
    return this.dsc.getField(fld_disabled);
  }

  public List<io.vacco.mt.test.schema.Device> loadWhereDisabledEq(java.lang.Boolean disabled) {
    return loadWhereEq(fld_disabled, disabled);
  }

}