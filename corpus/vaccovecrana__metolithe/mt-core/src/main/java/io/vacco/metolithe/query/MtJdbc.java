package io.vacco.metolithe.query;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.BiConsumer;

import static io.vacco.metolithe.core.MtErr.generalError;

public class MtJdbc implements MtConn {

  private static final Map<Thread, MtConn> txIdx = new ConcurrentHashMap<>();

  private final DataSource ds;

  public MtJdbc(DataSource ds) {
    this.ds = Objects.requireNonNull(ds);
  }

  public MtCmd select(String sql) {
    return new MtCmd(sql, this);
  }

  public MtCmd update(String sql) {
    return new MtCmd(sql, this);
  }

  public MtTx tx(BiConsumer<MtTx, Connection> txFn) {
    var tx = new MtTx().supplier(this);
    try (tx) {
      txIdx.put(Thread.currentThread(), tx);
      tx.run(conn -> txFn.accept(tx, conn));
    } catch (Exception e) {
      tx.error = generalError("Transaction failed", e);
    } finally {
      txIdx.remove(Thread.currentThread());
    }
    return tx;
  }

  private MtConn getTxFn() {
    return txIdx.get(Thread.currentThread());
  }

  @Override
  public Connection get() {
    var txFn = getTxFn();
    if (txFn != null && txFn.get() != null) {
      return txFn.get();
    }
    try {
      return ds.getConnection();
    } catch (SQLException e) {
      throw generalError("Error getting database connection", e);
    }
  }

  @Override
  public boolean inTx() {
    return getTxFn() != null;
  }

  @Override
  public void rollback() {
    var tx = getTxFn();
    if (tx != null) {
      tx.rollback();
    }
  }

}
