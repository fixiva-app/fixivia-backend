import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../app_theme.dart';

/// In-house card. Wraps [ShadCard].
class AppCard extends StatelessWidget {
  const AppCard({
    this.title,
    this.description,
    this.child,
    this.footer,
    this.leading,
    this.trailing,
    this.onTap,
    this.testId,
    super.key,
  });

  final String? title;
  final String? description;
  final Widget? child;
  final Widget? footer;
  final Widget? leading;
  final Widget? trailing;
  final VoidCallback? onTap;
  final String? testId;

  @override
  Widget build(BuildContext context) {
    final compact = appIsCompact(context);
    final card = ShadCard(
      width: double.infinity,
      padding: EdgeInsets.all(compact ? 16 : 24),
      title: title == null ? null : Text(title!),
      description: description == null ? null : Text(description!),
      leading: leading,
      trailing: trailing,
      footer: footer,
      child: child,
    );
    final wrapped = onTap == null
        ? card
        : MouseRegion(
            cursor: SystemMouseCursors.click,
            child: GestureDetector(onTap: onTap, child: card),
          );
    if (testId == null) return wrapped;
    return KeyedSubtree(key: Key(testId!), child: wrapped);
  }
}
