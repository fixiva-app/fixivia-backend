import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/theme/components/components.dart';

class WorkspacePage extends StatelessWidget {
  const WorkspacePage({
    required this.title,
    required this.testId,
    required this.child,
    this.subtitle,
    this.actions,
    super.key,
  });

  final String title;
  final String? subtitle;
  final String testId;
  final Widget child;

  /// Trailing header actions (buttons, filters).
  final List<Widget>? actions;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: AppColors.canvasOf(context),
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1040),
          child: ListView(
            key: Key(testId),
            padding: const EdgeInsets.fromLTRB(24, 28, 24, 48),
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        if (subtitle != null) ...[
                          const SizedBox(height: 6),
                          Text(
                            subtitle!,
                            style: Theme.of(context).textTheme.bodyMedium
                                ?.copyWith(
                                  color: AppColors.subOf(context),
                                  height: 1.45,
                                ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  if (actions != null) ...[
                    const SizedBox(width: 16),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      alignment: WrapAlignment.end,
                      children: actions!,
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 22),
              child,
            ],
          ),
        ),
      ),
    );
  }
}

class FetchBody extends StatelessWidget {
  const FetchBody({
    required this.future,
    required this.builder,
    this.onRetry,
    this.skeletonRows = 3,
    super.key,
  });

  final Future<dynamic> future;
  final Widget Function(dynamic data) builder;

  /// When set, failures show a retry button.
  final VoidCallback? onRetry;
  final int skeletonRows;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder(
      future: future,
      builder: (context, snap) {
        if (snap.hasError) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              AppAlert(
                title: 'Could not load this page',
                description: '${snap.error}',
                destructive: true,
              ),
              if (onRetry != null) ...[
                const SizedBox(height: 12),
                Align(
                  alignment: Alignment.centerLeft,
                  child: AppButton(
                    text: 'Try again',
                    testId: 'app_fetch_retry',
                    variant: AppButtonVariant.outline,
                    expands: false,
                    leading: const Icon(Icons.refresh_rounded, size: 16),
                    onPressed: onRetry,
                  ),
                ),
              ],
            ],
          );
        }
        if (!snap.hasData) {
          return LoadingSkeleton(rows: skeletonRows);
        }
        return builder(snap.data);
      },
    );
  }
}

class EmptyHint extends StatelessWidget {
  const EmptyHint(this.text, {this.icon = Icons.inbox_outlined, super.key});

  final String text;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return EmptyState(title: text, icon: icon);
  }
}

class StatusBadge extends StatelessWidget {
  const StatusBadge(this.label, {super.key});

  final String label;

  @override
  Widget build(BuildContext context) {
    final tone = _tone(label);
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: dark ? 0.18 : 0.1),
        borderRadius: BorderRadius.circular(AppRadii.pill),
        border: Border.all(color: tone.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 7,
            height: 7,
            decoration: BoxDecoration(color: tone, shape: BoxShape.circle),
          ),
          const SizedBox(width: 6),
          Text(
            pretty(label),
            style: TextStyle(
              color: dark ? tone.lightenForDark() : tone.darkenForLight(),
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class MetricCard extends StatelessWidget {
  const MetricCard({
    required this.label,
    required this.value,
    this.icon,
    this.tint,
    super.key,
  });

  final String label;
  final String value;
  final IconData? icon;
  final Color? tint;

  @override
  Widget build(BuildContext context) {
    final accent = tint ?? AppColors.brightOrange;
    return AppCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              if (icon != null) ...[
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(icon, size: 19, color: accent),
                ),
                const SizedBox(width: 10),
              ],
              Expanded(
                child: Text(
                  label,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            value,
            style: Theme.of(
              context,
            ).textTheme.headlineSmall?.copyWith(fontSize: 26),
          ),
        ],
      ),
    );
  }
}

class InfoRow extends StatelessWidget {
  const InfoRow(this.label, this.value, {super.key});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 9),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 124,
            child: Text(
              label,
              style: TextStyle(color: AppColors.subOf(context), fontSize: 13),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontSize: 13.5,
                fontWeight: FontWeight.w600,
                height: 1.4,
                color: AppColors.inkOf(context),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

Map<String, dynamic> asMap(dynamic value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) return Map<String, dynamic>.from(value);
  return {};
}

List<Map<String, dynamic>> asMapList(dynamic value) {
  if (value is! List) return const [];
  return [for (final item in value) asMap(item)];
}

String field(Map<String, dynamic> map, String key, [String fallback = '—']) {
  final value = map[key];
  if (value == null) return fallback;
  final text = '$value'.trim();
  return text.isEmpty ? fallback : text;
}

String money(dynamic value) {
  final raw = '$value';
  if (raw.isEmpty || raw == 'null') return '₹0';
  return '₹$raw';
}

String pretty(String value) {
  final spaced = value.replaceAll('_', ' ');
  if (spaced.isEmpty) return spaced;
  return spaced[0].toUpperCase() + spaced.substring(1);
}

Color _tone(String label) {
  final key = label.toLowerCase();
  if (key.contains('approv') ||
      key.contains('complete') ||
      key.contains('paid') ||
      key.contains('active') ||
      key.contains('enabled') ||
      key.contains('submit')) {
    return AppColors.successDeep;
  }
  if (key.contains('reject') ||
      key.contains('cancel') ||
      key.contains('overdue') ||
      key.contains('suspend') ||
      key.contains('inactive') ||
      key.contains('drop') ||
      key.contains('decline')) {
    return AppColors.danger;
  }
  if (key.contains('open') ||
      key.contains('sent') ||
      key.contains('pending') ||
      key.contains('progress') ||
      key.contains('schedul') ||
      key.contains('assign')) {
    return AppColors.deepOrange;
  }
  if (key.contains('featured')) return AppColors.warning;
  return const Color(0xFF525252);
}

extension on Color {
  Color darkenForLight() {
    final hsl = HSLColor.fromColor(this);
    return hsl.withLightness((hsl.lightness - 0.08).clamp(0.0, 1.0)).toColor();
  }

  Color lightenForDark() {
    final hsl = HSLColor.fromColor(this);
    return hsl.withLightness((hsl.lightness + 0.18).clamp(0.0, 1.0)).toColor();
  }
}
