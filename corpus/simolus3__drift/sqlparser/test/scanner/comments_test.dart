import 'package:sqlparser/src/engine/sql_engine.dart';
import 'package:test/test.dart';

import '../parser/utils.dart';

void main() {
  test('scans comments', () {
    const sql = r'''
--line
-- line
/*c*/
/*multi
  line */
/* not terminated''';

    // using whereType instead of cast because of the invisible eof token
    final tokens = SqlEngine().tokenizeString(sql).whereType<CommentToken>();

    expect(tokens.map((t) => t.mode), [
      CommentMode.line,
      CommentMode.line,
      CommentMode.cStyle,
      CommentMode.cStyle,
      CommentMode.cStyle,
    ]);

    expect(tokens.map((t) => t.content), [
      'line',
      ' line',
      'c',
      'multi\n  line ',
      ' not terminated',
    ]);
  });

  test('supports -- comments on last line', () {
    const sql = '-- not much to see';

    final tokens = SqlEngine().tokenizeString(sql);
    expect(tokens, hasLength(2));
    expect((tokens[0] as CommentToken).content, ' not much to see');
    expect(tokens[1].type, TokenType.eof);
  });
}
