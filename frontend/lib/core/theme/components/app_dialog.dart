import 'package:flutter/widgets.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

/// In-house dialog. Always use [AppDialog.show] from feature code.
class AppDialog {
  AppDialog._();

  static Future<T?> show<T>({
    required BuildContext context,
    required String title,
    String? description,
    Widget? child,
    List<Widget> actions = const [],
    bool barrierDismissible = true,
    bool alert = false,
  }) {
    return showShadDialog<T>(
      context: context,
      barrierDismissible: barrierDismissible,
      builder: (context) {
        if (alert) {
          return ShadDialog.alert(
            title: Text(title),
            description: description == null ? null : Text(description),
            actions: actions,
            child: child,
          );
        }
        return ShadDialog(
          title: Text(title),
          description: description == null ? null : Text(description),
          actions: actions,
          child: child,
        );
      },
    );
  }
}
