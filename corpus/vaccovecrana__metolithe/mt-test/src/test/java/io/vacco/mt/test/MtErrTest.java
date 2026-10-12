package io.vacco.mt.test;

import io.vacco.metolithe.changeset.MtApply;
import io.vacco.metolithe.core.MtCaseFormat;
import io.vacco.metolithe.core.MtErr;
import io.vacco.metolithe.core.MtFieldDescriptor;
import io.vacco.metolithe.id.MtMurmur3IFn;
import io.vacco.mt.test.dao.DbUserDao;
import io.vacco.mt.test.schema.DbUser;
import j8spec.annotation.DefinedOrder;
import j8spec.junit.J8SpecRunner;
import org.junit.runner.RunWith;

import java.io.File;
import java.io.IOException;
import java.util.Arrays;
import java.util.List;

import static j8spec.J8Spec.describe;
import static j8spec.J8Spec.it;
import static org.junit.Assert.assertEquals;

@DefinedOrder
@RunWith(J8SpecRunner.class)
public class MtErrTest {

  private static final DbUserDao userDao = new DbUserDao("public", MtCaseFormat.LOWER_CASE, null, new MtMurmur3IFn());
  private static final File testDir = new File("./test");
  private static final String testPackage = "io.vacco.test";
  private static final Class<?>[] testClasses = {Object.class};
  private static final String[] testSortFields = {"field1", "field2"};
  private static final Object[] testIndexKeys = {1, "key"};
  private static final Object testObject = new Object();

  static {
    describe("MtErr Exception Factory Methods", () -> {
      it("Throws badField exception with correct message", () -> {
        try {
          throw MtErr.badField("name", userDao.dsc);
        } catch (IllegalStateException e) {
          assertEquals(
            String.format("Missing field [name] in descriptor [%s]", DbUser.class.getCanonicalName()),
            e.getMessage()
          );
        }
      });

      it("Throws badPageAccess exception with correct message and cause", () -> {
        Exception cause = new IllegalStateException("Test cause");
        try {
          throw MtErr.badPageAccess(testSortFields, testIndexKeys, userDao.dsc, cause);
        } catch (IllegalStateException e) {
          assertEquals(
            String.format(
              "Page access error for descriptor [%s], sort fields %s, index keys %s",
              DbUser.class.getCanonicalName(), Arrays.toString(testSortFields), Arrays.toString(testIndexKeys)
            ),
            e.getMessage()
          );
          assertEquals(cause, e.getCause());
        }
      });

      it("Throws badForeignKey exception with correct message", () -> {
        try {
          throw MtErr.badForeignKey("srcTable", "srcField", "String", "dstTable", "dstField", "Integer");
        } catch (IllegalStateException e) {
          assertEquals(
            "Foreign key mismatch between entities: source [srcTable.srcField:String] to destination [dstTable.dstField:Integer]. Check @MtFk annotations and PK types on both classes.",
            e.getMessage()
          );
        }
      });

      it("Throws badPkDefinitions exception with correct message", () -> {
        List<MtFieldDescriptor> keys = List.of(userDao.dsc.getField(DbUserDao.fld_email));
        try {
          throw MtErr.badPkDefinitions(keys);
        } catch (IllegalStateException e) {
          assertEquals(
            String.format("Multiple primary key definitions found: %s", keys),
            e.getMessage()
          );
        }
      });

      it("Throws badPkComponent exception with correct message", () -> {
        try {
          throw MtErr.badPkComponent(testObject, userDao.dsc.getField(DbUserDao.fld_email));
        } catch (IllegalStateException e) {
          assertEquals(
            String.format("Missing primary key for object [%s] in field [email]", testObject),
            e.getMessage()
          );
        }
      });

      it("Throws badIdGenerator exception with correct message", () -> {
        try {
          throw MtErr.badIdGenerator("TestClass", "Long", "String");
        } catch (IllegalStateException e) {
          assertEquals(
            "ID generator mismatch for class [TestClass]: pk type [Long], generator type [String]",
            e.getMessage()
          );
        }
      });

      it("Throws badSqlTypeMapping exception with correct message", () -> {
        try {
          throw MtErr.badSqlTypeMapping(userDao.dsc.getField(DbUserDao.fld_email));
        } catch (IllegalStateException e) {
          assertEquals(
            String.format("Invalid SQL type mapping for field [email] in [%s]", String.class.getCanonicalName()),
            e.getMessage()
          );
        }
      });

      it("Throws badId exception with correct message", () -> {
        try {
          throw MtErr.badId("testId");
        } catch (IllegalStateException e) {
          assertEquals("Missing ID: [testId]", e.getMessage());
        }
      });

      it("Throws badFieldAccess exception with correct message and cause", () -> {
        Exception cause = new IllegalAccessException("Access error");
        try {
          throw MtErr.badFieldAccess(testObject, "value", cause);
        } catch (IllegalStateException e) {
          assertEquals(
            String.format("Field access error for target [%s], value [value]", testObject.getClass().getCanonicalName()),
            e.getMessage()
          );
          assertEquals(cause, e.getCause());
        }
      });

      it("Throws badDaoMapping exception with correct message and cause", () -> {
        Exception cause = new IOException("IO error");
        try {
          throw MtErr.badDaoMapping(testDir, testPackage, testClasses, cause);
        } catch (IllegalStateException e) {
          assertEquals(
            String.format("DAO mapping error: outDir [%s], package [%s], classes %s",
              testDir.getAbsolutePath(), testPackage, Arrays.toString(testClasses)),
            e.getMessage()
          );
          assertEquals(cause, e.getCause());
        }
      });

      it("Fails on bash hash check", () -> {
        try {
          MtApply.checkHash("111", "222", "test");
        } catch (IllegalStateException e) {
          assertEquals(
            "Changeset [test] hash mismatch. Was [222] but is now [111]",
            e.getMessage()
          );
        }
      });
    });
  }

}
