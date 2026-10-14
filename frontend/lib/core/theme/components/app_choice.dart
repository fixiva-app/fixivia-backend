import 'package:flutter/material.dart';

import '../app_theme.dart';
import 'app_test_id.dart';

/// Selectable pill used for categories, problems, slots, and filters.
/// Selected pills fill with the brand gradient and grow a check mark.
class AppChoice extends StatelessWidget {
  const AppChoice({
    required this.label,
    required this.selected,
    required this.onTap,
    required this.testId,
    this.icon,
    super.key,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;
  final String testId;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return AppTestId(
      testId: testId,
      child: _Hoverable(
        builder: (hovered) => GestureDetector(
          onTap: onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 160),
            curve: Curves.easeOut,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(
              gradient: selected ? AppColors.primaryGradient : null,
              color: selected
                  ? null
                  : hovered
                  ? (dark ? AppColors.charcoalSoft : AppColors.peachSoft)
                  : AppColors.surfaceOf(context),
              borderRadius: BorderRadius.circular(AppRadii.pill),
              border: Border.all(
                color: selected
                    ? Colors.transparent
                    : hovered
                    ? AppColors.brightOrange
                    : AppColors.lineOf(context),
              ),
              boxShadow: selected ? AppShadows.glowSoft : const [],
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (icon != null) ...[
                  Icon(
                    icon,
                    size: 16,
                    color: selected
                        ? AppColors.white
                        : AppColors.brightOrange,
                  ),
                  const SizedBox(width: 7),
                ],
                Flexible(
                  child: Text(
                    label,
                    style: TextStyle(
                      fontSize: 13.5,
                      fontWeight: FontWeight.w600,
                      color: selected
                          ? AppColors.white
                          : AppColors.inkOf(context),
                    ),
                  ),
                ),
                if (selected) ...[
                  const SizedBox(width: 6),
                  const Icon(
                    Icons.check_circle_rounded,
                    size: 16,
                    color: AppColors.white,
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Hoverable extends StatefulWidget {
  const _Hoverable({required this.builder});

  final Widget Function(bool hovered) builder;

  @override
  State<_Hoverable> createState() => _HoverableState();
}

class _HoverableState extends State<_Hoverable> {
  var _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: widget.builder(_hovered),
    );
  }
}
