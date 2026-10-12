import 'package:jaspr/dom.dart';
import 'package:jaspr/jaspr.dart';

import '../platform_specific.dart';

@client
final class WebCompatibilityCheck extends StatefulComponent {
  @override
  State<StatefulComponent> createState() => _WebCompatibilityCheckState();
}

final class _WebCompatibilityCheckState extends State<WebCompatibilityCheck> {
  Future<String>? _compatibilityResult;

  void startCheck() {
    setState(() {
      _compatibilityResult ??= determineDriftWasmCompatibility();
    });
  }

  @override
  Component build(BuildContext context) {
    return FutureBuilder(
      future: _compatibilityResult,
      builder: (context, snapshot) {
        return div([
          if (_compatibilityResult == null) ...[
            button(classes: 'compat', [
              Component.text('Check compatibility'),
            ], onClick: startCheck),
            pre([Component.text('Compatibility check not started yet.')]),
          ] else if (snapshot.connectionState == ConnectionState.waiting)
            Component.text('Loading...')
          else if (snapshot.hasError)
            pre([
              Component.text(
                'Error: ${snapshot.error}, Trace:\n${snapshot.stackTrace}',
              ),
            ])
          else
            pre([Component.text(snapshot.data ?? 'No results available')]),
        ]);
      },
    );
  }
}
