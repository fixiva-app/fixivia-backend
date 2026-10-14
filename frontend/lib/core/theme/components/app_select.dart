import 'package:flutter/material.dart';

import '../app_theme.dart';
import 'app_test_id.dart';

class AppSelectItem<T> {
  const AppSelectItem({required this.value, required this.label});

  final T value;
  final String label;
}

/// In-house select styled like [AppInputField].
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
    final dark = Theme.of(context).brightness == Brightness.dark;
    return AppTestId(
      testId: testId,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (label != null) ...[
            Text(label!, style: Theme.of(context).textTheme.labelMedium),
            const SizedBox(height: 7),
          ],
          DropdownButtonFormField<T>(
            initialValue: initialValue,
            onChanged: onChanged,
            menuMaxHeight: 320,
            icon: const Icon(
              Icons.keyboard_arrow_down_rounded,
              color: AppColors.brightOrange,
            ),
            dropdownColor: AppColors.surfaceOf(context),
            borderRadius: BorderRadius.circular(AppRadii.md),
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w500,
              color: AppColors.inkOf(context),
            ),
            decoration: InputDecoration(
              hintText: placeholder,
              hintStyle: TextStyle(color: AppColors.subOf(context)),
              filled: true,
              fillColor: dark
                  ? AppColors.charcoalSoft.withValues(alpha: 0.6)
                  : AppColors.white,
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 14,
                vertical: 13,
              ),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadii.md),
                borderSide: BorderSide(color: AppColors.lineOf(context)),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadii.md),
                borderSide: BorderSide(color: AppColors.lineOf(context)),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(AppRadii.md),
                borderSide: const BorderSide(
                  color: AppColors.brightOrange,
                  width: 1.6,
                ),
              ),
            ),
            selectedItemBuilder: (context) => [
              for (final item in items)
                Align(
                  alignment: Alignment.centerLeft,
                  child: selectedOptionBuilder(context, item.value),
                ),
            ],
            items: [
              for (final item in items)
                DropdownMenuItem<T>(
                  value: item.value,
                  child: Text(
                    item.label,
                    style: TextStyle(
                      fontWeight: FontWeight.w500,
                      color: AppColors.inkOf(context),
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
