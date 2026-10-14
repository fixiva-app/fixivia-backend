import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../app_theme.dart';
import 'app_test_id.dart';

/// In-house text field: filled rounded input with an orange focus ring.
class AppInputField extends StatefulWidget {
  const AppInputField({
    required this.testId,
    this.label,
    this.placeholder,
    this.controller,
    this.leading,
    this.trailing,
    this.keyboardType,
    this.maxLength,
    this.inputFormatters,
    this.obscureText = false,
    this.enabled = true,
    this.onChanged,
    super.key,
  });

  final String testId;
  final String? label;
  final String? placeholder;
  final TextEditingController? controller;
  final Widget? leading;
  final Widget? trailing;
  final TextInputType? keyboardType;
  final int? maxLength;
  final List<TextInputFormatter>? inputFormatters;
  final bool obscureText;
  final bool enabled;
  final ValueChanged<String>? onChanged;

  @override
  State<AppInputField> createState() => _AppInputFieldState();
}

class _AppInputFieldState extends State<AppInputField> {
  final _focus = FocusNode();
  var _focused = false;

  @override
  void initState() {
    super.initState();
    _focus.addListener(() => setState(() => _focused = _focus.hasFocus));
  }

  @override
  void dispose() {
    _focus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return AppTestId(
      testId: widget.testId,
      child: SizedBox(
        width: double.infinity,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            if (widget.label != null) ...[
              Text(
                widget.label!,
                style: Theme.of(context).textTheme.labelMedium,
              ),
              const SizedBox(height: 7),
            ],
            AnimatedContainer(
              duration: const Duration(milliseconds: 160),
              decoration: BoxDecoration(
                color: dark
                    ? AppColors.charcoalSoft.withValues(alpha: 0.6)
                    : AppColors.white,
                borderRadius: BorderRadius.circular(AppRadii.md),
                border: Border.all(
                  color: _focused
                      ? AppColors.brightOrange
                      : AppColors.lineOf(context),
                  width: _focused ? 1.6 : 1,
                ),
                boxShadow: _focused ? AppShadows.glowSoft : const [],
              ),
              child: Row(
                children: [
                  if (widget.leading != null)
                    Padding(
                      padding: const EdgeInsets.only(left: 14),
                      child: widget.leading!,
                    ),
                  Expanded(
                    child: TextField(
                      focusNode: _focus,
                      controller: widget.controller,
                      keyboardType: widget.keyboardType,
                      maxLength: widget.maxLength,
                      inputFormatters: widget.inputFormatters,
                      obscureText: widget.obscureText,
                      enabled: widget.enabled,
                      onChanged: widget.onChanged,
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w500,
                        color: AppColors.inkOf(context),
                      ),
                      cursorColor: AppColors.deepOrange,
                      buildCounter:
                          (
                            _, {
                            required currentLength,
                            required isFocused,
                            maxLength,
                          }) => null,
                      decoration: InputDecoration(
                        hintText: widget.placeholder,
                        hintStyle: TextStyle(
                          color: AppColors.subOf(context),
                          fontWeight: FontWeight.w400,
                        ),
                        border: InputBorder.none,
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 14,
                        ),
                        isDense: true,
                      ),
                    ),
                  ),
                  if (widget.trailing != null)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: widget.trailing!,
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
