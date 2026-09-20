import '../../core/theme/components/app_input_field.dart';

/// Legacy name. Prefer [AppInputField].
class FxTextField extends AppInputField {
  const FxTextField({
    required super.testId,
    required String label,
    super.controller,
    super.keyboardType,
    super.maxLength,
    super.inputFormatters,
    super.key,
  }) : super(label: label, placeholder: label);
}
