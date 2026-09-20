import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../core/session.dart';
import 'auth_api.dart';

class HttpAuthApi implements AuthApi {
  HttpAuthApi({required this.baseUrl, http.Client? client})
    : _client = client ?? http.Client();

  final String baseUrl;
  final http.Client _client;

  @override
  Future<void> requestOtp({
    required String mobile,
    required String purpose,
  }) async {
    final res = await _client.post(
      Uri.parse('$baseUrl/v1/otp/request'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'mobile': mobile, 'purpose': purpose}),
    );
    if (res.statusCode != 200) {
      throw Exception('otp_request_failed');
    }
  }

  @override
  Future<List<Map<String, dynamic>>> publicPartners() async {
    final res = await _client.get(Uri.parse('$baseUrl/v1/partners/public'));
    if (res.statusCode != 200) return [];
    final list = jsonDecode(res.body) as List<dynamic>;
    return list.cast<Map<String, dynamic>>();
  }

  @override
  Future<AuthResult> verifyOtp({
    required String mobile,
    required String purpose,
    required String code,
    String? fullName,
    String? role,
    String? partnerId,
  }) async {
    final res = await _client.post(
      Uri.parse('$baseUrl/v1/otp/verify'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'mobile': mobile,
        'purpose': purpose,
        'code': code,
        if (fullName != null) 'full_name': fullName,
        if (role != null) 'role': role,
        if (partnerId != null) 'partner_id': partnerId,
      }),
    );
    if (res.statusCode != 200) {
      throw Exception('otp_verify_failed');
    }
    final json = jsonDecode(res.body) as Map<String, dynamic>;
    final user = json['user'] as Map<String, dynamic>;
    return AuthResult(
      token: json['token'] as String,
      user: SessionUser(
        id: user['id'] as String,
        role: roleFromApi(user['role'] as String),
        fullName: user['full_name'] as String,
        partnerId: user['partner_id'] as String?,
      ),
    );
  }

  @override
  Future<List<AuthResult>> injectDevUsers() async {
    final res = await _client.post(Uri.parse('$baseUrl/v1/dev/inject-users'));
    if (res.statusCode != 200) return [];
    final json = jsonDecode(res.body) as Map<String, dynamic>;
    final list = json['accounts'] as List<dynamic>? ?? [];
    return [
      for (final raw in list)
        () {
          final row = raw as Map<String, dynamic>;
          final user = row['user'] as Map<String, dynamic>;
          return AuthResult(
            token: row['token'] as String,
            user: SessionUser(
              id: user['id'] as String,
              role: roleFromApi(user['role'] as String),
              fullName: user['full_name'] as String,
              partnerId: user['partner_id'] as String?,
            ),
          );
        }(),
    ];
  }
}
