import 'dart:collection';

import 'package:meta/meta.dart';
import 'package:source_span/source_span.dart';
import 'package:sqlparser/sqlparser.dart';
import 'package:sqlparser/src/reader/parser.dart';
import 'package:sqlparser/src/reader/tokenizer/scanner.dart';

import '../reader/tokenizer/token_source.dart';
import 'autocomplete/engine.dart';
import 'builtin_tables.dart';

final class SqlEngine {
  /// All tables registered with [registerTable].
  final List<NamedResultSet> knownResultSets = [];
  final List<Module> _knownModules = [];

  /// Internal options for this sql engine.
  final EngineOptions options;

  SchemaFromCreateTable? _schemaReader;

  SqlEngine([EngineOptions? engineOptions])
    : options = engineOptions ?? EngineOptions() {
    for (final extension in options.enabledExtensions) {
      extension.register(this);
    }

    registerTable(sqliteMaster);
    // sqlite3_schema has been added in sqlite 3.33.0 as an alias to the master
    // table. Since 3.34.0 is the first version for which we have feature flags,
    // we just add it unconditionally.
    registerTable(sqliteSchema);

    registerTable(sqliteSequence);
  }

  /// Obtain a [SchemaFromCreateTable] instance compatible with the
  /// configuration of this engine.
  ///
  /// The returned reader can be used to read the table structure from a
  /// [TableInducingStatement] by using [SchemaFromCreateTable.read].
  SchemaFromCreateTable get schemaReader {
    return _schemaReader ??= _createSchemaReader(null);
  }

  SchemaFromCreateTable _createSchemaReader(
    AnalyzeStatementOptions? stmtOptions,
  ) {
    final driftOptions = options.driftOptions;

    if (stmtOptions != null) {
      return SchemaFromCreateTable(
        driftExtensions: driftOptions != null,
        driftUseTextForDateTime: driftOptions?.storeDateTimesAsText == true,
        statementOptions: stmtOptions,
      );
    } else {
      return _schemaReader ??= SchemaFromCreateTable(
        driftExtensions: driftOptions != null,
        driftUseTextForDateTime: driftOptions?.storeDateTimesAsText == true,
      );
    }
  }

  /// Registers the [table], which means that it can later be used in sql
  /// statements.
  void registerTable(Table table) {
    registerResultSet(table);
  }

  /// Registers the [view], which means that it can later be used in sql
  /// statements.
  void registerView(View view) {
    registerResultSet(view);
  }

  /// Registers an arbitrary [namedResultSet], which means that it can later
  /// be used in sql statements.
  void registerResultSet(NamedResultSet namedResultSet) {
    knownResultSets.add(namedResultSet);
  }

  /// Registers the [module], which means that it can be used as a function in
  /// `CREATE VIRTUAL TABLE` statements.
  void registerModule(Module module) {
    _knownModules.add(module);
  }

  /// Registers the [handler], which can provide implementations for additional
  /// sql functions that can then be used in statements analyzed through this
  /// engine.
  void registerFunctionHandler(FunctionHandler handler) {
    options.addFunctionHandler(handler);
  }

  /// Registers the [handler], which can infer result sets for a table-valued
  /// function.
  void registerTableValuedFunctionHandler(TableValuedFunctionHandler handler) {
    options.addTableValuedFunctionHandler(handler);
  }

  RootScope _constructRootScope() {
    final scope = RootScope();

    for (final resultSet in knownResultSets) {
      scope.knownTables[resultSet.name] = resultSet;
    }

    for (final module in _knownModules) {
      scope.knownModules[module.name] = module;
    }

    return scope;
  }

  TokenSource _prepareScanning(FileSpan source) {
    final scanner = Scanner(
      source,
      scanDriftTokens: options.useDriftExtensions,
      scanDoubleColonTokens: options.supportPostgresCasts,
    );
    return TokenSource(scanner);
  }

  /// Tokenizes the [source] into a list list [Token]s. Each [Token] contains
  /// information about where it appears in the [source] and a [TokenType].
  ///
  /// If an error occurs while tokenizing, e.g. because an invalid token is
  /// found, throws a [CumulatedTokenizerException].
  ///
  /// Note that the list might be tokens that should be
  /// [Token.invisibleToParser], if you're passing them to a [Parser] directly,
  /// you need to filter them. When using the methods in this class, this will
  /// be taken care of automatically.
  List<Token> tokenize(FileSpan source) {
    final scanner = _prepareScanning(source)..readTokensUntilEnd();

    final errors = scanner.scanner.errors;
    if (errors.isNotEmpty) {
      throw CumulatedTokenizerException(errors);
    }

    return scanner.tokens;
  }

  /// Like [tokenize], but with a [FileSpan] created from the [sql] string.
  List<Token> tokenizeString(String sql) {
    return tokenize(stringSpan(sql));
  }

  /// Parses an SQL structure starting from the given [ParserEntrypoint].
  ///
  /// This method generally doesn't throw, but instead collects parsing errors
  /// through [ParseResult.errors]. Callers should check that value instead of
  /// blindly trusting the returned AST, as it will be an approximation if
  /// parsing errors were encountered.
  ///
  /// When [autoComplete] is enabled (it's disabled by default), the returned
  /// [ParseResult.autoCompleteEngine] will be set and can be queries for auto-
  /// complete inference.
  ParseResult<Root> parseSpan<Root extends AstNode>(
    ParserEntrypoint<Root> entrypoint,
    FileSpan sql, {
    bool autoComplete = false,
  }) {
    final tokenizer = _prepareScanning(sql);
    final autoCompleteEngine = autoComplete ? AutoCompleteEngine(this) : null;
    final disableDriftExtensions =
        entrypoint == ParserEntrypoint.columnConstraints ||
        entrypoint == ParserEntrypoint.tableConstraint;

    final parser = ParserState(
      tokenizer,
      options: EngineOptions(
        driftOptions: disableDriftExtensions ? null : options.driftOptions,
        supportSchemaInFunctionNames: options.supportSchemaInFunctionNames,
      ),
      autoComplete: autoCompleteEngine,
    );

    final node = entrypoint._parse(parser);
    if (node is DriftFile) {
      node.scope = _constructRootScope();
    }

    autoCompleteEngine?.installTokens(tokenizer.tokens);
    for (final error in tokenizer.scanner.errors) {
      parser.errors.add(ParsingError(error, error.message));
    }

    return ParseResult._(
      node,
      tokenizer.tokens,
      parser.errors,
      sql,
      autoCompleteEngine,
    );
  }

  /// Like [parseSpan], but with a [FileSpan] created from the [sql] string.
  ParseResult<Root> parse<Root extends AstNode>(
    ParserEntrypoint<Root> entrypoint,
    String sql,
  ) {
    return parseSpan(entrypoint, stringSpan(sql));
  }

  /// Parses and analyzes the [sql] statement. The [AnalysisContext] returned
  /// contains all information about type hints, errors, and the parsed AST.
  ///
  /// The analyzer needs to know all the available tables to resolve references
  /// and result columns, so all known tables should be registered using
  /// [registerTable] before calling this method.
  /// The [stmtOptions] can be used to pass additional options used to analyze
  /// this statement only.
  AnalysisContext analyzeSpan(
    FileSpan sql, {
    AnalyzeStatementOptions? stmtOptions,
  }) {
    final result = parseSpan(ParserEntrypoint.statement, sql);
    final analyzed = analyzeParsed(result, stmtOptions: stmtOptions);

    // Add parsing errors that occurred at the beginning since they are the most
    // prominent problems.
    analyzed.errors.insertAll(0, result.errors.map(AnalysisError.fromParser));

    return analyzed;
  }

  /// Like [analyzeSpan], but with a [FileSpan] created from the [sql] string.
  AnalysisContext analyze(String sql, {AnalyzeStatementOptions? stmtOptions}) {
    return analyzeSpan(stringSpan(sql), stmtOptions: stmtOptions);
  }

  /// Analyzes a parsed [result] statement. The [AnalysisContext] returned
  /// contains all information about type hints, errors, and the parsed AST.
  ///
  /// The analyzer needs to know all the available tables to resolve references
  /// and result columns, so all known tables should be registered using
  /// [registerTable] before calling this method.
  /// The [stmtOptions] can be used to pass additional options used to analyze
  /// this statement only.
  AnalysisContext analyzeParsed(
    ParseResult result, {
    AnalyzeStatementOptions? stmtOptions,
  }) {
    final node = result.rootNode;
    return analyzeNode(node, result.sql, stmtOptions: stmtOptions);
  }

  /// Analyzes the given [node], which should be a [CrudStatement].
  /// The [AnalysisContext] enhances the AST by reporting type hints and errors.
  /// The [file] should contain the full SQL source code that was used to parse
  /// the [node].
  ///
  /// The analyzer needs to know all the available tables to resolve references
  /// and result columns, so all known tables should be registered using
  /// [registerTable] before calling this method.
  /// The [stmtOptions] can be used to pass additional options used to analyze
  /// this statement only.
  AnalysisContext analyzeNode(
    AstNode node,
    FileSpan file, {
    AnalyzeStatementOptions? stmtOptions,
  }) {
    final context = _createContext(node, file, stmtOptions);
    _analyzeContext(context);
    return context;
  }

  AnalysisContext _createContext(
    AstNode node,
    FileSpan sql,
    AnalyzeStatementOptions? stmtOptions,
  ) {
    final schemaSupport = _createSchemaReader(stmtOptions);

    return AnalysisContext(
      node,
      sql,
      _constructRootScope(),
      options,
      stmtOptions: stmtOptions,
      schemaSupport: schemaSupport,
    );
  }

  void _analyzeContext(AnalysisContext context) {
    final node = context.root;
    node.scope = context.rootScope;

    AstPreparingVisitor(context: context).start(node);

    node
      ..accept(ColumnResolver(context), const ColumnResolverContext())
      ..accept(ReferenceResolver(context), const ReferenceResolvingContext());

    final session = TypeInferenceSession(context, options);
    final resolver = TypeResolver(session);
    resolver.run(node);
    context.types2 = session.results!;

    node.acceptWithoutArg(LintingVisitor(options, context));
  }
}

/// Different parse entrypoints that can be used by [SqlEngine.parseSpan] and
/// [SqlEngine.parse] to parse SQL text.
enum ParserEntrypoint<Root extends AstNode> {
  /// Parse a single SQL statement.
  statement<Statement>(_parseStatement),

  /// Parse multiple SQL statements separated by a semicolon.
  multiple<SemicolonSeparatedStatements>(_parseStatements),

  /// Used internally by `drift_dev`.
  driftFile<DriftFile>(_parseDriftFile),

  /// Parse a single table constraint.
  ///
  /// The [ParseResult.rootNode] will either be a [TableConstraint] or an
  /// [InvalidStatement] in case of parsing errors.
  tableConstraint<AstNode>(_parseTableConstraint),

  /// Parse a list of column constraints.
  ///
  /// The [ParseResult.rootNode] will be a [ColumnDefinition] with the parsed
  /// constraints.
  columnConstraints<ColumnDefinition>(_parseColumnConstraints),

  /// Parse a single expression.
  expression<Expression>(_parseExpression);

  final Root Function(ParserState) _parse;

  const ParserEntrypoint(this._parse);

  static Statement _parseStatement(ParserState state) {
    return state.safeStatement();
  }

  static SemicolonSeparatedStatements _parseStatements(ParserState state) {
    return state.safeStatements();
  }

  static DriftFile _parseDriftFile(ParserState state) {
    return state.driftFile();
  }

  static ColumnDefinition _parseColumnConstraints(ParserState state) {
    return ColumnDefinition(
      columnName: '',
      typeName: '',
      constraints: state.columnConstraintsUntilEnd(),
    );
  }

  static AstNode _parseTableConstraint(ParserState state) {
    try {
      if (state.tableConstraintOrNull(requireConstraint: true)
          case final constraint?) {
        return constraint;
      }
    } on ParsingError {
      // Ignore, will be added to parser.errors anyway
    }

    return InvalidStatement();
  }

  static Expression _parseExpression(ParserState state) {
    return state.expression();
  }
}

/// The result of parsing an sql query. Contains the root of the AST and all
/// errors that might have occurred during parsing.
final class ParseResult<Root extends AstNode> {
  /// The topmost node in the sql AST that was parsed.
  final Root rootNode;

  /// The tokens that were scanned in the source file, including those that are
  /// [Token.invisibleToParser].
  final List<Token> tokens;

  /// A list of all errors that occurred during parsing. [ParsingError.toString]
  /// returns a helpful description of what went wrong, along with the position
  /// where the error occurred.
  final List<ParsingError> errors;

  /// The sql source that created the AST at [rootNode].
  final FileSpan sql;

  /// The engine which can be used to handle auto-complete requests on this
  /// result.
  final AutoCompleteEngine? autoCompleteEngine;

  ParseResult._(
    this.rootNode,
    this.tokens,
    this.errors,
    this.sql,
    this.autoCompleteEngine,
  ) {
    const SetParentVisitor().startAtRoot(rootNode);
  }

  /// Attempts to find the most relevant (bottom-most in the AST) nodes that
  /// intersects with the source range from [offset] to [offset] + [length].
  List<AstNode> findNodesAtPosition(int offset, {int length = 0}) {
    if (tokens.isEmpty) return const [];

    final candidates = <AstNode>{};
    final unchecked = Queue<AstNode>();
    unchecked.add(rootNode);

    while (unchecked.isNotEmpty) {
      final node = unchecked.removeFirst();

      final span = node.span!;
      final start = span.start.offset;
      final end = span.end.offset;

      final hasIntersection = !(end < offset || start > offset + length);
      if (hasIntersection) {
        // this node matches. As we want to find the bottom-most node in the AST
        // that matches, this means that the parent is no longer a candidate.
        candidates.add(node);
        candidates.remove(node.parent);

        // assume that the span of a node is a superset of the span of any
        // child, so each child could potentially be interesting.
        unchecked.addAll(node.childNodes);
      }
    }

    return candidates.toList();
  }

  /// Returns the lexeme that created an AST [node] (which should be a child of
  /// [rootNode], e.g appear in this result).
  String lexemeOfNode(AstNode node) {
    return sql.text.substring(node.firstPosition, node.lastPosition);
  }
}

@internal
FileSpan stringSpan(String source) {
  return SourceFile.fromString(source).span(0);
}
