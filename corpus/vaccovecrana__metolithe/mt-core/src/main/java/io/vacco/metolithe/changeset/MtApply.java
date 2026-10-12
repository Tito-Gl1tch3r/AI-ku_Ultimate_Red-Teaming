package io.vacco.metolithe.changeset;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Objects;

import static io.vacco.metolithe.changeset.MtSummary.summarize;
import static io.vacco.metolithe.core.MtErr.generalError;
import static io.vacco.metolithe.core.MtLog.info;
import static java.lang.String.format;
import static java.lang.String.join;

public class MtApply {

  private static final String MTLOG_TABLE = "MTLOG";
  private static final String MTLOCK_TABLE = "MTLOCK";
  private static final String LOCK_ID;

  static {
    try {
      var hostname = InetAddress.getLocalHost().getHostName();
      var timestamp = Instant.now().getEpochSecond();
      LOCK_ID = format("%s_%d", hostname, timestamp);
    } catch (UnknownHostException e) {
      throw generalError("Cannot determine hostname for lock ID", e);
    }
  }

  private final String schema;
  private final Connection conn;

  private boolean useTransactions = true;

  public MtApply(Connection conn, String schema) {
    this.conn = Objects.requireNonNull(conn);
    this.schema = schema;
  }

  /**
   * If true (default), wrap operations in transactions for atomicity.
   * If false, assume auto-commit mode and apply changes without explicit transactions
   * (useful for databases with limited transaction support).
   */
  public MtApply withTransactions(boolean useTransactions) {
    this.useTransactions = useTransactions;
    return this;
  }

  private boolean tableMissing(String tableName) throws SQLException {
    try (var rs = conn.getMetaData().getTables(null, null, tableName, new String[]{"TABLE"})) {
      return !rs.next();
    }
  }

  private String lockTableName() {
    return schema == null ? MTLOCK_TABLE : format("%s.%s", schema, MTLOCK_TABLE);
  }

  private String logTableName() {
    return schema == null ? MTLOG_TABLE : format("%s.%s", schema, MTLOG_TABLE);
  }

  public void init() throws SQLException {
    if (tableMissing(MTLOG_TABLE)) {
      try (var stmt = conn.createStatement()) {
        int state = stmt.executeUpdate(String.format(
          "CREATE TABLE %s (%s)",
          logTableName(),
          String.join(", ",
            "id           VARCHAR(255) NOT NULL",
            "source       VARCHAR(255)",
            "context      VARCHAR(255)",
            "hash         VARCHAR(64) NOT NULL",
            "author       VARCHAR(255)",
            "sql          VARCHAR NOT NULL",
            "description  VARCHAR(255)",
            "utcMs        BIGINT NOT NULL",
            "PRIMARY KEY  (id)"
          )
        ));
        if (state == 0) {
          info("Created table {}", logTableName());
        }
      }
    }
    if (tableMissing(MTLOCK_TABLE)) {
      try (var stmt = conn.createStatement()) {
        int state = stmt.executeUpdate(format(
          "CREATE TABLE %s (%s)",
          lockTableName(),
          join(", ",
            "id           INTEGER PRIMARY KEY",
            "locked       BOOLEAN NOT NULL",
            "lock_granted TIMESTAMP",
            "locked_by    VARCHAR(255)"
          )
        ));
        stmt.executeUpdate(format(
          "INSERT INTO %s (id, locked, lock_granted, locked_by) VALUES (1, FALSE, NULL, NULL)",
          lockTableName()
        ));
        if (state == 0) {
          info("Created table {}", lockTableName());
        }
      }
    }
  }

  public boolean claimLock() throws SQLException {
    var originalAutoCommit = conn.getAutoCommit();
    try {
      if (useTransactions) {
        conn.setAutoCommit(false);
      }
      try (var pstmt = conn.prepareStatement(format(
        "UPDATE %s SET locked = ?, lock_granted = ?, locked_by = ? WHERE id = 1 AND (locked = FALSE OR lock_granted < ?)",
        lockTableName()
      ))) {
        var staleThreshold = Timestamp.from(Instant.now().minusSeconds(300)); // 5mins, tweakable
        pstmt.setBoolean(1, true);
        pstmt.setTimestamp(2, Timestamp.from(Instant.now()));
        pstmt.setString(3, LOCK_ID);
        pstmt.setTimestamp(4, staleThreshold);
        var rowsUpdated = pstmt.executeUpdate();
        if (rowsUpdated == 1) {
          if (useTransactions) {
            conn.commit();
          }
          info("Acquired database lock");
          return true; // Lock acquired
        }
      }

      try (var checkStmt = conn.prepareStatement(format("SELECT 1 FROM %s WHERE id = 1", lockTableName()))) {
        var rs = checkStmt.executeQuery();
        if (!rs.next()) {
          try (var insStmt = conn.prepareStatement(format(
            "INSERT INTO %s (id, locked, lock_granted, locked_by) VALUES (1, TRUE, ?, ?)",
            lockTableName()
          ))) {
            insStmt.setTimestamp(1, Timestamp.from(Instant.now()));
            insStmt.setString(2, LOCK_ID);
            insStmt.executeUpdate();
            if (useTransactions) {
              conn.commit();
            }
            info("Acquired database lock (re-inserted missing row)");
            return true;
          }
        }
      }

      if (useTransactions) {
        conn.rollback();
      }
      return false; // Lock already held

    } finally {
      if (useTransactions) {
        conn.setAutoCommit(originalAutoCommit);
      }
    }
  }

  public void releaseLock() throws SQLException {
    var originalAutoCommit = conn.getAutoCommit();
    try {
      if (useTransactions) {
        conn.setAutoCommit(false);
      }
      try (var pstmt = conn.prepareStatement(format(
        "UPDATE %s SET locked = FALSE, lock_granted = NULL, locked_by = NULL WHERE id = 1 AND locked_by = ?",
        lockTableName()
      ))) {
        pstmt.setString(1, LOCK_ID);
        int state = pstmt.executeUpdate();
        if (useTransactions) {
          conn.commit();
        }
        if (state > 0) {
          info("Released database lock");
        }
      }
    } catch (SQLException e) {
      if (useTransactions) {
        conn.rollback();
      }
      throw e;
    } finally {
      if (useTransactions) {
        conn.setAutoCommit(originalAutoCommit);
      }
    }
  }

  public static void checkHash(String h0, String h1, String changeSetId) {
    if (h0 == null || !h0.equals(h1)) {
      throw generalError(
        format(
          "Changeset [%s] hash mismatch. Was [%s] but is now [%s]",
          changeSetId, h1, h0
        )
      );
    }
  }

  public void applyChanges(List<MtChange> changes, String context) throws Exception {
    init();
    if (!claimLock()) {
      throw generalError("Unable to acquire database lock");
    }
    var originalAutoCommit = conn.getAutoCommit();
    try {
      for (var chg : changes) {
        var tryApply = context == null || context.equals(chg.context);
        if (!tryApply) {
          chg.state = MtState.Skipped;
          continue;
        }
        try (var checkStmt = conn.prepareStatement(
          format("SELECT id, hash FROM %s WHERE id = ?", logTableName())
        )) {
          checkStmt.setString(1, chg.id);
          try (var rs = checkStmt.executeQuery()) {
            if (rs.next()) {
              var hash = rs.getString(2); // hash col
              checkHash(hash, chg.hash, chg.id);
              chg.state = MtState.Found;
              continue;
            }
          }
        }
        if (useTransactions) {
          conn.setAutoCommit(false);
        }
        try {
          try (var stmt = conn.createStatement()) {
            stmt.executeUpdate(chg.sql);
          }
          var nowMs = System.currentTimeMillis();
          try (var logStmt = conn.prepareStatement(
            format(
              join("\n",
                "INSERT INTO %s",
                "(id, source, context, hash, author, sql, description, utcMs)",
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
              ),
              logTableName()
            )
          )) {
            logStmt.setString(1, chg.id);
            logStmt.setString(2, chg.source);
            logStmt.setString(3, chg.context);
            logStmt.setString(4, chg.hash);
            logStmt.setString(5, chg.author);
            logStmt.setString(6, chg.sql);
            logStmt.setString(7, chg.description);
            logStmt.setLong(8, nowMs);
            logStmt.executeUpdate();
          }
          if (useTransactions) {
            conn.commit();
          }
          chg.utcMs = nowMs;
          chg.state = MtState.Applied;
          info("Executed changeset {}", chg);
        } catch (Exception e) {
          if (useTransactions) {
            conn.rollback();
          }
          chg.state = MtState.Failed;
          throw e;
        } finally {
          if (useTransactions) {
            conn.setAutoCommit(originalAutoCommit);
          }
        }
      }
    } finally {
      conn.setAutoCommit(originalAutoCommit);
      releaseLock();
      info(summarize(changes));
    }
  }

}
