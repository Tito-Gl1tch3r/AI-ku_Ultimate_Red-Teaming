import 'package:clock/clock.dart';
// #docregion setup
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:file/local.dart';
import 'package:sqlite3/sqlite3.dart';
import 'package:sqlite3_test/sqlite3_test.dart';
import 'package:uuid/uuid.dart';
// #enddocregion setup
import 'package:test/test.dart';

import '../platforms/postgres.dart';

// #docregion setup

void main() {
  late TestSqliteFileSystem vfs;

  setUpAll(() {
    vfs = TestSqliteFileSystem(fs: const LocalFileSystem(), name: Uuid().v4());
    sqlite3.registerVirtualFileSystem(vfs);
  });
  tearDownAll(() => sqlite3.unregisterVirtualFileSystem(vfs));
  // #enddocregion setup

  late MyDatabase database;

  setUp(() {
    final rawDatabase = sqlite3.openInMemory(vfs: vfs.name);

    database = MyDatabase(
      DatabaseConnection(
        NativeDatabase.opened(rawDatabase),
        closeStreamsSynchronously: true,
      ),
    );
  });
  tearDown(() async {
    await database.close();
  });

  // #docregion test
  test('my test depending on database time', () async {
    // The VFS uses package:clock to get the current time, which can be
    // overridden for tests:
    final moonLanding = DateTime.utc(1969, 7, 20, 20, 18, 04);
    await withClock(Clock.fixed(moonLanding), () async {
      // This reads the time directly, but indirect references (e.g. in triggers
      // or default columns) would also use the mocked time.
      final row = await database.selectExpressions([
        currentDateAndTime.year,
      ]).getSingle();

      expect(row.read(currentDateAndTime.year)!, 1969);
    });
  });
  // #enddocregion test
  // #docregion setup
}

// #enddocregion setup
