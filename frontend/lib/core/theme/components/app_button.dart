import 'package:flutter/material.dart';

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

enum AppButtonSize { sm, md, lg }

/// In-house button. Pill-shaped per the brand board: orange gradient primary
/// CTA with white label and trailing arrow; white pill secondary.
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
    this.size = AppButtonSize.md,
    super.key,
  }) : onlyIcon = null,
       onlyIconSize = 18;

  /// Circular icon-only button (back chevrons, close, etc.).
  const AppButton.iconOnly({
    required this.testId,
    required IconData icon,
    this.onPressed,
    this.variant = AppButtonVariant.outline,
    this.enabled = true,
    this.isLoading = false,
    double iconSize = 18,
    super.key,
  }) : text = '',
       leading = null,
       trailing = null,
       expands = false,
       showArrow = false,
       size = AppButtonSize.md,
       onlyIcon = icon,
       onlyIconSize = iconSize;

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
  final AppButtonSize size;

  /// Set only by [AppButton.iconOnly].
  final IconData? onlyIcon;
  final double onlyIconSize;

  bool get _iconOnly => onlyIcon != null;

  @override
  Widget build(BuildContext context) {
    final compact = appIsCompact(context);
    final fill = expands ?? compact;
    final busy = isLoading;
    final canTap = enabled && !busy && onPressed != null;
    final dark = Theme.of(context).brightness == Brightness.dark;

    final fg = _foreground(context, dark);
    final lead = busy
        ? SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(
              strokeWidth: 2.2,
              color: fg,
            ),
          )
        : leading;
    final trail = showArrow && !busy
        ? (trailing ?? Icon(Icons.arrow_forward_rounded, size: 17, color: fg))
        : trailing;

    final content = _iconOnly
        ? Icon(onlyIcon, size: onlyIconSize, color: fg)
        : Row(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (lead != null) ...[lead, const SizedBox(width: 8)],
              Flexible(
                child: Text(
                  text,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: fg,
                    fontSize: size == AppButtonSize.sm ? 13.5 : 15,
                    fontWeight: FontWeight.w600,
                    height: 1.2,
                  ),
                ),
              ),
              if (trail != null) ...[const SizedBox(width: 8), trail],
            ],
          );

    final pad = _iconOnly
        ? const EdgeInsets.all(11)
        : switch (size) {
            AppButtonSize.sm => const EdgeInsets.symmetric(
              horizontal: 16,
              vertical: 9,
            ),
            AppButtonSize.md => const EdgeInsets.symmetric(
              horizontal: 22,
              vertical: 13,
            ),
            AppButtonSize.lg => const EdgeInsets.symmetric(
              horizontal: 26,
              vertical: 16,
            ),
          };

    return AppTestId(
      testId: testId,
      child: _Pressable(
        enabled: canTap,
        onTap: onPressed,
        builder: (pressed, hovered) {
          final lift = !canTap
              ? 0.0
              : pressed
              ? -1.0
              : hovered
              ? -2.0
              : 0.0;
          return AnimatedOpacity(
            duration: const Duration(milliseconds: 150),
            opacity: canTap ? 1 : 0.45,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 150),
              curve: Curves.easeOut,
              width: fill && !_iconOnly ? double.infinity : null,
              padding: pad,
              transform: Matrix4.translationValues(0, lift, 0),
              decoration: _decoration(context, dark, hovered && canTap),
              child: _iconOnly
                  ? content
                  : Center(
                      widthFactor: fill ? null : 1,
                      child: content,
                    ),
            ),
          );
        },
      ),
    );
  }

  Color _foreground(BuildContext context, bool dark) {
    return switch (variant) {
      AppButtonVariant.primary => AppColors.white,
      AppButtonVariant.secondary =>
          dark ? AppColors.charcoal : AppColors.white,
      AppButtonVariant.destructive => AppColors.white,
      AppButtonVariant.onBrand => AppColors.deepOrange,
      AppButtonVariant.outline => AppColors.inkOf(context),
      AppButtonVariant.ghost => AppColors.inkOf(context),
    };
  }

  BoxDecoration _decoration(
    BuildContext context,
    bool dark,
    bool hovered,
  ) {
    const radius = BorderRadius.all(Radius.circular(AppRadii.pill));
    switch (variant) {
      case AppButtonVariant.primary:
        return BoxDecoration(
          gradient: AppColors.primaryGradient,
          borderRadius: radius,
          boxShadow: hovered ? AppShadows.glow : AppShadows.glowSoft,
        );
      case AppButtonVariant.secondary:
        return BoxDecoration(
          color: dark ? AppColors.white : AppColors.charcoal,
          borderRadius: radius,
          boxShadow: hovered ? AppShadows.lift : AppShadows.soft,
        );
      case AppButtonVariant.destructive:
        return BoxDecoration(
          color: AppColors.danger,
          borderRadius: radius,
          boxShadow: hovered ? AppShadows.lift : AppShadows.soft,
        );
      case AppButtonVariant.onBrand:
        return BoxDecoration(
          color: AppColors.white,
          borderRadius: radius,
          boxShadow: hovered ? AppShadows.lift : AppShadows.soft,
        );
      case AppButtonVariant.outline:
        return BoxDecoration(
          color: hovered
              ? (dark ? AppColors.charcoalSoft : AppColors.peachSoft)
              : (dark ? Colors.transparent : AppColors.white),
          borderRadius: radius,
          border: Border.all(
            color: hovered ? AppColors.brightOrange : AppColors.lineOf(context),
          ),
        );
      case AppButtonVariant.ghost:
        return BoxDecoration(
          color: hovered
              ? (dark
                    ? AppColors.white.withValues(alpha: 0.08)
                    : AppColors.charcoal.withValues(alpha: 0.06))
              : Colors.transparent,
          borderRadius: radius,
        );
    }
  }
}

/// Hover + press wrapper that rebuilds its child with interaction state.
class _Pressable extends StatefulWidget {
  const _Pressable({
    required this.builder,
    required this.enabled,
    this.onTap,
  });

  final Widget Function(bool pressed, bool hovered) builder;
  final bool enabled;
  final VoidCallback? onTap;

  @override
  State<_Pressable> createState() => _PressableState();
}

class _PressableState extends State<_Pressable> {
  var _pressed = false;
  var _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: widget.enabled
          ? SystemMouseCursors.click
          : SystemMouseCursors.basic,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() {
        _hovered = false;
        _pressed = false;
      }),
      child: GestureDetector(
        onTapDown: widget.enabled ? (_) => setState(() => _pressed = true) : null,
        onTapUp: widget.enabled ? (_) => setState(() => _pressed = false) : null,
        onTapCancel: () => setState(() => _pressed = false),
        onTap: widget.enabled ? widget.onTap : null,
        child: AnimatedScale(
          scale: _pressed && widget.enabled ? 0.97 : 1,
          duration: const Duration(milliseconds: 120),
          child: widget.builder(_pressed, _hovered),
        ),
      ),
    );
  }
}
