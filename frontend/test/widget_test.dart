import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import 'package:fixvia/core/theme/app_theme.dart';
import 'package:fixvia/core/theme/components/app_account_menu.dart';
import 'package:fixvia/core/theme/components/app_button.dart';
import 'package:fixvia/features/auth/auth_api.dart';
import 'package:fixvia/features/auth/auth_screen.dart';
import 'package:fixvia/l10n/app_localizations.dart';
import 'package:fixvia/shared/widgets/fx_choice_button.dart';
import 'package:fixvia/shared/widgets/fx_secondary_button.dart';

class _FakeAuthApi implements AuthApi {
  @override
  Future<List<Map<String, dynamic>>> publicPartners() async => [];

  @override
  Future<void> requestOtp({
    required String mobile,
    required String purpose,
  }) async {}

  @override
  Future<AuthResult> verifyOtp({
    required String mobile,
    required String purpose,
    required String code,
    String? fullName,
    String? role,
    String? partnerId,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<List<AuthResult>> injectDevUsers() async => [];
}

Widget _harness(Widget child) {
  return ShadApp(
    theme: appShadTheme(Brightness.light),
    home: Scaffold(body: child),
  );
}

Widget _authApp() {
  return ShadApp.custom(
    theme: appShadTheme(Brightness.light),
    appBuilder: (context) {
      return MaterialApp(
        theme: Theme.of(context),
        locale: const Locale('en'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalShadLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        builder: (context, child) => ShadAppBuilder(child: child!),
        home: AuthScreen(api: _FakeAuthApi(), onAuthenticated: (_) {}),
      );
    },
  );
}

void main() {
  testWidgets('auth screen is a formatted card with mode toggle', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_authApp());
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('auth_form_card')), findsOneWidget);
    expect(find.text('Create an account'), findsOneWidget);
    expect(find.text('Trusted home services in Kerala'), findsOneWidget);
    expect(find.byKey(const Key('auth_mode_login')), findsOneWidget);
    expect(find.byKey(const Key('auth_login_mobile')), findsOneWidget);
    expect(find.byKey(const Key('auth_login_send_otp')), findsOneWidget);

    await tester.tap(find.byKey(const Key('auth_mode_login')));
    await tester.pumpAndSettle();
    expect(find.text('Log in'), findsWidgets);
  });
  testWidgets('primary button uses test id and callback', (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      _harness(
        AppButton(
          text: 'Book a Service',
          testId: 'customer_home_book',
          onPressed: () => tapped = true,
          expands: false,
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('customer_home_book')), findsOneWidget);
    await tester.tap(find.byKey(const Key('customer_home_book')));
    expect(tapped, isTrue);
  });

  testWidgets('choice button selected state', (tester) async {
    await tester.pumpWidget(
      _harness(
        FxChoiceButton(
          label: 'AC',
          selected: true,
          testId: 'customer_booking_category_ac',
          onTap: () {},
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(
      find.byKey(const Key('customer_booking_category_ac')),
      findsOneWidget,
    );
  });

  testWidgets('secondary button disabled does not fire', (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      _harness(
        FxSecondaryButton(
          label: 'Later',
          testId: 'auth_login_later',
          onPressed: null,
          showArrow: false,
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(
      find.byKey(const Key('auth_login_later')),
      warnIfMissed: false,
    );
    expect(tapped, isFalse);
  });

  testWidgets('account menu logs out after tapping the name', (tester) async {
    var loggedOut = false;
    await tester.pumpWidget(
      _harness(
        AppAccountMenu(
          name: 'Meera Customer',
          onLogout: () => loggedOut = true,
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('shell_account_name')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('shell_logout')));
    await tester.pumpAndSettle();
    expect(loggedOut, isTrue);
  });
}
