import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/theme/components/app_input_field.dart';

class FxOtpInput extends StatelessWidget {
  const FxOtpInput({required this.controller, required this.testId, super.key});

  final TextEditingController controller;
  final String testId;

  @override
  Widget build(BuildContext context) {
    return AppInputField(
      testId: testId,
      controller: controller,
      label: 'OTP',
      placeholder: '6-digit code',
      keyboardType: TextInputType.number,
      maxLength: 6,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
    );
  }
}
