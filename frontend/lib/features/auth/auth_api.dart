import '../../core/session.dart';

class AuthResult {
  const AuthResult({required this.token, required this.user});
  final String token;
  final SessionUser user;
}

abstract class AuthApi {
  Future<void> requestOtp({required String mobile, required String purpose});
  Future<List<Map<String, dynamic>>> publicPartners();
  Future<AuthResult> verifyOtp({
    required String mobile,
    required String purpose,
    required String code,
    String? fullName,
    String? role,
    String? partnerId,
  });

  /// Dev-only. Empty list when the API is not in flavor=dev.
  Future<List<AuthResult>> injectDevUsers();
}
