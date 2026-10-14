import 'package:flutter/material.dart';

import '../app_theme.dart';

/// Maps a service-category slug to a Material icon so catalog rows,
/// booking cards, and dashboards can show a glyph per service.
IconData categoryIcon(String? slug) {
  final key = (slug ?? '').toLowerCase();
  if (key.contains('ac') || key.contains('cool') || key.contains('air')) {
    return Icons.ac_unit_rounded;
  }
  if (key.contains('plumb') || key.contains('water') || key.contains('tank')) {
    return Icons.water_drop_rounded;
  }
  if (key.contains('electric') || key.contains('wiring') || key.contains('fan')) {
    return Icons.bolt_rounded;
  }
  if (key.contains('clean') || key.contains('wash') || key.contains('laundry')) {
    return Icons.cleaning_services_rounded;
  }
  if (key.contains('appliance') ||
      key.contains('fridge') ||
      key.contains('kitchen')) {
    return Icons.kitchen_rounded;
  }
  if (key.contains('carpent') || key.contains('furniture')) {
    return Icons.chair_rounded;
  }
  if (key.contains('paint')) return Icons.format_paint_rounded;
  if (key.contains('pest')) return Icons.bug_report_rounded;
  if (key.contains('garden') || key.contains('lawn')) {
    return Icons.grass_rounded;
  }
  if (key.contains('cCTV') || key.contains('cctv') || key.contains('camera')) {
    return Icons.videocam_rounded;
  }
  if (key.contains('invert') || key.contains('batter')) {
    return Icons.battery_charging_full_rounded;
  }
  if (key.contains('purifier') || key.contains('filter')) {
    return Icons.water_drop_outlined;
  }
  if (key.contains('lock') || key.contains('key')) return Icons.key_rounded;
  if (key.contains('mason') || key.contains('tile')) {
    return Icons.construction_rounded;
  }
  if (key.contains('salon') || key.contains('beauty')) {
    return Icons.content_cut_rounded;
  }
  if (key.contains('shift') || key.contains('pack') || key.contains('move')) {
    return Icons.local_shipping_rounded;
  }
  return Icons.handyman_rounded;
}

/// Rounded service glyph tile: peach wash + orange icon, or gradient when
/// [selected]. Used across booking, catalog, and booking lists.
class FxServiceTile extends StatelessWidget {
  const FxServiceTile({
    required this.icon,
    this.size = 46,
    this.selected = false,
    this.onBrand = false,
    super.key,
  });

  final IconData icon;
  final double size;
  final bool selected;
  final bool onBrand;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final filled = selected || onBrand;
    return AnimatedContainer(
      duration: const Duration(milliseconds: 160),
      width: size,
      height: size,
      decoration: BoxDecoration(
        gradient: filled ? AppColors.primaryGradient : null,
        color: filled
            ? null
            : (dark
                  ? AppColors.brightOrange.withValues(alpha: 0.14)
                  : AppColors.peachSoft),
        borderRadius: BorderRadius.circular(size * 0.32),
        border: filled
            ? null
            : Border.all(
                color: dark
                    ? AppColors.brightOrange.withValues(alpha: 0.3)
                    : AppColors.peach,
              ),
        boxShadow: selected ? AppShadows.glowSoft : const [],
      ),
      child: Icon(
        icon,
        size: size * 0.48,
        color: filled
            ? AppColors.white
            : (dark ? AppColors.amber : AppColors.deepOrange),
      ),
    );
  }
}

/// Gradient avatar circle with initials.
class FxAvatar extends StatelessWidget {
  const FxAvatar({required this.name, this.size = 40, super.key});

  final String name;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: const BoxDecoration(
        gradient: AppColors.primaryGradientDiagonal,
        shape: BoxShape.circle,
      ),
      alignment: Alignment.center,
      child: Text(
        _initials(name),
        style: TextStyle(
          color: AppColors.white,
          fontWeight: FontWeight.w700,
          fontSize: size * 0.36,
        ),
      ),
    );
  }
}

String _initials(String name) {
  final parts = name.trim().split(RegExp(r'\s+'));
  if (parts.isEmpty || parts.first.isEmpty) return '?';
  if (parts.length == 1) return parts.first[0].toUpperCase();
  return (parts.first[0] + parts.last[0]).toUpperCase();
}

/// Decorative concentric rings for hero / brand surfaces.
class FxRings extends StatelessWidget {
  const FxRings({this.color = AppColors.white, this.opacity = 0.16, super.key});

  final Color color;
  final double opacity;

  @override
  Widget build(BuildContext context) {
    return CustomPaint(painter: _RingsPainter(color.withValues(alpha: opacity)));
  }
}

class _RingsPainter extends CustomPainter {
  _RingsPainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    final center = Offset(size.width * 0.85, size.height * 0.15);
    final maxR = size.longestSide;
    for (var i = 1; i <= 5; i++) {
      canvas.drawCircle(center, maxR * i / 5, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _RingsPainter oldDelegate) =>
      oldDelegate.color != color;
}
