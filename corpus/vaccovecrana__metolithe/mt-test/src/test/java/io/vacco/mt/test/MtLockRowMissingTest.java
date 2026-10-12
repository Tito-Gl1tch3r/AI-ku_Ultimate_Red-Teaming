package io.vacco.mt.test;

import io.vacco.metolithe.changeset.MtApply;
import io.vacco.metolithe.changeset.MtChange;
import j8spec.annotation.DefinedOrder;
import j8spec.junit.J8SpecRunner;
import org.junit.runner.RunWith;

import java.sql.DriverManager;
import java.util.List;

import static j8spec.J8Spec.it;
import static org.junit.Assert.fail;

@DefinedOrder
@RunWith(J8SpecRunner.class)
public class MtLockRowMissingTest extends MtTest {

  static {
    it("Recreates the lock row if it's missing", () -> {
      var db = MtDb.Sqlite;
      try (var conn = DriverManager.getConnection(db.url)) {
        conn.setAutoCommit(true);
        var apply = new MtApply(conn, db.schema);
        apply.init();
        // Delete the lock row
        try (var stmt = conn.createStatement()) {
          stmt.executeUpdate("DELETE FROM " + (db.schema == null ? "MTLOCK" : db.schema + ".MTLOCK") + " WHERE id = 1");
        }
        // Attempt to apply a dummy change
        var change = new MtChange();
        change.id = "test-id";
        change.sql = "SELECT 1";
        change.hash = "dummy-hash";
        change.context = null;
        change.source = "test";
        change.author = "test";
        change.description = "test";
        change.utcMs = System.currentTimeMillis();
        // This should now succeed because the lock row is re-inserted
        try {
          apply.applyChanges(List.of(change), null);
        } catch (Exception e) {
          fail("Should not have thrown an exception: " + e.getMessage());
        }
      }
    });
  }
}
