// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'Fixiva';

  @override
  String get tagline => 'Home services';

  @override
  String get mobileLabel => 'Mobile number';

  @override
  String get sendOtp => 'Send OTP';

  @override
  String get verifyOtp => 'Verify OTP';

  @override
  String get otpLabel => 'OTP';

  @override
  String get fullName => 'Full name';

  @override
  String get register => 'Register';

  @override
  String get login => 'Log in';

  @override
  String get bookAService => 'Book a Service';

  @override
  String get customerHome => 'Bookings';

  @override
  String get spHome => 'Offers';

  @override
  String get partnerHome => 'Operations';

  @override
  String get masterHome => 'Platform';
}
