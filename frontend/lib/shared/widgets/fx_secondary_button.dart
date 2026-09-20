import 'package:flutter/material.dart';

import '../theme/fx_colors.dart';
import 'fx_test_id.dart';

class FxSecondaryButton extends StatelessWidget {
  const FxSecondaryButton({
    required this.label,
    required this.testId,
    required this.onPressed,
    this.showArrow = true,
    super.key,
  });

  final String label;
  final String testId;
  final VoidCallback? onPressed;
  final bool showArrow;

  @override
  Widget build(BuildContext context) {
    return FxTestId(
      testId: testId,
      child: OutlinedButton(
        onPressed: onPressed,
        style: OutlinedButton.styleFrom(
          foregroundColor: FxColors.charcoal,
          side: const BorderSide(color: Color(0xFFE6E6E6)),
          backgroundColor: FxColors.white,
          shape: const StadiumBorder(),
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
            if (showArrow) ...[
              const SizedBox(width: 8),
              const Icon(Icons.arrow_forward, size: 18, color: FxColors.charcoal),
            ],
          ],
        ),
      ),
    );
  }
}
