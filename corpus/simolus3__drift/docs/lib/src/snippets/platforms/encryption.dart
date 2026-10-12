import 'dart:io';
import 'package:drift/native.dart';
import 'package:sqlite3/sqlite3.dart';

// #docregion check_cipher
bool _debugCheckHasCipher(Database database) {
  return database.select('PRAGMA cipher;').isNotEmpty;
}
// #enddocregion check_cipher

void databases() {
  final myDatabaseFile = File('/dev/null');

  // #docregion encrypted1
  NativeDatabase.createInBackground(
    myDatabaseFile,
    setup: (rawDb) {
      rawDb.execute("PRAGMA key = 'passphrase';");
    },
  );
  // #enddocregion encrypted1

  // #docregion encrypted2
  NativeDatabase.createInBackground(
    myDatabaseFile,
    setup: (rawDb) {
      assert(_debugCheckHasCipher(rawDb));
      rawDb.execute("PRAGMA key = 'passphrase';");
    },
  );
  // #enddocregion encrypted2

  // #docregion migration
  final existingDatabasePath = '/path/to/your/database.db';
  final encryptedDatabasePath = '/path/to/your/encrypted.db';
  const yourKey = 'passphrase';

  String escapeString(String source) {
    return source.replaceAll('\'', '\'\'');
  }

  // This database can be passed to the constructor of your database class
  NativeDatabase.createInBackground(
    File(encryptedDatabasePath),
    isolateSetup: () async {
      final existing = File(existingDatabasePath);
      final encrypted = File(encryptedDatabasePath);

      if (await existing.exists() && !await encrypted.exists()) {
        // Copy an unencrypted database into a .tmp file, encrypt that file,
        // then rename the .tmp into the encrypted path.
        final tmp = File('${encrypted.path}.tmp');
        if (await tmp.exists()) {
          await tmp.delete();
        }

        // We have an existing database to migrate.
        final plaintextDb = sqlite3.open(existingDatabasePath)
          ..execute("VACUUM INTO '${escapeString(tmp.path)}';");
        plaintextDb.close();

        final encryptedDb = sqlite3.open(tmp.path);
        encryptedDb.execute("PRAGMA rekey = '${escapeString(yourKey)}';");
        encryptedDb.close();

        // This should have created the encrypted database.
        assert(await tmp.exists());
        await tmp.rename(encryptedDatabasePath);
        await existing.delete();
      }
    },
    setup: (rawDb) {
      assert(_debugCheckHasCipher(rawDb));
      rawDb.execute("PRAGMA key = '${escapeString(yourKey)}';");
    },
  );
  // #enddocregion migration
}
