import '../../core/theme/components/app_button.dart';

/// Legacy name. Prefer [AppButton].
class FxPrimaryButton extends AppButton {
  const FxPrimaryButton({
    required super.testId,
    required String label,
    super.onPressed,
    super.showArrow = true,
    super.key,
  }) : super(text: label);
}
