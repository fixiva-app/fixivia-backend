import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../app_theme.dart';
import 'app_test_id.dart';

/// Selectable chip used for categories, slots, and filters.
class AppChoice extends StatelessWidget {
  const AppChoice({
    required this.label,
    required this.selected,
    required this.onTap,
    required this.testId,
    super.key,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;
  final String testId;

  @override
  Widget build(BuildContext context) {
    final button = selected
        ? ShadButton(
            onPressed: onTap,
            size: ShadButtonSize.sm,
            gradient: AppColors.primaryGradient,
            foregroundColor: AppColors.white,
            child: Text(label),
          )
        : ShadButton.outline(
            onPressed: onTap,
            size: ShadButtonSize.sm,
            child: Text(label),
          );
    return AppTestId(testId: testId, child: button);
  }
}
