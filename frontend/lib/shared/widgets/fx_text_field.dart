import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'fx_test_id.dart';

class FxTextField extends StatelessWidget {
  const FxTextField({
    required this.label,
    required this.testId,
    required this.controller,
    this.keyboardType,
    this.maxLength,
    this.inputFormatters,
    super.key,
  });

  final String label;
  final String testId;
  final TextEditingController controller;
  final TextInputType? keyboardType;
  final int? maxLength;
  final List<TextInputFormatter>? inputFormatters;

  @override
  Widget build(BuildContext context) {
    return FxTestId(
      testId: testId,
      child: TextField(
        controller: controller,
        keyboardType: keyboardType,
        maxLength: maxLength,
        inputFormatters: inputFormatters,
        decoration: InputDecoration(
          labelText: label,
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
          counterText: '',
        ),
      ),
    );
  }
}
