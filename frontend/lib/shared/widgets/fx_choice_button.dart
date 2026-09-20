import '../../core/theme/components/app_choice.dart';

/// Legacy name. Prefer [AppChoice].
class FxChoiceButton extends AppChoice {
  const FxChoiceButton({
    required super.label,
    required super.selected,
    required super.onTap,
    required super.testId,
    super.key,
  });
}
