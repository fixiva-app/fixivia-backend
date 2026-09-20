import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import 'app_test_id.dart';

/// In-house text field. Wraps [ShadInput].
class AppInputField extends StatelessWidget {
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
  Widget build(BuildContext context) {
    final field = ShadInput(
      controller: controller,
      placeholder: placeholder == null ? null : Text(placeholder!),
      leading: leading,
      trailing: trailing,
      keyboardType: keyboardType,
      maxLength: maxLength,
      inputFormatters: inputFormatters,
      obscureText: obscureText,
      enabled: enabled,
      onChanged: onChanged,
    );

    final body = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (label != null) ...[
          Text(label!, style: ShadTheme.of(context).textTheme.small),
          const SizedBox(height: 6),
        ],
        field,
      ],
    );

    return AppTestId(
      testId: testId,
      child: SizedBox(width: double.infinity, child: body),
    );
  }
}
