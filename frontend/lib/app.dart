import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import 'api/client.dart';
import 'core/session.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/auth_api.dart';
import 'features/auth/auth_screen.dart';
import 'features/shells/role_shells.dart';
import 'l10n/app_localizations.dart';

class FixviaApp extends StatefulWidget {
  const FixviaApp({
    required this.authApi,
    required this.api,
    this.locale,
    this.themeMode = ThemeMode.system,
    super.key,
  });

  final AuthApi authApi;
  final ApiClient api;
  final Locale? locale;
  final ThemeMode themeMode;

  @override
  State<FixviaApp> createState() => _FixviaAppState();
}

class _FixviaAppState extends State<FixviaApp> {
  SessionUser? _user;

  @override
  Widget build(BuildContext context) {
    return ShadApp.custom(
      themeMode: widget.themeMode,
      theme: appShadTheme(Brightness.light),
      darkTheme: appShadTheme(Brightness.dark),
      appBuilder: (context) {
        return MaterialApp(
          title: 'Fixiva',
          locale: widget.locale,
          theme: buildAppTheme(Brightness.light),
          darkTheme: buildAppTheme(Brightness.dark),
          themeMode: widget.themeMode,
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalShadLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
          builder: (context, child) => ShadAppBuilder(child: child!),
          home: _user == null
              ? AuthScreen(
                  api: widget.authApi,
                  onAuthenticated: (result) {
                    widget.api.token = result.token;
                    setState(() => _user = result.user);
                  },
                )
              : shellFor(
                  _user!,
                  widget.api,
                  onLogout: () {
                    widget.api.token = null;
                    setState(() => _user = null);
                  },
                ),
        );
      },
    );
  }
}
