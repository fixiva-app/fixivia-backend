import 'package:flutter/material.dart';

/// Stable automation id: Flutter [Key] + Semantics identifier.
class AppTestId extends StatelessWidget {
  const AppTestId({required this.testId, required this.child, super.key});

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
