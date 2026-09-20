import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fixvia/api/client.dart';
import 'package:fixvia/core/booking_rules.dart';
import 'package:fixvia/core/session.dart';
import 'package:fixvia/core/validators.dart';
import 'package:fixvia/features/shells/role_shells.dart';

void main() {
  test('mobile and otp validators', () {
    expect(Validators.mobile('9876543210'), isNull);
    expect(Validators.mobile('123'), isNotNull);
    expect(Validators.otp('123456'), isNull);
    expect(Validators.otp('12'), isNotNull);
    expect(Validators.pincode('682001'), isNull);
    expect(Validators.pincode('68'), isNotNull);
  });

  test('featured ranks 1-5 unique', () {
    expect(Validators.featuredRankOk([1, 2, 3, 4, 5]), isTrue);
    expect(Validators.featuredRankOk([1, 1]), isFalse);
    expect(Validators.featuredRankOk([0, 1]), isFalse);
    expect(Validators.featuredRankOk([1, null, 2]), isTrue);
  });

  test('48 hour booking date', () {
    final now = DateTime(2026, 9, 4, 10);
    expect(isServiceDateAllowed(DateTime(2026, 9, 6), now), isTrue);
    expect(isServiceDateAllowed(DateTime(2026, 9, 4), now), isFalse);
    expect(isServiceDateAllowed(DateTime(2026, 9, 5), now), isFalse);
  });

  test('shell routing by role', () {
    final api = ApiClient(baseUrl: 'http://localhost');
    Widget shell(UserRole role) => shellFor(
          SessionUser(id: '1', role: role, fullName: 'A'),
          api,
        );
    expect(shell(UserRole.customer), isA<WorkspaceShell>());
    expect(shell(UserRole.servicePartner), isA<WorkspaceShell>());
    expect(shell(UserRole.masterAdmin), isA<WorkspaceShell>());
  });
}
