import 'package:flutter/material.dart';

import '../app_theme.dart';
import 'app_visual.dart';

/// Friendly empty state: service tile + KoHo title + hint + optional action.
class EmptyState extends StatelessWidget {
  const EmptyState({
    required this.title,
    this.hint,
    this.icon = Icons.inbox_outlined,
    this.action,
    super.key,
  });

  final String title;
  final String? hint;
  final IconData icon;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          FxServiceTile(icon: icon, size: 60),
          const SizedBox(height: 16),
          Text(
            title,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          if (hint != null) ...[
            const SizedBox(height: 6),
            Text(
              hint!,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(height: 1.5),
            ),
          ],
          if (action != null) ...[const SizedBox(height: 18), action!],
        ],
      ),
    );
  }
}

/// Pulsing placeholder list shown while a page loads.
class LoadingSkeleton extends StatefulWidget {
  const LoadingSkeleton({this.rows = 3, super.key});

  final int rows;

  @override
  State<LoadingSkeleton> createState() => _LoadingSkeletonState();
}

class _LoadingSkeletonState extends State<LoadingSkeleton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1100),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return AnimatedBuilder(
      animation: _ctrl,
      builder: (context, _) => Opacity(
        opacity: 0.45 + _ctrl.value * 0.45,
        child: Column(
          children: [
            for (var i = 0; i < widget.rows; i++) ...[
              Container(
                height: 96,
                decoration: BoxDecoration(
                  color: dark ? AppColors.charcoalSoft : AppColors.white,
                  borderRadius: BorderRadius.circular(AppRadii.lg),
                  border: Border.all(color: AppColors.lineOf(context)),
                ),
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Container(
                      width: 46,
                      height: 46,
                      decoration: BoxDecoration(
                        color: dark
                            ? AppColors.darkLine
                            : AppColors.lightGray,
                        borderRadius: BorderRadius.circular(14),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          _bar(context, dark, 0.55),
                          const SizedBox(height: 8),
                          _bar(context, dark, 0.35),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              if (i != widget.rows - 1) const SizedBox(height: 12),
            ],
          ],
        ),
      ),
    );
  }

  Widget _bar(BuildContext context, bool dark, double widthFactor) {
    return FractionallySizedBox(
      widthFactor: widthFactor,
      child: Container(
        height: 12,
        decoration: BoxDecoration(
          color: dark ? AppColors.darkLine : AppColors.lightGray,
          borderRadius: BorderRadius.circular(6),
        ),
      ),
    );
  }
}

/// Section heading row: KoHo title with an optional trailing action.
class SectionHeader extends StatelessWidget {
  const SectionHeader({
    required this.title,
    this.actionLabel,
    this.onAction,
    this.actionTestId,
    super.key,
  });

  final String title;
  final String? actionLabel;
  final VoidCallback? onAction;
  final String? actionTestId;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(title, style: Theme.of(context).textTheme.titleLarge),
        ),
        if (actionLabel != null && onAction != null)
          GestureDetector(
            key: actionTestId == null ? null : Key(actionTestId!),
            onTap: onAction,
            child: MouseRegion(
              cursor: SystemMouseCursors.click,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    actionLabel!,
                    style: const TextStyle(
                      color: AppColors.deepOrange,
                      fontWeight: FontWeight.w600,
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(width: 2),
                  const Icon(
                    Icons.arrow_forward_rounded,
                    size: 16,
                    color: AppColors.deepOrange,
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}
