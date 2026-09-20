import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

/// Fixiva tokens on top of shadcn orange.
abstract final class AppColors {
  static const deepOrange = Color(0xFFFD3F02);
  static const warmOrange = Color(0xFFFD8D08);
  static const brightOrange = Color(0xFFFF6B35);
  static const charcoal = Color(0xFF171717);
  static const lightGray = Color(0xFFF3F3F3);
  static const white = Color(0xFFFFFFFF);
  static const muted = Color(0xFF737373);
  static const border = Color(0xFFE6E6E6);

  static const primaryGradient = LinearGradient(
    colors: [deepOrange, warmOrange],
  );
}

ShadThemeData appShadTheme(Brightness brightness) {
  final dark = brightness == Brightness.dark;
  final scheme = dark
      ? const ShadOrangeColorScheme.dark(
          primary: AppColors.deepOrange,
          ring: AppColors.deepOrange,
          background: Color(0xFF0C0A09),
          foreground: Color(0xFFFAFAF9),
          card: Color(0xFF171717),
          cardForeground: Color(0xFFFAFAF9),
        )
      : const ShadOrangeColorScheme.light(
          primary: AppColors.deepOrange,
          ring: AppColors.deepOrange,
          background: AppColors.lightGray,
          foreground: AppColors.charcoal,
          card: AppColors.white,
          cardForeground: AppColors.charcoal,
          secondary: Color(0xFFF3F3F3),
          muted: Color(0xFFF3F3F3),
          border: Color(0xFFE6E6E6),
          input: Color(0xFFE6E6E6),
        );

  return ShadThemeData(
    brightness: brightness,
    colorScheme: scheme,
    textTheme: ShadTextTheme.fromGoogleFont(GoogleFonts.inter),
  );
}

/// Compact vs desktop using shadcn md breakpoint (768).
bool appIsCompact(BuildContext context) {
  return MediaQuery.sizeOf(context).width < 768;
}

double appContentMaxWidth(BuildContext context) {
  return appIsCompact(context) ? double.infinity : 720;
}
