package io.vacco.metolithe.changeset;

import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.List;

import static java.lang.String.format;

public class MtSummary {

  private static final DateTimeFormatter DATE_FORMATTER =
    DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")
      .withZone(ZoneId.systemDefault());

  public static String summarize(List<MtChange> changes) {
    long total = changes.size();
    long applied = changes.stream().filter(c -> c.state == MtState.Applied).count();
    long skipped = changes.stream().filter(c -> c.state == MtState.Skipped).count();
    long found = changes.stream().filter(c -> c.state == MtState.Found).count();
    var sb = new StringBuilder();

    sb.append(format(
      "Changeset Summary (%s):\n",
      DATE_FORMATTER.format(Instant.now())
    ));
    sb.append(format(
      "Total: %d changesets (%d applied, %d skipped, %d found)\n",
      total, applied, skipped, found
    ));
    if (!changes.isEmpty()) {
      sb.append("Details:\n");
      changes.forEach(change -> {
        var description = change.description != null && !change.description.isEmpty()
          ? change.description
          : change.sql.length() > 32
          ? change.sql.substring(0, 32) + "..."
          : change.sql;
        sb.append(format(
          "- [%s] %s: %s\n",
          change.state != null ? change.state.name().toUpperCase() : "UNKNOWN",
          change.id,
          description
        ));
      });
    }
    return sb.toString();
  }

}