import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/session.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/components/components.dart';
import '../../core/validators.dart';
import '../../l10n/app_localizations.dart';
import '../../shared/widgets/fx_logo.dart';
import 'auth_api.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({
    required this.api,
    required this.onAuthenticated,
    super.key,
  });

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
  List<AuthResult> _devAccounts = [];

  @override
  void initState() {
    super.initState();
    if (kDebugMode) {
      _loadDevAccounts();
    }
  }

  Future<void> _loadDevAccounts() async {
    try {
      final list = await widget.api.injectDevUsers();
      if (!mounted || list.isEmpty) return;
      setState(() => _devAccounts = list);
    } catch (_) {}
  }

  @override
  void dispose() {
    _mobile.dispose();
    _otp.dispose();
    _name.dispose();
    super.dispose();
  }

  void _setMode(bool register) {
    setState(() {
      _register = register;
      _sent = false;
      _otp.clear();
      _error = null;
    });
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

  String _errorText(AppLocalizations l10n) {
    return switch (_error) {
      'otp_request_failed' => l10n.authOtpFailed,
      'otp_verify_failed' => l10n.authVerifyFailed,
      _ => _error ?? '',
    };
  }

  @override
  Widget build(BuildContext context) {
    final compact = appIsCompact(context);
    if (compact) return _compact();
    return Scaffold(
      backgroundColor: AppColors.lightGray,
      body: Row(
        children: [
          const Expanded(flex: 5, child: _BrandPane()),
          Expanded(
            flex: 6,
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(
                  horizontal: 48,
                  vertical: 40,
                ),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 460),
                  child: _formCard(),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _compact() {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      backgroundColor: AppColors.lightGray,
      body: SafeArea(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            Container(
              padding: const EdgeInsets.fromLTRB(24, 28, 24, 56),
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    AppColors.charcoalDeep,
                    AppColors.charcoal,
                    AppColors.ember,
                    AppColors.deepOrange,
                  ],
                  stops: [0.0, 0.42, 0.78, 1.0],
                ),
                borderRadius: BorderRadius.vertical(
                  bottom: Radius.circular(32),
                ),
              ),
              child: Stack(
                children: [
                  const Positioned.fill(child: FxRings(opacity: 0.18)),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const FxLogo(white: true, height: 34),
                      const SizedBox(height: 18),
                      Text(
                        l10n.appTitle,
                        style: Theme.of(context).textTheme.displaySmall
                            ?.copyWith(color: AppColors.white, fontSize: 36),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        l10n.authWelcome,
                        style: const TextStyle(
                          color: Color(0xE6FFFFFF),
                          fontSize: 15,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 32),
              child: Transform.translate(
                offset: const Offset(0, -32),
                child: _formCard(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _formCard() {
    return _AuthFormCard(
      register: _register,
      sent: _sent,
      busy: _busy,
      role: _role,
      partnerId: _partnerId,
      partners: _partners,
      error: _error,
      errorText: _error == null ? null : _errorText,
      name: _name,
      mobile: _mobile,
      otp: _otp,
      onMode: _setMode,
      onCustomer: () => setState(() => _role = 'customer'),
      onServicePartner: _pickServicePartner,
      onPartnerChanged: (id) => setState(() => _partnerId = id),
      onSubmit: _busy ? null : (_sent ? _verify : _send),
      devAccounts: _devAccounts,
      onDevLogin: widget.onAuthenticated,
    );
  }

  Future<void> _pickServicePartner() async {
    final list = await widget.api.publicPartners();
    setState(() {
      _role = 'service_partner';
      _partners = list;
      if (list.isNotEmpty) {
        _partnerId = list.first['id'] as String;
      }
    });
  }
}

class _BrandPane extends StatelessWidget {
  const _BrandPane();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            AppColors.charcoalDeep,
            AppColors.charcoal,
            AppColors.ember,
            AppColors.deepOrange,
          ],
          stops: [0.0, 0.42, 0.78, 1.0],
        ),
      ),
      child: Stack(
        children: [
          const Positioned.fill(child: FxRings(opacity: 0.16)),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(52, 44, 52, 40),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const FxLogo(white: true, height: 40),
                  const Spacer(),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.white.withValues(alpha: 0.14),
                      borderRadius: BorderRadius.circular(AppRadii.pill),
                      border: Border.all(
                        color: AppColors.white.withValues(alpha: 0.25),
                      ),
                    ),
                    child: Text(
                      l10n.tagline,
                      style: const TextStyle(
                        color: AppColors.white,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    l10n.appTitle,
                    style: Theme.of(context).textTheme.displaySmall?.copyWith(
                      color: AppColors.white,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    l10n.authWelcome,
                    style: const TextStyle(
                      color: Color(0xE6FFFFFF),
                      fontSize: 17,
                      height: 1.45,
                    ),
                  ),
                  const SizedBox(height: 32),
                  _BrandPoint(text: l10n.authBrandPoint1),
                  const SizedBox(height: 12),
                  _BrandPoint(text: l10n.authBrandPoint2),
                  const SizedBox(height: 12),
                  _BrandPoint(text: l10n.authBrandPoint3),
                  const Spacer(),
                  const Wrap(
                    spacing: 26,
                    runSpacing: 12,
                    children: [
                      _MiniStat(value: '2', label: 'slots / day'),
                      _MiniStat(value: 'OTP', label: 'verified work'),
                      _MiniStat(value: '#1', label: 'first-accept wins'),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _MiniStat extends StatelessWidget {
  const _MiniStat({required this.value, required this.label});

  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          value,
          style: const TextStyle(
            color: AppColors.white,
            fontSize: 22,
            fontWeight: FontWeight.w800,
          ),
        ),
        Text(
          label,
          style: TextStyle(
            color: AppColors.white.withValues(alpha: 0.75),
            fontSize: 12,
          ),
        ),
      ],
    );
  }
}

class _BrandPoint extends StatelessWidget {
  const _BrandPoint({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
      decoration: BoxDecoration(
        color: AppColors.white.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(AppRadii.md),
        border: Border.all(color: AppColors.white.withValues(alpha: 0.16)),
      ),
      child: Row(
        children: [
          Container(
            width: 24,
            height: 24,
            decoration: const BoxDecoration(
              color: AppColors.white,
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.check_rounded,
              size: 15,
              color: AppColors.deepOrange,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(
                color: AppColors.white,
                fontSize: 14.5,
                fontWeight: FontWeight.w500,
                height: 1.35,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _AuthFormCard extends StatelessWidget {
  const _AuthFormCard({
    required this.register,
    required this.sent,
    required this.busy,
    required this.role,
    required this.partnerId,
    required this.partners,
    required this.error,
    required this.errorText,
    required this.name,
    required this.mobile,
    required this.otp,
    required this.onMode,
    required this.onCustomer,
    required this.onServicePartner,
    required this.onPartnerChanged,
    required this.onSubmit,
    required this.devAccounts,
    required this.onDevLogin,
  });

  final bool register;
  final bool sent;
  final bool busy;
  final String role;
  final String? partnerId;
  final List<Map<String, dynamic>> partners;
  final String? error;
  final String Function(AppLocalizations l10n)? errorText;
  final TextEditingController name;
  final TextEditingController mobile;
  final TextEditingController otp;
  final ValueChanged<bool> onMode;
  final VoidCallback onCustomer;
  final VoidCallback onServicePartner;
  final ValueChanged<String?> onPartnerChanged;
  final VoidCallback? onSubmit;
  final List<AuthResult> devAccounts;
  final void Function(AuthResult result) onDevLogin;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final title = register ? l10n.authRegisterTitle : l10n.authLoginTitle;
    final subtitle = sent
        ? l10n.authOtpSent
        : (register ? l10n.authRegisterSubtitle : l10n.authLoginSubtitle);

    return SizedBox(
      width: double.infinity,
      child: AppCard(
        testId: 'auth_form_card',
        padding: const EdgeInsets.all(28),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(title, style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 8),
            Text(
              subtitle,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: AppColors.muted,
                height: 1.45,
              ),
            ),
            const SizedBox(height: 22),
            _ModeToggle(
              register: register,
              loginLabel: l10n.login,
              registerLabel: l10n.register,
              onChanged: onMode,
            ),
            if (register) ...[
              const SizedBox(height: 18),
              Text(
                'I am joining as',
                style: Theme.of(context).textTheme.labelMedium,
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  AppChoice(
                    label: l10n.authRoleCustomer,
                    icon: Icons.home_rounded,
                    selected: role == 'customer',
                    testId: 'auth_register_role_customer',
                    onTap: onCustomer,
                  ),
                  AppChoice(
                    label: l10n.authRoleSp,
                    icon: Icons.handyman_rounded,
                    selected: role == 'service_partner',
                    testId: 'auth_register_role_sp',
                    onTap: onServicePartner,
                  ),
                ],
              ),
              if (role == 'service_partner' && partners.isNotEmpty) ...[
                const SizedBox(height: 14),
                AppSelect<String>(
                  testId: 'auth_register_partner',
                  label: l10n.authPartnerLabel,
                  placeholder: l10n.authPartnerPlaceholder,
                  initialValue: partnerId,
                  items: [
                    for (final p in partners)
                      AppSelectItem(
                        value: p['id'] as String,
                        label: '${p['trade_name']}',
                      ),
                  ],
                  selectedOptionBuilder: (context, value) {
                    for (final p in partners) {
                      if (p['id'] == value) {
                        return Text('${p['trade_name']}');
                      }
                    }
                    return Text(value);
                  },
                  onChanged: onPartnerChanged,
                ),
              ],
              const SizedBox(height: 14),
              AppInputField(
                label: l10n.fullName,
                placeholder: l10n.fullName,
                testId: 'auth_register_name',
                controller: name,
              ),
            ],
            const SizedBox(height: 14),
            AppInputField(
              label: l10n.mobileLabel,
              placeholder: '9000000001',
              testId: 'auth_login_mobile',
              controller: mobile,
              keyboardType: TextInputType.phone,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              leading: const Text(
                '+91',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  color: AppColors.charcoal,
                ),
              ),
            ),
            if (sent) ...[
              const SizedBox(height: 14),
              AppInputField(
                testId: 'auth_login_otp_input',
                controller: otp,
                label: l10n.otpLabel,
                placeholder: '••••••',
                keyboardType: TextInputType.number,
                maxLength: 6,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              ),
            ],
            if (error != null && errorText != null) ...[
              const SizedBox(height: 14),
              AppAlert(title: errorText!(l10n), destructive: true),
            ],
            const SizedBox(height: 22),
            AppButton(
              text: sent ? l10n.verifyOtp : l10n.sendOtp,
              testId: sent ? 'auth_login_verify' : 'auth_login_send_otp',
              onPressed: onSubmit,
              isLoading: busy,
              expands: true,
              size: AppButtonSize.lg,
              showArrow: !busy,
            ),
            if (kDebugMode && devAccounts.isNotEmpty) ...[
              const SizedBox(height: 20),
              const Divider(height: 1, color: AppColors.border),
              const SizedBox(height: 12),
              const Text(
                'Dev only — enter as',
                style: TextStyle(fontSize: 12, color: Color(0xFF737373)),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final acc in devAccounts)
                    AppChoice(
                      label: _devRoleLabel(acc.user.role),
                      selected: false,
                      testId: 'auth_dev_login_${acc.user.role.name}',
                      onTap: () => onDevLogin(acc),
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ModeToggle extends StatelessWidget {
  const _ModeToggle({
    required this.register,
    required this.loginLabel,
    required this.registerLabel,
    required this.onChanged,
  });

  final bool register;
  final String loginLabel;
  final String registerLabel;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.lightGray,
        borderRadius: BorderRadius.circular(AppRadii.pill),
      ),
      child: Padding(
        padding: const EdgeInsets.all(4),
        child: Row(
          children: [
            Expanded(
              child: _Segment(
                label: registerLabel,
                selected: register,
                testId: 'auth_mode_register',
                onTap: () => onChanged(true),
              ),
            ),
            const SizedBox(width: 4),
            Expanded(
              child: _Segment(
                label: loginLabel,
                selected: !register,
                testId: 'auth_mode_login',
                onTap: () => onChanged(false),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Segment extends StatelessWidget {
  const _Segment({
    required this.label,
    required this.selected,
    required this.testId,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final String testId;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return AppTestId(
      testId: testId,
      child: GestureDetector(
        onTap: onTap,
        child: MouseRegion(
          cursor: SystemMouseCursors.click,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            padding: const EdgeInsets.symmetric(vertical: 11),
            decoration: BoxDecoration(
              gradient: selected ? AppColors.primaryGradient : null,
              color: selected ? null : Colors.transparent,
              borderRadius: BorderRadius.circular(AppRadii.pill),
              boxShadow: selected ? AppShadows.glowSoft : const [],
            ),
            alignment: Alignment.center,
            child: Text(
              label,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: selected ? AppColors.white : AppColors.muted,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

String _devRoleLabel(UserRole role) {
  return switch (role) {
    UserRole.masterAdmin => 'Master',
    UserRole.partnerOwner => 'Owner',
    UserRole.partnerAdmin => 'P-admin',
    UserRole.servicePartner => 'Technician',
    UserRole.customer => 'Customer',
  };
}
