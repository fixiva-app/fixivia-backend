import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'fx_colors.dart';

ThemeData fxTheme() {
  final inter = GoogleFonts.interTextTheme();
  return ThemeData(
    useMaterial3: true,
    scaffoldBackgroundColor: FxColors.lightGray,
    colorScheme: const ColorScheme.light(
      primary: FxColors.deepOrange,
      secondary: FxColors.warmOrange,
      surface: FxColors.white,
      onPrimary: FxColors.white,
      onSurface: FxColors.charcoal,
    ),
    textTheme: inter.copyWith(
      headlineMedium: GoogleFonts.koHo(
        fontWeight: FontWeight.w700,
        color: FxColors.charcoal,
      ),
      titleLarge: GoogleFonts.koHo(
        fontWeight: FontWeight.w700,
        color: FxColors.charcoal,
      ),
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: FxColors.white,
      foregroundColor: FxColors.charcoal,
      elevation: 0,
      titleTextStyle: GoogleFonts.koHo(
        fontWeight: FontWeight.w700,
        fontSize: 20,
        color: FxColors.charcoal,
      ),
    ),
  );
}
