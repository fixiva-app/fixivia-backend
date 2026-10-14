import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

/// Fixiva brand tokens (docs/Req/18-branding.md).
///
/// Primary identity stays orange gradient + charcoal. The extra tones below
/// are supporting washes and status colors only — never a second primary.
abstract final class AppColors {
  // Brand core (do not change).
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
  static const primaryGradientDiagonal = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [deepOrange, warmOrange],
  );

  // Supporting warm tones.
  static const amber = Color(0xFFFFB020);
  static const peach = Color(0xFFFFE8D3);
  static const peachSoft = Color(0xFFFFF3E8);
  static const ember = Color(0xFFC22E00);

  // Dark surfaces.
  static const charcoalDeep = Color(0xFF0C0C0C);
  static const charcoalSoft = Color(0xFF262626);
  static const darkSurface = Color(0xFF1C1917);
  static const darkCanvas = Color(0xFF0C0A09);
  static const darkLine = Color(0xFF292524);
  static const darkMuted = Color(0xFFA8A29E);
  static const darkText = Color(0xFFFAFAF9);

  // Status.
  static const success = Color(0xFF16A34A);
  static const successDeep = Color(0xFF15803D);
  static const danger = Color(0xFFDC2626);
  static const warning = Color(0xFFD97706);
  static const info = Color(0xFF2563EB);

  /// Card / sheet surface for the current brightness.
  static Color surfaceOf(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark ? darkSurface : white;

  /// Page canvas for the current brightness.
  static Color canvasOf(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark ? darkCanvas : lightGray;

  /// Primary text for the current brightness.
  static Color inkOf(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark ? darkText : charcoal;

  /// Secondary text for the current brightness.
  static Color subOf(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark ? darkMuted : muted;

  /// Hairline for the current brightness.
  static Color lineOf(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark ? darkLine : border;
}

/// Corner radii used across the app.
abstract final class AppRadii {
  static const sm = 10.0;
  static const md = 16.0;
  static const lg = 24.0;
  static const pill = 999.0;
}

/// Shared shadows. Orange glow is reserved for primary CTAs and the
/// selected nav item — cards use the soft neutral shadow.
abstract final class AppShadows {
  static const soft = [
    BoxShadow(
      color: Color(0x14000000),
      blurRadius: 16,
      offset: Offset(0, 6),
    ),
  ];
  static const lift = [
    BoxShadow(
      color: Color(0x1F000000),
      blurRadius: 28,
      offset: Offset(0, 12),
    ),
  ];
  static const glow = [
    BoxShadow(
      color: Color(0x59FD5A06),
      blurRadius: 18,
      offset: Offset(0, 8),
    ),
  ];
  static const glowSoft = [
    BoxShadow(
      color: Color(0x33FD5A06),
      blurRadius: 12,
      offset: Offset(0, 4),
    ),
  ];
}

/// KoHo headings + Inter body, per the brand doc.
TextTheme appTextTheme(Brightness brightness) {
  final base = brightness == Brightness.dark
      ? ThemeData.dark().textTheme
      : ThemeData.light().textTheme;
  final ink = brightness == Brightness.dark
      ? AppColors.darkText
      : AppColors.charcoal;
  final sub = brightness == Brightness.dark
      ? AppColors.darkMuted
      : AppColors.muted;
  return base.copyWith(
    displaySmall: GoogleFonts.koHo(
      fontSize: 40,
      fontWeight: FontWeight.w700,
      height: 1.05,
      letterSpacing: -0.5,
      color: ink,
    ),
    headlineMedium: GoogleFonts.koHo(
      fontSize: 30,
      fontWeight: FontWeight.w700,
      height: 1.12,
      letterSpacing: -0.3,
      color: ink,
    ),
    headlineSmall: GoogleFonts.koHo(
      fontSize: 24,
      fontWeight: FontWeight.w700,
      height: 1.2,
      color: ink,
    ),
    titleLarge: GoogleFonts.koHo(
      fontSize: 19,
      fontWeight: FontWeight.w600,
      height: 1.25,
      color: ink,
    ),
    titleMedium: GoogleFonts.inter(
      fontSize: 16,
      fontWeight: FontWeight.w600,
      height: 1.35,
      color: ink,
    ),
    titleSmall: GoogleFonts.inter(
      fontSize: 14,
      fontWeight: FontWeight.w600,
      height: 1.4,
      color: ink,
    ),
    bodyLarge: GoogleFonts.inter(fontSize: 16, height: 1.5, color: ink),
    bodyMedium: GoogleFonts.inter(fontSize: 14.5, height: 1.5, color: ink),
    bodySmall: GoogleFonts.inter(fontSize: 13, height: 1.45, color: sub),
    labelLarge: GoogleFonts.inter(
      fontSize: 15,
      fontWeight: FontWeight.w600,
      color: ink,
    ),
    labelMedium: GoogleFonts.inter(
      fontSize: 13,
      fontWeight: FontWeight.w600,
      color: ink,
    ),
    labelSmall: GoogleFonts.inter(
      fontSize: 12,
      fontWeight: FontWeight.w600,
      color: sub,
    ),
  );
}

ThemeData buildAppTheme(Brightness brightness) {
  final dark = brightness == Brightness.dark;
  final scheme =
      ColorScheme.fromSeed(
        seedColor: AppColors.deepOrange,
        brightness: brightness,
      ).copyWith(
        primary: AppColors.deepOrange,
        secondary: AppColors.warmOrange,
        surface: dark ? AppColors.darkSurface : AppColors.white,
        error: AppColors.danger,
      );
  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: scheme,
    scaffoldBackgroundColor: dark ? AppColors.darkCanvas : AppColors.lightGray,
    textTheme: appTextTheme(brightness),
    dividerColor: dark ? AppColors.darkLine : AppColors.border,
    datePickerTheme: DatePickerThemeData(
      headerForegroundColor: AppColors.deepOrange,
      dayForegroundColor: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) return AppColors.white;
        return dark ? AppColors.darkText : AppColors.charcoal;
      }),
      dayBackgroundColor: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return AppColors.deepOrange;
        }
        return Colors.transparent;
      }),
      todayForegroundColor: const WidgetStatePropertyAll(
        AppColors.deepOrange,
      ),
    ),
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

bool appIsWide(BuildContext context) {
  return MediaQuery.sizeOf(context).width >= 1100;
}

double appContentMaxWidth(BuildContext context) {
  return appIsCompact(context) ? double.infinity : 720;
}
