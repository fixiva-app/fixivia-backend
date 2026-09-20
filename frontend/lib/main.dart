import 'package:flutter/material.dart';

import 'api/client.dart';
import 'app.dart';
import 'features/auth/http_auth_api.dart';

void main() {
  const flavor = String.fromEnvironment('FLAVOR', defaultValue: 'dev');
  const apiBase = String.fromEnvironment(
    'API_BASE',
    defaultValue: 'http://127.0.0.1:8080',
  );
  debugPrint('Fixiva flavor=$flavor api=$apiBase');
  final api = ApiClient(baseUrl: apiBase);
  runApp(
    FixviaApp(
      authApi: HttpAuthApi(baseUrl: apiBase),
      api: api,
    ),
  );
}
