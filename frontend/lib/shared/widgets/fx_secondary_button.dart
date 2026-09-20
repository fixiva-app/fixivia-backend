import '../../core/theme/components/app_button.dart';

/// Legacy name. Prefer [AppButton] with [AppButtonVariant.outline].
class FxSecondaryButton extends AppButton {
  const FxSecondaryButton({
    required super.testId,
    required String label,
    super.onPressed,
    super.showArrow = true,
    super.key,
  }) : super(text: label, variant: AppButtonVariant.outline);
}
