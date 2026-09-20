import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../app_theme.dart';
import 'app_test_id.dart';

enum AppButtonVariant {
  primary,
  secondary,
  outline,
  ghost,
  destructive,
  onBrand,
}

/// In-house button. Wraps [ShadButton]; feature screens must not use ShadButton directly.
class AppButton extends StatelessWidget {
  const AppButton({
    required this.text,
    required this.testId,
    this.onPressed,
    this.variant = AppButtonVariant.primary,
    this.leading,
    this.trailing,
    this.isLoading = false,
    this.enabled = true,
    this.expands,
    this.showArrow = false,
    super.key,
  });

  final String text;
  final String testId;
  final VoidCallback? onPressed;
  final AppButtonVariant variant;
  final Widget? leading;
  final Widget? trailing;
  final bool isLoading;
  final bool enabled;
  final bool? expands;
  final bool showArrow;

  @override
  Widget build(BuildContext context) {
    final compact = appIsCompact(context);
    final fill = expands ?? compact;
    final busy = isLoading;
    final canTap = enabled && !busy && onPressed != null;
    final lead = busy
        ? const SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(strokeWidth: 2),
          )
        : leading;
    final trail = showArrow && !busy
        ? (trailing ?? const Icon(LucideIcons.arrowRight, size: 16))
        : trailing;

    final child = Text(text);
    final button = switch (variant) {
      AppButtonVariant.primary => ShadButton(
        onPressed: canTap ? onPressed : null,
        enabled: canTap,
        leading: lead,
        trailing: trail,
        expands: fill,
        gradient: AppColors.primaryGradient,
        foregroundColor: AppColors.white,
        child: child,
      ),
      AppButtonVariant.secondary => ShadButton.secondary(
        onPressed: canTap ? onPressed : null,
        enabled: canTap,
        leading: lead,
        trailing: trail,
        expands: fill,
        child: child,
      ),
      AppButtonVariant.outline => ShadButton.outline(
        onPressed: canTap ? onPressed : null,
        enabled: canTap,
        leading: lead,
        trailing: trail,
        expands: fill,
        child: child,
      ),
      AppButtonVariant.ghost => ShadButton.ghost(
        onPressed: canTap ? onPressed : null,
        enabled: canTap,
        leading: lead,
        trailing: trail,
        expands: fill,
        child: child,
      ),
      AppButtonVariant.destructive => ShadButton.destructive(
        onPressed: canTap ? onPressed : null,
        enabled: canTap,
        leading: lead,
        trailing: trail,
        expands: fill,
        child: child,
      ),
      AppButtonVariant.onBrand => ShadButton(
        onPressed: canTap ? onPressed : null,
        enabled: canTap,
        leading: lead,
        trailing: trail,
        expands: fill,
        backgroundColor: AppColors.white,
        foregroundColor: AppColors.deepOrange,
        child: child,
      ),
    };

    return AppTestId(testId: testId, child: button);
  }
}
