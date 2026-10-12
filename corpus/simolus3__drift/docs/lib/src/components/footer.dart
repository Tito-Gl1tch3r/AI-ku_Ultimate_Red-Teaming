import 'package:jaspr/dom.dart';
import 'package:jaspr/jaspr.dart';
import 'package:jaspr_docsy/jaspr_docsy.dart';

final class DriftFooter extends StatelessComponent {
  const DriftFooter();

  @override
  Component build(BuildContext context) {
    return Footer(
      left: FooterLinks(
        children: [
          FooterLink(
            title: 'Drift on GitHub',
            href: 'https://github.com/simolus3/drift',
            child: i(classes: 'fa-brands fa-github', []),
          ),
        ],
      ),
      center: span(classes: 'td-footer__authors', [
        Component.text('©2019–2025'),
        span(classes: 'td-footer__authors', [
          Component.text(
            'Simon Binder, Drift authors. Documentation licensed under ',
          ),
          a(href: 'https://creativecommons.org/publicdomain/zero/1.0/', [
            Component.text('CC0 1.0'),
          ]),
          Component.text(', Drift itself is '),
          a(href: 'https://github.com/simolus3/drift/blob/develop/LICENSE', [
            Component.text('MIT-licensed'),
          ]),
        ]),
      ]),
      right: a(
        classes: 'jaspr-badge-link',
        href: 'https://jaspr.site',
        target: Target.blank,
        referrerPolicy: ReferrerPolicy.noReferrer,
        attributes: {'title': 'Built with the Jaspr web framework for Dart.'},
        [JasprBadge.light(), JasprBadge.lightTwoTone()],
      ),
    );
  }
}
