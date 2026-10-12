package io.vacco.metolithe.query;

import io.vacco.metolithe.core.MtLog;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.*;

import static io.vacco.metolithe.core.MtErr.badSql;

public class MtCmd {

  private final Map<String, Object> params = new LinkedHashMap<>();
  private final List<Object> values = new ArrayList<>();
  private MtConn connFn;

  public String sqlP;
  private final String sql;
  public int rowCount = -1;

  MtCmd(String sql, MtConn connFn) {
    this.sql = Objects.requireNonNull(sql);
    this.connFn = Objects.requireNonNull(connFn);
  }

  public MtCmd param(String name, Object value) {
    if (value instanceof Enum) {
      params.put(name, value.toString());
    } else {
      params.put(name, value);
    }
    return this;
  }

  public MtCmd prepareSql() {
    sqlP = sql;
    for (var param : params.keySet()) {
      sqlP = sqlP.replaceFirst(":" + param, "?");
      values.add(params.get(param));
    }
    return this;
  }

  public void fill(PreparedStatement ps) throws SQLException {
    for (int i = 0; i < values.size(); i++) {
      ps.setObject(i + 1, values.get(i));
    }
  }

  private void close(Connection conn) {
    try {
      conn.close();
    } catch (Exception e) {
      MtLog.warn("Failed to close connection", e);
    }
  }

  public MtCmd execute() {
    var conn = connFn.get();
    try (var ps = conn.prepareStatement(prepareSql().sqlP)) {
      this.fill(ps);
      this.rowCount = ps.executeUpdate();
      return this;
    } catch (SQLException e) {
      throw badSql(false, sql, e);
    } finally {
      if (!connFn.inTx()) {
        close(conn);
      }
    }
  }

  public <T> List<T> list(MtMapper<T> mapper) {
    var conn = connFn.get();
    try (var ps = conn.prepareStatement(prepareSql().sqlP)) {
      this.fill(ps);
      var rs = ps.executeQuery();
      var results = new ArrayList<T>();
      while (rs.next()) {
        results.add(mapper.map(rs));
      }
      return results;
    } catch (SQLException e) {
      throw badSql(true, sql, e);
    } finally {
      if (!connFn.inTx()) {
        close(conn);
      }
    }
  }

  public <T> Optional<T> one(MtMapper<T> mapper) {
    return list(mapper).stream().findFirst();
  }

  void clearConnection() {
    this.connFn = null;
  }

}
