package io.vacco.metolithe.query;

import io.vacco.metolithe.core.MtLog;

import java.sql.Connection;
import java.sql.SQLException;
import java.sql.SQLWarning;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Objects;
import java.util.function.Consumer;

import static io.vacco.metolithe.core.MtErr.generalError;
import static io.vacco.metolithe.core.MtLog.debug;

public class MtTx implements AutoCloseable, MtConn {

  private MtConn connFn;
  private Connection txConn;
  private boolean isOpen, isBatch;
  private boolean shouldCommit = true;

  public List<MtResult<?>> results = new ArrayList<>();
  public List<SQLWarning> warnings = new ArrayList<>();
  public Exception error;

  public boolean isOk() {
    return error == null && warnings.isEmpty();
  }

  public MtTx orThrow() {
    if (!isOk()) {
      throw generalError("Transaction failed", error);
    }
    return this;
  }

  public MtTx supplier(MtConn connFn) {
    this.connFn = Objects.requireNonNull(connFn);
    return this;
  }

  public MtTx batch() {
    this.isBatch = true;
    return this;
  }

  private void runBatch() throws SQLException {
    var idx = new LinkedHashMap<String, List<MtResult<?>>>();
    for (var res : results) {
      var sql = res.cmd.prepareSql().sqlP;
      idx.computeIfAbsent(sql, k -> new ArrayList<>()).add(res);
    }
    for (var e : idx.entrySet()) {
      var sql = e.getValue().get(0).cmd.sqlP;
      debug("Executing batch [{}]", sql);
      try (var ps = get().prepareStatement(sql)) {
        for (var res : e.getValue()) {
          res.cmd.fill(ps);
          ps.addBatch();
        }
        var counts = ps.executeBatch();
        for (int i = 0; i < counts.length; i++) {
          e.getValue().get(i).cmd.rowCount = counts[i];
        }
      }
    }
  }

  public void run(Consumer<Connection> txConnFn) {
    try {
      this.txConn = connFn.get();
      this.txConn.setAutoCommit(false);
      this.isOpen = true;
      txConnFn.accept(txConn);
      if (shouldCommit) {
        if (isBatch) {
          runBatch();
        } else {
          for (var res : this.results) {
            res.cmd.execute();
          }
        }
      }
    } catch (SQLException e) {
      throw generalError("Failed to run transaction", e);
    }
  }

  public MtTx result(MtResult<?> res) {
    this.results.add(res);
    return this;
  }

  @Override
  public void rollback() {
    shouldCommit = false;
  }

  @Override
  public void close() {
    try {
      if (isOpen) {
        if (shouldCommit) {
          try {
            txConn.commit();
          } catch (SQLException e) {
            throw generalError("Commit failed", e);
          }
        } else {
          try {
            txConn.rollback();
          } catch (SQLException e) {
            throw generalError("Rollback failed", e);
          }
        }
        isOpen = false;
      }
    } finally {
      try {
        txConn.setAutoCommit(true);
        var txw = txConn.getWarnings();
        while (txw != null) {
          this.warnings.add(txw);
          txw = txw.getNextWarning();
        }
        txConn.clearWarnings();
        txConn.close();
      } catch (SQLException e) {
        MtLog.warn("Failed to close connection", e);
      }
    }
    for (var res : results) {
      if (res != null && res.cmd != null) {
        res.cmd.clearConnection();
      }
    }
  }

  @Override
  public Connection get() {
    return txConn;
  }

  @Override
  public boolean inTx() {
    return true;
  }

}