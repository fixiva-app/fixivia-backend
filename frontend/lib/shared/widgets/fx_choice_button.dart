import 'package:flutter/material.dart';

import '../theme/fx_colors.dart';
import 'fx_test_id.dart';

class FxChoiceButton extends StatelessWidget {
  const FxChoiceButton({
    required this.label,
    required this.selected,
    required this.onTap,
    required this.testId,
    super.key,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;
  final String testId;

  @override
  Widget build(BuildContext context) {
    return FxTestId(
      testId: testId,
      child: Material(
        color: selected ? FxColors.brightOrange : FxColors.white,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(16),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: selected ? FxColors.deepOrange : const Color(0xFFE6E6E6),
              ),
            ),
            child: Text(
              label,
              style: TextStyle(
                fontWeight: FontWeight.w600,
                color: selected ? FxColors.white : FxColors.charcoal,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
