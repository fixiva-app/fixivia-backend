import 'package:flutter/widgets.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

/// In-house alert. Wraps [ShadAlert].
class AppAlert extends StatelessWidget {
  const AppAlert({
    required this.title,
    this.description,
    this.destructive = false,
    super.key,
  });

  final String title;
  final String? description;
  final bool destructive;

  @override
  Widget build(BuildContext context) {
    if (destructive) {
      return ShadAlert.destructive(
        icon: const Icon(LucideIcons.circleAlert),
        title: Text(title),
        description: description == null ? null : Text(description!),
      );
    }
    return ShadAlert(
      icon: const Icon(LucideIcons.info),
      title: Text(title),
      description: description == null ? null : Text(description!),
    );
  }
}
