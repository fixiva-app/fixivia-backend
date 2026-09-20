import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'api/client.dart';
import 'core/session.dart';
import 'features/auth/auth_api.dart';
import 'features/auth/auth_screen.dart';
import 'features/shells/role_shells.dart';
import 'l10n/app_localizations.dart';
import 'shared/theme/fx_theme.dart';

class FixviaApp extends StatefulWidget {
  const FixviaApp({required this.authApi, required this.api, this.locale, super.key});

  final AuthApi authApi;
  final ApiClient api;
  final Locale? locale;

  @override
  State<FixviaApp> createState() => _FixviaAppState();
}

class _FixviaAppState extends State<FixviaApp> {
  SessionUser? _user;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Fixiva',
      locale: widget.locale,
      theme: fxTheme(),
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      home: _user == null
          ? AuthScreen(
              api: widget.authApi,
              onAuthenticated: (result) {
                widget.api.token = result.token;
                setState(() => _user = result.user);
              },
            )
          : shellFor(_user!, widget.api),
    );
  }
}
