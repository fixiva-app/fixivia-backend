import 'package:flutter/material.dart';

/// Stable automation id: Flutter [Key] plus Semantics identifier (web/UI tests).
class FxTestId extends StatelessWidget {
  const FxTestId({required this.testId, required this.child, super.key});

  final String testId;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      identifier: testId,
      container: true,
      child: KeyedSubtree(key: Key(testId), child: child),
    );
  }
}
