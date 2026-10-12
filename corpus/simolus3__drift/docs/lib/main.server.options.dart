// dart format off
// ignore_for_file: type=lint

// GENERATED FILE, DO NOT MODIFY
// Generated with jaspr_builder

import 'package:jaspr/server.dart';
import 'package:drift_website/src/components/anchors.dart' as _anchors;
import 'package:drift_website/src/components/modal.dart' as _modal;
import 'package:drift_website/src/components/search_input.dart'
    as _search_input;
import 'package:drift_website/src/components/web_compatibility.dart'
    as _web_compatibility;
import 'package:drift_website/src/search/component.dart' as _component;
import 'package:jaspr_content_snippets/internal/client.dart' as _client;
import 'package:jaspr_docsy/components/internal/sidebar_toggle.dart'
    as _sidebar_toggle;
import 'package:jaspr_docsy/components/internal/tabs.dart' as _tabs;

/// Default [ServerOptions] for use with your Jaspr project.
///
/// Use this to initialize Jaspr **before** calling [runApp].
///
/// Example:
/// ```dart
/// import 'main.server.options.dart';
///
/// void main() {
///   Jaspr.initializeApp(
///     options: defaultServerOptions,
///   );
///
///   runApp(...);
/// }
/// ```
ServerOptions get defaultServerOptions => ServerOptions(
  clientId: 'main.client.dart.js',
  clients: {
    _anchors.ActiveAnchors: ClientTarget<_anchors.ActiveAnchors>('anchors'),
    _modal.Backdrop: ClientTarget<_modal.Backdrop>('modal'),
    _search_input.DriftSearchInput:
        ClientTarget<_search_input.DriftSearchInput>('search_input'),
    _web_compatibility.WebCompatibilityCheck:
        ClientTarget<_web_compatibility.WebCompatibilityCheck>(
          'web_compatibility',
        ),
    _component.SearchModal: ClientTarget<_component.SearchModal>('component'),
    _client.CodeBlockCopyButton: ClientTarget<_client.CodeBlockCopyButton>(
      'jaspr_content_snippets:client',
    ),
    _sidebar_toggle.MobileSidebarToggle:
        ClientTarget<_sidebar_toggle.MobileSidebarToggle>(
          'jaspr_docsy:sidebar_toggle',
          params: __sidebar_toggleMobileSidebarToggle,
        ),
    _tabs.InternalTabHeaders: ClientTarget<_tabs.InternalTabHeaders>(
      'jaspr_docsy:tabs',
      params: __tabsInternalTabHeaders,
    ),
  },
  styles: () => [],
);

Map<String, Object?> __sidebar_toggleMobileSidebarToggle(
  _sidebar_toggle.MobileSidebarToggle c,
) => {'target': c.target};
Map<String, Object?> __tabsInternalTabHeaders(_tabs.InternalTabHeaders c) => {
  'items': c.items,
};
