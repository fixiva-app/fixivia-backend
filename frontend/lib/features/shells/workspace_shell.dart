import 'package:flutter/material.dart';

import '../../api/client.dart';
import '../../core/session.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/components/components.dart';
import '../../l10n/app_localizations.dart';
import '../../shared/widgets/fx_logo.dart';
import '../customer/booking_flow.dart';
import 'pages/resource_pages.dart';
import 'pages/workspace_page.dart';

class WorkspaceShell extends StatefulWidget {
  const WorkspaceShell({
    required this.api,
    required this.user,
    this.onLogout,
    super.key,
  });

  final ApiClient api;
  final SessionUser user;
  final VoidCallback? onLogout;

  @override
  State<WorkspaceShell> createState() => _WorkspaceShellState();
}

class _WorkspaceShellState extends State<WorkspaceShell> {
  var _index = 0;

  List<_Tab> get _tabs {
    switch (widget.user.role) {
      case UserRole.customer:
        return [
          _Tab(
            'Home',
            Icons.home,
            () => _CustomerHome(api: widget.api, user: widget.user),
            testId: 'nav_home',
          ),
          _Tab(
            'Bookings',
            Icons.event,
            () => BookingsListPage(
              api: widget.api,
              path: '/v1/bookings',
              testId: 'customer_bookings',
              title: 'Your bookings',
              onOpen: (id) => _openBooking(id),
            ),
          ),
          _Tab('Addresses', Icons.place, () => _AddressesPage(api: widget.api)),
        ];
      case UserRole.servicePartner:
        return [
          _Tab('Inbox', Icons.inbox, () => _OffersPage(api: widget.api)),
          _Tab(
            'Schedule',
            Icons.calendar_today,
            () => SchedulePage(api: widget.api),
          ),
          _Tab('Earnings', Icons.payments, () => EarningsPage(api: widget.api)),
          _Tab('Profile', Icons.person, () => _SpProfilePage(api: widget.api)),
          _Tab(
            'Reports',
            Icons.insights,
            () => AnalyticsPage(api: widget.api, testId: 'sp_reports'),
          ),
        ];
      case UserRole.partnerOwner:
      case UserRole.partnerAdmin:
        return [
          _Tab(
            'Open',
            Icons.pending,
            () => BookingsListPage(
              api: widget.api,
              path: '/v1/bookings?status=open',
              testId: 'partner_open',
              title: 'Open requests',
              onOpen: _openBooking,
            ),
          ),
          _Tab(
            'Upcoming',
            Icons.upcoming,
            () => BookingsListPage(
              api: widget.api,
              testId: 'partner_upcoming',
              title: 'Bookings',
              onOpen: _openBooking,
            ),
          ),
          _Tab('Roster', Icons.groups, () => _RosterPage(api: widget.api)),
          _Tab('Pricing', Icons.sell, () => PricingPage(api: widget.api)),
          _Tab(
            'Analytics',
            Icons.insights,
            () => AnalyticsPage(api: widget.api, testId: 'partner_analytics'),
          ),
        ];
      case UserRole.masterAdmin:
        return [
          _Tab(
            'Partners',
            Icons.apartment,
            () => PartnersPage(api: widget.api),
          ),
          _Tab(
            'Categories',
            Icons.category,
            () => CategoriesPage(api: widget.api),
          ),
          _Tab(
            'Admins',
            Icons.person_add,
            () => AdminRequestsPage(api: widget.api),
          ),
          _Tab('Invoices', Icons.receipt, () => InvoicesPage(api: widget.api)),
          _Tab(
            'Analytics',
            Icons.insights,
            () => AnalyticsPage(api: widget.api, testId: 'master_analytics'),
          ),
        ];
    }
  }

  void _openBooking(String id) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => _BookingDetail(api: widget.api, id: id),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final tabs = _tabs;
    final body = tabs[_index].builder();
    return AppWorkspaceFrame(
      brand: const FxLogo(height: 28),
      account: AppAccountMenu(
        name: widget.user.fullName,
        subtitle: _roleLabel(widget.user.role),
        logoutLabel: AppLocalizations.of(context).logout,
        onLogout: widget.onLogout ?? () {},
      ),
      destinations: [
        for (final t in tabs)
          AppNavDest(label: t.label, icon: t.icon, testId: t.testId),
      ],
      selectedIndex: _index,
      onSelect: (i) => setState(() => _index = i),
      body: body,
    );
  }
}

String _roleLabel(UserRole role) {
  return switch (role) {
    UserRole.masterAdmin => 'Master admin',
    UserRole.partnerOwner => 'Partner owner',
    UserRole.partnerAdmin => 'Partner admin',
    UserRole.servicePartner => 'Service partner',
    UserRole.customer => 'Customer',
  };
}

class _Tab {
  const _Tab(this.label, this.icon, this.builder, {this.testId});
  final String label;
  final IconData icon;
  final Widget Function() builder;
  final String? testId;
}

class _CustomerHome extends StatelessWidget {
  const _CustomerHome({required this.api, required this.user});
  final ApiClient api;
  final SessionUser user;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return WorkspacePage(
      title: 'Hi, ${user.fullName}',
      subtitle: l10n.authWelcome,
      testId: 'customer_home',
      child: Column(
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(28),
            decoration: BoxDecoration(
              gradient: AppColors.primaryGradient,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Ready when you are',
                  style: TextStyle(color: Color(0xE6FFFFFF), fontSize: 14),
                ),
                const SizedBox(height: 8),
                Text(
                  l10n.bookAService,
                  style: const TextStyle(
                    color: AppColors.white,
                    fontSize: 28,
                    fontWeight: FontWeight.w700,
                    height: 1.15,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  l10n.tagline,
                  style: const TextStyle(
                    color: Color(0xE6FFFFFF),
                    fontSize: 15,
                  ),
                ),
                const SizedBox(height: 20),
                AppButton(
                  text: l10n.bookAService,
                  testId: 'customer_home_book',
                  variant: AppButtonVariant.onBrand,
                  expands: false,
                  showArrow: true,
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => BookingFlow(api: api)),
                    );
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _BookingDetail extends StatefulWidget {
  const _BookingDetail({required this.api, required this.id});
  final ApiClient api;
  final String id;

  @override
  State<_BookingDetail> createState() => _BookingDetailState();
}

class _BookingDetailState extends State<_BookingDetail> {
  final _otp = TextEditingController();
  String? _msg;

  @override
  Widget build(BuildContext context) {
    return AppSubpageScaffold(
      title: 'Booking',
      child: FutureBuilder(
        future: widget.api.get('/v1/bookings/${widget.id}'),
        builder: (context, snap) {
          if (snap.hasError) {
            return Padding(
              padding: const EdgeInsets.all(24),
              child: AppAlert(title: '${snap.error}', destructive: true),
            );
          }
          if (!snap.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final b = snap.data as Map<String, dynamic>;
          return ListView(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 40),
            children: [
              AppCard(
                title: '${b['category_name'] ?? 'Booking'}',
                description:
                    '${b['service_date']} · ${b['slot']} · ${b['pincode']}',
                trailing: StatusBadge('${b['status']}'),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    InfoRow(
                      'Technician',
                      '${b['technician_name'] ?? 'Waiting'} ${b['technician_mobile_masked'] ?? ''}'
                          .trim(),
                    ),
                    InfoRow('OTP hint', '${b['start_work_otp_hint'] ?? '—'}'),
                    const SizedBox(height: 16),
                    AppInputField(
                      label: 'Start-work OTP',
                      testId: 'sp_start_otp',
                      controller: _otp,
                      placeholder: '6-digit code',
                    ),
                    if (_msg != null) ...[
                      const SizedBox(height: 12),
                      AppAlert(title: _msg!, destructive: _msg != 'ok'),
                    ],
                    const SizedBox(height: 16),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        AppButton(
                          text: 'Accept',
                          testId: 'sp_offer_accept',
                          expands: false,
                          onPressed: () =>
                              _act('/v1/bookings/${widget.id}/accept'),
                        ),
                        AppButton(
                          text: 'Decline',
                          testId: 'sp_offer_decline',
                          variant: AppButtonVariant.outline,
                          expands: false,
                          onPressed: () =>
                              _act('/v1/bookings/${widget.id}/decline'),
                        ),
                        AppButton(
                          text: 'Start work',
                          testId: 'sp_start_work',
                          variant: AppButtonVariant.secondary,
                          expands: false,
                          onPressed: () => _act(
                            '/v1/bookings/${widget.id}/start',
                            {'code': _otp.text},
                          ),
                        ),
                        AppButton(
                          text: 'Complete',
                          testId: 'sp_complete',
                          variant: AppButtonVariant.outline,
                          expands: false,
                          onPressed: () => _act(
                            '/v1/bookings/${widget.id}/complete',
                            {'payment_mode': 'cash'},
                          ),
                        ),
                        AppButton(
                          text: 'Drop',
                          testId: 'sp_drop',
                          variant: AppButtonVariant.ghost,
                          expands: false,
                          onPressed: () =>
                              _act('/v1/bookings/${widget.id}/drop'),
                        ),
                        AppButton(
                          text: 'Cancel',
                          testId: 'customer_booking_cancel',
                          variant: AppButtonVariant.destructive,
                          expands: false,
                          onPressed: () =>
                              _act('/v1/bookings/${widget.id}/cancel'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Future<void> _act(String path, [Map<String, dynamic>? body]) async {
    try {
      await widget.api.post(path, body);
      if (mounted) setState(() => _msg = 'ok');
    } catch (e) {
      setState(() => _msg = e.toString());
    }
  }
}

class _OffersPage extends StatelessWidget {
  const _OffersPage({required this.api});
  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    return WorkspacePage(
      title: 'Open offers',
      subtitle: 'First accept wins the job.',
      testId: 'sp_inbox',
      child: FetchBody(
        future: api.get('/v1/offers'),
        builder: (data) {
          final items = data as List<dynamic>;
          if (items.isEmpty) return const EmptyHint('No open offers.');
          return Column(
            children: [
              for (final o in items) ...[
                AppCard(
                  title: '${o['category_name']} · ${o['pincode']}',
                  description:
                      '${o['service_date']} · ${o['slot']} · load ${o['slot_load']}/${o['slot_cap']}',
                  footer: AppButton(
                    text: 'Open',
                    testId: 'sp_offer_open_${o['id']}',
                    expands: true,
                    showArrow: true,
                    onPressed: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) =>
                            _BookingDetail(api: api, id: o['id'] as String),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _AddressesPage extends StatefulWidget {
  const _AddressesPage({required this.api});
  final ApiClient api;
  @override
  State<_AddressesPage> createState() => _AddressesPageState();
}

class _AddressesPageState extends State<_AddressesPage> {
  final _line = TextEditingController();
  final _pin = TextEditingController(text: '682001');

  @override
  Widget build(BuildContext context) {
    return WorkspacePage(
      title: 'Addresses',
      subtitle: 'Saved places for home visits.',
      testId: 'customer_addresses',
      child: Column(
        children: [
          AppCard(
            title: 'Add address',
            child: Column(
              children: [
                AppInputField(
                  label: 'Line 1',
                  testId: 'customer_address_line1',
                  controller: _line,
                  placeholder: 'House / street',
                ),
                const SizedBox(height: 12),
                AppInputField(
                  label: 'Pincode',
                  testId: 'customer_address_pincode',
                  controller: _pin,
                ),
                const SizedBox(height: 16),
                AppButton(
                  text: 'Save address',
                  testId: 'customer_address_save',
                  expands: true,
                  onPressed: () async {
                    await widget.api.post('/v1/addresses', {
                      'label': 'home',
                      'line1': _line.text,
                      'pincode': _pin.text,
                      'is_default': true,
                    });
                    setState(() {});
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          FetchBody(
            future: widget.api.get('/v1/addresses'),
            builder: (data) {
              final items = data as List<dynamic>;
              if (items.isEmpty) return const EmptyHint('No saved addresses.');
              return Column(
                children: [
                  for (final a in items) ...[
                    AppCard(
                      title: '${a['line1']}',
                      description: '${a['pincode']}',
                    ),
                    const SizedBox(height: 12),
                  ],
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class _RosterPage extends StatelessWidget {
  const _RosterPage({required this.api});
  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    return WorkspacePage(
      title: 'Roster',
      subtitle: 'Service partners on your team.',
      testId: 'partner_roster',
      child: FetchBody(
        future: api.get('/v1/sp/roster'),
        builder: (data) {
          final items = data as List<dynamic>;
          if (items.isEmpty) return const EmptyHint('No technicians yet.');
          return Column(
            children: [
              for (final s in items) ...[
                AppCard(
                  title: '${s['full_name']}',
                  trailing: StatusBadge('${s['kyc_status']}'),
                  footer: Wrap(
                    spacing: 8,
                    children: [
                      AppButton(
                        text: 'Approve',
                        testId: 'roster_approve_${s['id']}',
                        expands: false,
                        onPressed: () => api.post('/v1/sp/${s['id']}/kyc', {
                          'status': 'approved',
                        }),
                      ),
                      AppButton(
                        text: 'Reject',
                        testId: 'roster_reject_${s['id']}',
                        variant: AppButtonVariant.outline,
                        expands: false,
                        onPressed: () => api.post('/v1/sp/${s['id']}/kyc', {
                          'status': 'rejected',
                        }),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _SpProfilePage extends StatefulWidget {
  const _SpProfilePage({required this.api});
  final ApiClient api;
  @override
  State<_SpProfilePage> createState() => _SpProfilePageState();
}

class _SpProfilePageState extends State<_SpProfilePage> {
  String? _msg;

  @override
  Widget build(BuildContext context) {
    return WorkspacePage(
      title: 'Your profile',
      testId: 'sp_profile',
      child: FetchBody(
        future: widget.api.get('/v1/sp/profile'),
        builder: (data) {
          final p = data as Map<String, dynamic>;
          return AppCard(
            title: 'KYC',
            trailing: StatusBadge('${p['kyc_status']}'),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                InfoRow('Pincodes', '${p['pincodes']}'),
                if (_msg != null) ...[
                  const SizedBox(height: 12),
                  AppAlert(title: _msg!),
                ],
                const SizedBox(height: 16),
                AppButton(
                  text: 'Submit KYC (demo paths)',
                  testId: 'sp_kyc_submit',
                  expands: true,
                  onPressed: () async {
                    try {
                      await widget.api.put('/v1/sp/profile', {
                        'pincodes':
                            p['pincodes'] is List &&
                                (p['pincodes'] as List).isNotEmpty
                            ? p['pincodes']
                            : ['682001'],
                        'category_ids': p['category_ids'] ?? [],
                        'aadhaar_path': 'local://masked-aadhaar',
                        'police_path': 'local://police',
                      });
                      setState(() => _msg = 'submitted');
                    } catch (e) {
                      setState(() => _msg = e.toString());
                    }
                  },
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
