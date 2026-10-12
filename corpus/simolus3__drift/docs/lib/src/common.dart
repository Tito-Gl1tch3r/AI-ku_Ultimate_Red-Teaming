import 'package:jaspr/server.dart';
import 'package:jaspr_content/jaspr_content.dart';
import 'package:jaspr_content/theme.dart';
import 'package:jaspr_content_snippets/jaspr_content_snippets.dart';
import 'package:jaspr_docsy/jaspr_docsy.dart';
import 'package:markdown/markdown.dart' as md;

import 'components/admonition.dart';
import 'components/collapsible.dart';
import 'components/page_ref.dart';
import 'components/web_compatibility.dart';
import 'generated_snippets.dart';
import 'layouts/docs.dart';
import 'version_data_loader.dart';

md.Document driftMarkdownDocumentBuilder() {
  return md.Document(
    blockSyntaxes: [
      ...MarkdownParser.defaultBlockSyntaxes,
      const AdmonitionSyntax(),
    ],
    extensionSet: md.ExtensionSet.gitHubWeb,
  );
}

FilesystemLoader driftWebsiteLoader() {
  return FilesystemLoader('content', keepSuffixPattern: RegExp(r'.*\.html$'));
}

ConfigResolver driftPageConfig({bool forSearchIndex = false}) {
  return PageConfig.all(
    enableFrontmatter: true,
    dataLoaders: [
      PackageVersionDataLoader(),
      MemoryDataLoader({
        'site': {'base': false},
      }),
    ],
    templateEngine: MustacheTemplateEngine(),
    parsers: [
      MarkdownParser(documentBuilder: (_) => driftMarkdownDocumentBuilder()),
      HtmlParser(),
    ],
    extensions: [
      // Adds heading anchors to each heading.
      HeadingAnchorsExtension(),
      // Generates a table of contents for each page.
      TableOfContentsExtension(),
    ],
    components: [
      PageRef(),
      BetterCodeBlock(),
      Collapsible.component(),
      DocsyTabs(),
      renderedSnippetComponent(snippets: generatedSnippets),
      CustomComponent(
        pattern: 'WebCompatibilityCheck',
        builder: (_, _, _) => WebCompatibilityCheck(),
      ),
    ],
    layouts: [if (forSearchIndex) _ContentOnlyLayout() else DriftDocsLayout()],
    theme: ContentTheme.none(),
  );
}

final class _ContentOnlyLayout extends PageLayoutBase {
  @override
  Component buildBody(Page page, Component child) {
    return child;
  }

  @override
  Pattern get name => 'text';
}
