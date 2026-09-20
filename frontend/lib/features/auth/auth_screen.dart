import 'package:flutter/material.dart';

import '../../core/validators.dart';
import '../../l10n/app_localizations.dart';
import '../../shared/theme/fx_colors.dart';
import '../../shared/widgets/fx_choice_button.dart';
import '../../shared/widgets/fx_logo.dart';
import '../../shared/widgets/fx_otp_input.dart';
import '../../shared/widgets/fx_primary_button.dart';
import '../../shared/widgets/fx_text_field.dart';
import 'auth_api.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({required this.api, required this.onAuthenticated, super.key});

  final AuthApi api;
  final void Function(AuthResult result) onAuthenticated;

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _mobile = TextEditingController();
  final _otp = TextEditingController();
  final _name = TextEditingController();
  var _register = true;
  var _sent = false;
  var _busy = false;
  var _role = 'customer';
  String? _partnerId;
  List<Map<String, dynamic>> _partners = [];
  String? _error;

  @override
  void dispose() {
    _mobile.dispose();
    _otp.dispose();
    _name.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final err = Validators.mobile(_mobile.text);
    if (err != null) {
      setState(() => _error = err);
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.api.requestOtp(
        mobile: _mobile.text.trim(),
        purpose: _register ? 'register' : 'login',
      );
      setState(() => _sent = true);
    } catch (_) {
      setState(() => _error = 'otp_request_failed');
    } finally {
      setState(() => _busy = false);
    }
  }

  Future<void> _verify() async {
    final err = Validators.otp(_otp.text);
    if (err != null) {
      setState(() => _error = err);
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final result = await widget.api.verifyOtp(
        mobile: _mobile.text.trim(),
        purpose: _register ? 'register' : 'login',
        code: _otp.text.trim(),
        fullName: _name.text.trim().isEmpty ? null : _name.text.trim(),
        role: _register ? _role : null,
        partnerId: _register && _role == 'service_partner' ? _partnerId : null,
      );
      widget.onAuthenticated(result);
    } catch (_) {
      setState(() => _error = 'otp_verify_failed');
    } finally {
      setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            const FxLogo(height: 36),
            const SizedBox(height: 12),
            Text(l10n.tagline, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 24),
            Row(
              children: [
                FxChoiceButton(
                  label: l10n.register,
                  selected: _register,
                  testId: 'auth_mode_register',
                  onTap: () => setState(() => _register = true),
                ),
                const SizedBox(width: 8),
                FxChoiceButton(
                  label: l10n.login,
                  selected: !_register,
                  testId: 'auth_mode_login',
                  onTap: () => setState(() => _register = false),
                ),
              ],
            ),
            if (_register) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                children: [
                  FxChoiceButton(
                    label: 'Customer',
                    selected: _role == 'customer',
                    testId: 'auth_register_role_customer',
                    onTap: () => setState(() => _role = 'customer'),
                  ),
                  FxChoiceButton(
                    label: 'Service Partner',
                    selected: _role == 'service_partner',
                    testId: 'auth_register_role_sp',
                    onTap: () async {
                      final list = await widget.api.publicPartners();
                      setState(() {
                        _role = 'service_partner';
                        _partners = list;
                        if (list.isNotEmpty) {
                          _partnerId = list.first['id'] as String;
                        }
                      });
                    },
                  ),
                ],
              ),
              if (_role == 'service_partner' && _partners.isNotEmpty)
                DropdownButton<String>(
                  key: const Key('auth_register_partner'),
                  value: _partnerId,
                  items: [
                    for (final p in _partners)
                      DropdownMenuItem(
                        value: p['id'] as String,
                        child: Text('${p['trade_name']}'),
                      ),
                  ],
                  onChanged: (v) => setState(() => _partnerId = v),
                ),
            ],
            const SizedBox(height: 16),
            if (_register)
              FxTextField(
                label: l10n.fullName,
                testId: 'auth_register_name',
                controller: _name,
              ),
            if (_register) const SizedBox(height: 12),
            FxTextField(
              label: l10n.mobileLabel,
              testId: 'auth_login_mobile',
              controller: _mobile,
              keyboardType: TextInputType.phone,
            ),
            if (_sent) ...[
              const SizedBox(height: 12),
              FxOtpInput(controller: _otp, testId: 'auth_login_otp_input'),
            ],
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: const TextStyle(color: FxColors.deepOrange)),
            ],
            const SizedBox(height: 20),
            FxPrimaryButton(
              label: _sent ? l10n.verifyOtp : l10n.sendOtp,
              testId: _sent ? 'auth_login_verify' : 'auth_login_send_otp',
              onPressed: _busy ? null : (_sent ? _verify : _send),
            ),
          ],
        ),
      ),
    );
  }
}
