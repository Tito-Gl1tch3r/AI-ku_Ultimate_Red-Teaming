import 'dart:js_interop';

import 'package:jaspr/client.dart';
import 'package:jaspr_riverpod/jaspr_riverpod.dart';

import 'package:web/web.dart' as web;

import 'main.client.options.dart';

void main() {
  Jaspr.initializeApp(options: defaultClientOptions);

  runApp(const ProviderScope(child: ClientApp(), observers: [_ErrorLogger()]));
}

final class _ErrorLogger extends ProviderObserver {
  const _ErrorLogger();

  @override
  void providerDidFail(
    ProviderObserverContext context,
    Object error,
    StackTrace stackTrace,
  ) {
    super.providerDidFail(context, error, stackTrace);

    web.console.error(
      <JSAny>[
        'Provider failed: ${context.provider.name}'.toJS,
        error.toString().toJS,
        stackTrace.toString().toJS,
      ].toJS,
    );
  }
}
