import 'package:test/test.dart';

import '../../generated/converter.dart';
import '../../generated/custom_tables.dart';
import '../../test_utils.dart';

void main() {
  final table = ConfigTable();
  final column = table.syncState;
  final converter = ConfigTable.$convertersyncState;

  test('isInValues', () async {
    expect(
      column.isInValues([SyncType.synchronized, SyncType.locallyCreated]),
      generates('"sync_state" IN (?1,?2) AND "sync_state" IS NOT NULL', [
        converter.toSql(SyncType.synchronized),
        converter.toSql(SyncType.locallyCreated),
      ]),
    );
    expect(
      column.isInValues([SyncType.synchronized, SyncType.locallyCreated, null]),
      generates('"sync_state" IN (?1,?2) OR "sync_state" IS NULL', [
        converter.toSql(SyncType.synchronized),
        converter.toSql(SyncType.locallyCreated),
      ]),
    );
  });

  test('isNotInValues', () async {
    expect(
      column.isNotInValues([SyncType.synchronized, SyncType.locallyCreated]),
      generates('"sync_state" NOT IN (?1,?2) OR "sync_state" IS NULL', [
        converter.toSql(SyncType.synchronized),
        converter.toSql(SyncType.locallyCreated),
      ]),
    );
    expect(
      column.isNotInValues([
        SyncType.synchronized,
        SyncType.locallyCreated,
        null,
      ]),
      generates('"sync_state" NOT IN (?1,?2) AND "sync_state" IS NOT NULL', [
        converter.toSql(SyncType.synchronized),
        converter.toSql(SyncType.locallyCreated),
      ]),
    );
  });
}
