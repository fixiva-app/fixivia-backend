import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'fx_text_field.dart';

class FxOtpInput extends StatelessWidget {
  const FxOtpInput({
    required this.controller,
    required this.testId,
    super.key,
  });

  final TextEditingController controller;
  final String testId;

  @override
  Widget build(BuildContext context) {
    return FxTextField(
      label: 'OTP',
      testId: testId,
      controller: controller,
      keyboardType: TextInputType.number,
      maxLength: 6,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
    );
  }
}
