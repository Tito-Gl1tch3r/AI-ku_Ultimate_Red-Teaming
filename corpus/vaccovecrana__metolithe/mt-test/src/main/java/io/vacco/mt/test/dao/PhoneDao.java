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
public class PhoneDao extends MtWriteDao<io.vacco.mt.test.schema.Phone, java.lang.Integer> {

  public static final String fld_countryCode = "countryCode";
  public static final String fld_number = "number";
  public static final String fld_smsVerificationCode = "smsVerificationCode";

  public PhoneDao(String schema, MtCaseFormat fmt, MtJdbc jdbc, MtIdFn<java.lang.Integer> idFn) {
    super(schema, jdbc, new MtDescriptor<>(io.vacco.mt.test.schema.Phone.class, fmt), idFn);
  }

  public MtFieldDescriptor fld_countryCode() {
    return this.dsc.getField(fld_countryCode);
  }

  public List<io.vacco.mt.test.schema.Phone> loadWhereCountryCodeEq(java.lang.Integer countryCode) {
    return loadWhereEq(fld_countryCode, countryCode);
  }

  public final List<io.vacco.mt.test.schema.Phone> listWhereCountryCodeIn(java.lang.Integer ... values) {
    return listWhereIn(fld_countryCode, values);
  }
  public final List<io.vacco.mt.test.schema.Phone> listWhereCountryCodeIn(java.util.List<java.lang.Integer> values) {
    return listWhereIn(fld_countryCode, values);
  }

  public MtFieldDescriptor fld_number() {
    return this.dsc.getField(fld_number);
  }

  public MtFieldDescriptor fld_smsVerificationCode() {
    return this.dsc.getField(fld_smsVerificationCode);
  }

}