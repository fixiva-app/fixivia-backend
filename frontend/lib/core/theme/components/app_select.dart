import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import 'app_test_id.dart';

class AppSelectItem<T> {
  const AppSelectItem({required this.value, required this.label});

  final T value;
  final String label;
}

/// In-house select. Wraps [ShadSelect].
class AppSelect<T> extends StatelessWidget {
  const AppSelect({
    required this.testId,
    required this.items,
    required this.selectedOptionBuilder,
    this.label,
    this.placeholder,
    this.initialValue,
    this.onChanged,
    super.key,
  });

  final String testId;
  final String? label;
  final String? placeholder;
  final T? initialValue;
  final List<AppSelectItem<T>> items;
  final Widget Function(BuildContext context, T value) selectedOptionBuilder;
  final ValueChanged<T?>? onChanged;

  @override
  Widget build(BuildContext context) {
    final theme = ShadTheme.of(context);
    return AppTestId(
      testId: testId,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (label != null) ...[
            Text(label!, style: theme.textTheme.small),
            const SizedBox(height: 6),
          ],
          LayoutBuilder(
            builder: (context, constraints) {
              final width = constraints.maxWidth.isFinite
                  ? constraints.maxWidth
                  : 320.0;
              return ShadSelect<T>(
                minWidth: width,
                maxWidth: width,
                initialValue: initialValue,
                placeholder: placeholder == null ? null : Text(placeholder!),
                onChanged: onChanged,
                selectedOptionBuilder: selectedOptionBuilder,
                options: [
                  for (final item in items)
                    ShadOption(value: item.value, child: Text(item.label)),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}
