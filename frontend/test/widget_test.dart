import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:shadcn_ui/shadcn_ui.dart';
import 'package:fixvia/api/client.dart';
import 'package:fixvia/core/theme/app_theme.dart';
import 'package:fixvia/core/theme/components/app_account_menu.dart';
import 'package:fixvia/core/theme/components/app_button.dart';
import 'package:fixvia/features/auth/auth_api.dart';
import 'package:fixvia/features/auth/auth_screen.dart';
import 'package:fixvia/features/customer/booking_flow.dart';
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

  testWidgets('auth screen compact layout renders without overflow', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_authApp());
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('auth_form_card')), findsOneWidget);
    expect(find.text('Create an account'), findsOneWidget);
    expect(find.byKey(const Key('auth_login_mobile')), findsOneWidget);
    expect(find.byKey(const Key('auth_login_send_otp')), findsOneWidget);
  });

  testWidgets('booking flow walks category then problem steps', (tester) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(_bookingApp());
    await tester.pumpAndSettle();

    expect(
      find.byKey(const Key('customer_booking_category_ac-service')),
      findsOneWidget,
    );
    expect(
      find.byKey(const Key('customer_booking_category_other')),
      findsOneWidget,
    );

    // Next without a category shows an error and stays on step 1.
    await tester.tap(find.byKey(const Key('customer_booking_next')));
    await tester.pumpAndSettle();
    expect(find.text('Pick a category'), findsOneWidget);

    await tester.tap(
      find.byKey(const Key('customer_booking_category_ac-service')),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('customer_booking_next')));
    await tester.pumpAndSettle();

    expect(
      find.byKey(const Key('customer_booking_problem_prob-1')),
      findsOneWidget,
    );
    expect(find.byKey(const Key('customer_booking_back')), findsOneWidget);
  });
}

class _FakeHttp extends http.BaseClient {
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final path = request.url.path;
    final body = switch (path) {
      '/v1/categories' => jsonEncode([
        {
          'id': 'cat-1',
          'slug': 'ac-service',
          'name_en': 'AC Service',
          'featured_rank': 1,
          'problems': [
            {
              'id': 'prob-1',
              'text_en': 'Not cooling',
              'featured_rank': 1,
            },
            {
              'id': 'prob-2',
              'text_en': 'Water leak',
              'featured_rank': null,
            },
          ],
        },
        {
          'id': 'cat-2',
          'slug': 'deep-cleaning',
          'name_en': 'Deep Cleaning',
          'featured_rank': null,
          'problems': [],
        },
      ]),
      '/v1/addresses' => jsonEncode([
        {'id': 'addr-1', 'label': 'home', 'pincode': '682001'},
      ]),
      _ => jsonEncode({}),
    };
    return http.StreamedResponse(
      Stream.value(utf8.encode(body)),
      200,
      request: request,
      headers: {'content-type': 'application/json'},
    );
  }
}

Widget _bookingApp() {
  final api = ApiClient(baseUrl: 'http://test', httpClient: _FakeHttp());
  return MaterialApp(
    theme: buildAppTheme(Brightness.light),
    locale: const Locale('en'),
    localizationsDelegates: const [
      AppLocalizations.delegate,
      GlobalMaterialLocalizations.delegate,
      GlobalWidgetsLocalizations.delegate,
      GlobalCupertinoLocalizations.delegate,
    ],
    supportedLocales: AppLocalizations.supportedLocales,
    home: BookingFlow(api: api),
  );
}
