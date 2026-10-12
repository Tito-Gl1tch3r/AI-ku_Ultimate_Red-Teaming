package io.vacco.mt.test;

import io.vacco.metolithe.changeset.MtTable;
import io.vacco.metolithe.query.MtJdbc;
import j8spec.annotation.DefinedOrder;
import j8spec.junit.J8SpecRunner;
import org.h2.jdbcx.JdbcDataSource;
import org.junit.runner.RunWith;

import java.util.ArrayList;

import static io.vacco.mt.test.MtDaoTest.*;
import static j8spec.J8Spec.it;

@DefinedOrder
@RunWith(J8SpecRunner.class)
public class MtDaoH2Test {
  static {
    var db = MtTest.MtDb.H2;
    var ds = new JdbcDataSource();
    ds.setURL(db.url);
    var jdbc = new MtJdbc(ds);
    var tables = new ArrayList<MtTable>();

    it("Generates changelogs", () -> tables.addAll(changeLogMake()));
    it("Applies change logs.", () -> changeLogApply(tables, db, ds));
    it("Uses base DAOs for data access", () -> daoDataAccess(db, jdbc));
    it("Uses generated POJO DAOs for data access", () -> daoPojoAccess(db, jdbc));
    it("Uses filter predicates for basic search", () -> daoPredicates(db, jdbc));
    it("Can paginate over record collections", () -> daoPagination(db, jdbc));
    it("Renders DAO queries", () -> daoQueries(db, jdbc));
    it("Renders DAO JOIN queries", () -> daoJoins(db, jdbc));
  }
}
