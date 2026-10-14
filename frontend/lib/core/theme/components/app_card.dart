import 'package:flutter/material.dart';

import '../app_theme.dart';

/// In-house card: white rounded surface, hairline border, soft shadow.
/// Tappable cards lift slightly on hover (desktop/web).
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
    this.padding,
    this.tint,
    this.gradient,
    this.borderColor,
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

  /// Overrides the default content padding.
  final EdgeInsetsGeometry? padding;

  /// Flat background override. Ignored when [gradient] is set.
  final Color? tint;

  /// Background gradient override (hero / promo cards).
  final Gradient? gradient;

  /// Border override. Defaults to the theme hairline.
  final Color? borderColor;

  @override
  Widget build(BuildContext context) {
    final compact = appIsCompact(context);
    final dark = Theme.of(context).brightness == Brightness.dark;
    final pad = padding ?? EdgeInsets.all(compact ? 16 : 20);

    final body = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (title != null || leading != null || trailing != null) ...[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (leading != null) ...[leading!, const SizedBox(width: 12)],
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (title != null)
                      Text(
                        title!,
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontSize: 17,
                          color: gradient != null
                              ? AppColors.white
                              : AppColors.inkOf(context),
                        ),
                      ),
                    if (title != null && description != null)
                      const SizedBox(height: 4),
                    if (description != null)
                      Text(
                        description!,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          height: 1.45,
                          color: gradient != null
                              ? AppColors.white.withValues(alpha: 0.85)
                              : AppColors.subOf(context),
                        ),
                      ),
                  ],
                ),
              ),
              if (trailing != null) ...[
                const SizedBox(width: 12),
                trailing!,
              ],
            ],
          ),
        ],
        if (child != null) ...[
          if (title != null || leading != null || trailing != null)
            const SizedBox(height: 14),
          child!,
        ],
        if (footer != null) ...[const SizedBox(height: 16), footer!],
      ],
    );

    final card = AnimatedContainer(
      duration: const Duration(milliseconds: 160),
      width: double.infinity,
      padding: pad,
      decoration: BoxDecoration(
        color: gradient == null
            ? (tint ?? AppColors.surfaceOf(context))
            : null,
        gradient: gradient,
        borderRadius: BorderRadius.circular(AppRadii.lg),
        border: gradient == null
            ? Border.all(color: borderColor ?? AppColors.lineOf(context))
            : null,
        boxShadow: dark && gradient == null ? null : AppShadows.soft,
      ),
      child: body,
    );

    final interactive = onTap == null
        ? card
        : _HoverLift(onTap: onTap!, child: card);
    if (testId == null) return interactive;
    return KeyedSubtree(key: Key(testId!), child: interactive);
  }
}

/// Lifts a tappable surface on hover.
class _HoverLift extends StatefulWidget {
  const _HoverLift({required this.onTap, required this.child});

  final VoidCallback onTap;
  final Widget child;

  @override
  State<_HoverLift> createState() => _HoverLiftState();
}

class _HoverLiftState extends State<_HoverLift> {
  var _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          curve: Curves.easeOut,
          transform: Matrix4.translationValues(0, _hovered ? -3 : 0, 0),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppRadii.lg),
            boxShadow: _hovered ? AppShadows.lift : const [],
          ),
          child: widget.child,
        ),
      ),
    );
  }
}
