import 'package:flutter/material.dart';

import '../app_theme.dart';

/// In-house banner. Destructive (red), success (green), or neutral.
class AppAlert extends StatelessWidget {
  const AppAlert({
    required this.title,
    this.description,
    this.destructive = false,
    this.success = false,
    super.key,
  });

  final String title;
  final String? description;
  final bool destructive;
  final bool success;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final accent = destructive
        ? AppColors.danger
        : success
        ? AppColors.successDeep
        : AppColors.brightOrange;
    final bg = destructive
        ? AppColors.danger.withValues(alpha: dark ? 0.14 : 0.08)
        : success
        ? AppColors.success.withValues(alpha: dark ? 0.14 : 0.09)
        : (dark
              ? AppColors.white.withValues(alpha: 0.06)
              : AppColors.peachSoft);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(AppRadii.md),
        border: Border.all(color: accent.withValues(alpha: 0.35)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 30,
            height: 30,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.14),
              shape: BoxShape.circle,
            ),
            child: Icon(
              destructive
                  ? Icons.error_outline_rounded
                  : success
                  ? Icons.check_circle_outline_rounded
                  : Icons.info_outline_rounded,
              size: 17,
              color: accent,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    height: 1.35,
                    color: AppColors.inkOf(context),
                  ),
                ),
                if (description != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    description!,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
