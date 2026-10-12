package io.vacco.metolithe.changeset;

import java.util.Date;
import java.util.Objects;

public class MtChange {

  /**
   * Unique identifier for the changeset
   */
  public String id;

  /**
   * What generated this change? (i.e. a file, dynamic, url)
   */
  public String source;

  /**
   * An application context group (i.e. backwards-compatible, non-backwards-compatible changes.)
   */
  public String context;

  /**
   * A hashcode of the SQL that was executed.
   */
  public String hash;

  /**
   * Who authored the change (defaults to "system" for generated changes)
   */
  public String author = "system";

  /**
   * SQL command(s) to execute
   */
  public String sql;

  /**
   * Human-readable description of the change
   */
  public String description;

  /**
   * When the change was applied, as a UNIX millisecond timestamp.
   */
  public Long utcMs;

  public transient MtState state;

  public static MtChange change(String id, String sql) {
    var chg = new MtChange();
    chg.id = Objects.requireNonNull(id);
    chg.sql = Objects.requireNonNull(sql);
    return chg;
  }

  @Override
  public String toString() {
    return String.format(
      "id=%s, source=%s, ctx=%s, hash=%s, author=%s, description=%s, utcMs=%s%n sql=%s",
      id, source, context, hash, author, description,
      utcMs != null ? new Date(utcMs) : null,
      sql
    );
  }

}