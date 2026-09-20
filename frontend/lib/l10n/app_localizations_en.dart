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
  String get authWelcome => 'Trusted home services in Kerala';

  @override
  String get authLoginTitle => 'Log in';

  @override
  String get authRegisterTitle => 'Create an account';

  @override
  String get authLoginSubtitle =>
      'We’ll send a one-time code to your mobile number.';

  @override
  String get authRegisterSubtitle => 'Join as a customer or a service partner.';

  @override
  String get authOtpSent => 'Enter the 6-digit code from the console / SMS.';

  @override
  String get authPartnerLabel => 'Operation partner';

  @override
  String get authPartnerPlaceholder => 'Select a partner';

  @override
  String get authRoleCustomer => 'Customer';

  @override
  String get authRoleSp => 'Service partner';

  @override
  String get authBrandPoint1 => 'Book AC, plumbing, electrical and more';

  @override
  String get authBrandPoint2 => 'First-accept dispatch — no bidding';

  @override
  String get authBrandPoint3 => 'OTP-verified start of work';

  @override
  String get authOtpFailed =>
      'Could not send OTP. Check the number and try again.';

  @override
  String get authVerifyFailed => 'That code didn’t match. Try again.';

  @override
  String get logout => 'Log out';

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
