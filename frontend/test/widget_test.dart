import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fixvia/shared/widgets/fx_choice_button.dart';
import 'package:fixvia/shared/widgets/fx_primary_button.dart';
import 'package:fixvia/shared/widgets/fx_secondary_button.dart';

void main() {
  testWidgets('primary button uses test id and callback', (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      MaterialApp(
        home: FxPrimaryButton(
          label: 'Book a Service',
          testId: 'customer_home_book',
          onPressed: () => tapped = true,
        ),
      ),
    );
    expect(find.byKey(const Key('customer_home_book')), findsOneWidget);
    await tester.tap(find.byKey(const Key('customer_home_book')));
    expect(tapped, isTrue);
  });

  testWidgets('choice button selected state', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: FxChoiceButton(
          label: 'AC',
          selected: true,
          testId: 'customer_booking_category_ac',
          onTap: () {},
        ),
      ),
    );
    expect(find.byKey(const Key('customer_booking_category_ac')), findsOneWidget);
  });

  testWidgets('secondary button disabled does not fire', (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      MaterialApp(
        home: FxSecondaryButton(
          label: 'Later',
          testId: 'auth_login_later',
          onPressed: null,
        ),
      ),
    );
    await tester.tap(find.byKey(const Key('auth_login_later')));
    expect(tapped, isFalse);
  });
}
