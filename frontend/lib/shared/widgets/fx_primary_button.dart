import 'package:flutter/material.dart';

import '../theme/fx_colors.dart';
import 'fx_test_id.dart';

class FxPrimaryButton extends StatelessWidget {
  const FxPrimaryButton({
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
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onPressed,
          borderRadius: BorderRadius.circular(999),
          child: Ink(
            decoration: BoxDecoration(
              gradient: onPressed == null ? null : FxColors.primaryGradient,
              color: onPressed == null ? const Color(0xFFC4C4C4) : null,
              borderRadius: BorderRadius.circular(999),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    label,
                    style: const TextStyle(
                      color: FxColors.white,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (showArrow) ...[
                    const SizedBox(width: 8),
                    const Icon(Icons.arrow_forward, color: FxColors.white, size: 18),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
