import 'package:flutter/material.dart';

import '../../api/client.dart';
import '../../core/session.dart';
import '../../l10n/app_localizations.dart';
import '../../shared/theme/fx_colors.dart';
import '../../shared/widgets/fx_logo.dart';
import '../../shared/widgets/fx_primary_button.dart';
import '../../shared/widgets/fx_secondary_button.dart';
import '../../shared/widgets/fx_text_field.dart';
import '../customer/booking_flow.dart';

class WorkspaceShell extends StatefulWidget {
  const WorkspaceShell({required this.api, required this.user, super.key});

  final ApiClient api;
  final SessionUser user;

  @override
  State<WorkspaceShell> createState() => _WorkspaceShellState();
}

class _WorkspaceShellState extends State<WorkspaceShell> {
  var _index = 0;

  List<_Tab> get _tabs {
    switch (widget.user.role) {
      case UserRole.customer:
        return [
          _Tab('Home', Icons.home, () => _CustomerHome(api: widget.api, user: widget.user)),
          _Tab('Bookings', Icons.event, () => _JsonPage(api: widget.api, path: '/v1/bookings', testId: 'customer_bookings')),
          _Tab('Addresses', Icons.place, () => _AddressesPage(api: widget.api)),
        ];
      case UserRole.servicePartner:
        return [
          _Tab('Inbox', Icons.inbox, () => _OffersPage(api: widget.api)),
          _Tab('Schedule', Icons.calendar_today, () => _JsonPage(api: widget.api, path: '/v1/sp/schedule', testId: 'sp_schedule')),
          _Tab('Earnings', Icons.payments, () => _JsonPage(api: widget.api, path: '/v1/sp/earnings', testId: 'sp_earnings')),
          _Tab('Profile', Icons.person, () => _SpProfilePage(api: widget.api)),
          _Tab('Reports', Icons.insights, () => _JsonPage(api: widget.api, path: '/v1/analytics', testId: 'sp_reports')),
        ];
      case UserRole.partnerOwner:
      case UserRole.partnerAdmin:
        return [
          _Tab('Open', Icons.pending, () => _JsonPage(api: widget.api, path: '/v1/bookings?status=open', testId: 'partner_open')),
          _Tab('Upcoming', Icons.upcoming, () => _JsonPage(api: widget.api, path: '/v1/bookings', testId: 'partner_upcoming')),
          _Tab('Roster', Icons.groups, () => _RosterPage(api: widget.api)),
          _Tab('Pricing', Icons.sell, () => _JsonPage(api: widget.api, path: '/v1/partner/pricing', testId: 'partner_pricing')),
          _Tab('Analytics', Icons.insights, () => _JsonPage(api: widget.api, path: '/v1/analytics', testId: 'partner_analytics')),
        ];
      case UserRole.masterAdmin:
        return [
          _Tab('Partners', Icons.apartment, () => _JsonPage(api: widget.api, path: '/v1/partners', testId: 'master_partners')),
          _Tab('Categories', Icons.category, () => _JsonPage(api: widget.api, path: '/v1/categories', testId: 'master_categories')),
          _Tab('Admins', Icons.person_add, () => _JsonPage(api: widget.api, path: '/v1/partner-admin-requests', testId: 'master_admin_reqs')),
          _Tab('Invoices', Icons.receipt, () => _JsonPage(api: widget.api, path: '/v1/invoices', testId: 'master_invoices')),
          _Tab('Analytics', Icons.insights, () => _JsonPage(api: widget.api, path: '/v1/analytics', testId: 'master_analytics')),
        ];
    }
  }

  @override
  Widget build(BuildContext context) {
    final tabs = _tabs;
    final wide = MediaQuery.sizeOf(context).width >= 800;
    final body = tabs[_index].builder();
    return Scaffold(
      appBar: AppBar(
        title: const FxLogo(height: 28),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Center(child: Text(widget.user.fullName)),
          ),
        ],
      ),
      body: wide
          ? Row(
              children: [
                NavigationRail(
                  selectedIndex: _index,
                  onDestinationSelected: (i) => setState(() => _index = i),
                  labelType: NavigationRailLabelType.all,
                  destinations: [
                    for (final t in tabs) NavigationRailDestination(icon: Icon(t.icon), label: Text(t.label)),
                  ],
                ),
                const VerticalDivider(width: 1),
                Expanded(child: body),
              ],
            )
          : body,
      bottomNavigationBar: wide
          ? null
          : NavigationBar(
              selectedIndex: _index,
              onDestinationSelected: (i) => setState(() => _index = i),
              destinations: [
                for (final t in tabs) NavigationDestination(icon: Icon(t.icon), label: t.label),
              ],
            ),
    );
  }
}

class _Tab {
  const _Tab(this.label, this.icon, this.builder);
  final String label;
  final IconData icon;
  final Widget Function() builder;
}

class _CustomerHome extends StatelessWidget {
  const _CustomerHome({required this.api, required this.user});
  final ApiClient api;
  final SessionUser user;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(AppLocalizations.of(context).customerHome, style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          Text(user.fullName),
          const SizedBox(height: 24),
          FxPrimaryButton(
            label: AppLocalizations.of(context).bookAService,
            testId: 'customer_home_book',
            onPressed: () {
              Navigator.push(context, MaterialPageRoute(builder: (_) => BookingFlow(api: api)));
            },
          ),
        ],
      ),
    );
  }
}

class _JsonPage extends StatelessWidget {
  const _JsonPage({required this.api, required this.path, required this.testId});
  final ApiClient api;
  final String path;
  final String testId;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder(
      future: api.get(path),
      builder: (context, snap) {
        if (snap.hasError) return Center(child: Text('${snap.error}'));
        if (!snap.hasData) return const Center(child: CircularProgressIndicator());
        final data = snap.data;
        final items = data is List ? data : [data];
        return ListView.builder(
          key: Key(testId),
          padding: const EdgeInsets.all(16),
          itemCount: items.length,
          itemBuilder: (context, i) {
            final item = items[i];
            return Card(
              child: ListTile(
                title: Text(item is Map ? '${item['status'] ?? item['trade_name'] ?? item['name_en'] ?? item['type'] ?? item}' : '$item'),
                subtitle: Text(item is Map ? '$item' : ''),
                onTap: item is Map && item['id'] != null
                    ? () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => _BookingDetail(api: api, id: item['id'] as String)),
                        )
                    : null,
              ),
            );
          },
        );
      },
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
    return Scaffold(
      appBar: AppBar(title: const Text('Booking')),
      body: FutureBuilder(
        future: widget.api.get('/v1/bookings/${widget.id}'),
        builder: (context, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final b = snap.data as Map<String, dynamic>;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text('${b['category_name']} · ${b['status']}', style: Theme.of(context).textTheme.titleLarge),
              Text('${b['service_date']} ${b['slot']} · ${b['pincode']}'),
              Text('Tech: ${b['technician_name'] ?? 'waiting'} ${b['technician_mobile_masked'] ?? ''}'),
              Text('OTP: ${b['start_work_otp_hint'] ?? '—'} (console in mock)'),
              const SizedBox(height: 12),
              FxTextField(label: 'Start-work OTP', testId: 'sp_start_otp', controller: _otp),
              if (_msg != null) Text(_msg!, style: const TextStyle(color: FxColors.deepOrange)),
              Wrap(
                spacing: 8,
                children: [
                  FxPrimaryButton(
                    label: 'Accept',
                    testId: 'sp_offer_accept',
                    onPressed: () => _act('/v1/bookings/${widget.id}/accept'),
                  ),
                  FxSecondaryButton(
                    label: 'Decline',
                    testId: 'sp_offer_decline',
                    onPressed: () => _act('/v1/bookings/${widget.id}/decline'),
                  ),
                  FxSecondaryButton(
                    label: 'Start work',
                    testId: 'sp_start_work',
                    onPressed: () => _act('/v1/bookings/${widget.id}/start', {'code': _otp.text}),
                  ),
                  FxSecondaryButton(
                    label: 'Complete',
                    testId: 'sp_complete',
                    onPressed: () => _act('/v1/bookings/${widget.id}/complete', {'payment_mode': 'cash'}),
                  ),
                  FxSecondaryButton(
                    label: 'Drop',
                    testId: 'sp_drop',
                    onPressed: () => _act('/v1/bookings/${widget.id}/drop'),
                  ),
                  FxSecondaryButton(
                    label: 'Cancel',
                    testId: 'customer_booking_cancel',
                    onPressed: () => _act('/v1/bookings/${widget.id}/cancel'),
                  ),
                ],
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
    return FutureBuilder(
      future: api.get('/v1/offers'),
      builder: (context, snap) {
        if (!snap.hasData) return const Center(child: CircularProgressIndicator());
        final items = snap.data as List<dynamic>;
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            for (final o in items)
              Card(
                child: ListTile(
                  title: Text('${o['category_name']} ${o['pincode']}'),
                  subtitle: Text('${o['service_date']} ${o['slot']} · load ${o['slot_load']}/${o['slot_cap']}'),
                  trailing: FxPrimaryButton(
                    label: 'Open',
                    testId: 'sp_offer_open_${o['id']}',
                    onPressed: () => Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => _BookingDetail(api: api, id: o['id'] as String)),
                    ),
                  ),
                ),
              ),
          ],
        );
      },
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
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        FxTextField(label: 'Line 1', testId: 'customer_address_line1', controller: _line),
        FxTextField(label: 'Pincode', testId: 'customer_address_pincode', controller: _pin),
        FxPrimaryButton(
          label: 'Save address',
          testId: 'customer_address_save',
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
        FutureBuilder(
          future: widget.api.get('/v1/addresses'),
          builder: (context, snap) {
            if (!snap.hasData) return const SizedBox.shrink();
            final items = snap.data as List<dynamic>;
            return Column(
              children: [
                for (final a in items) ListTile(title: Text('${a['line1']}'), subtitle: Text('${a['pincode']}')),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _RosterPage extends StatelessWidget {
  const _RosterPage({required this.api});
  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder(
      future: api.get('/v1/sp/roster'),
      builder: (context, snap) {
        if (!snap.hasData) return const Center(child: CircularProgressIndicator());
        final items = snap.data as List<dynamic>;
        return ListView(
          children: [
            for (final s in items)
              ListTile(
                title: Text('${s['full_name']}'),
                subtitle: Text('KYC ${s['kyc_status']}'),
                trailing: Wrap(
                  children: [
                    TextButton(
                      onPressed: () => api.post('/v1/sp/${s['id']}/kyc', {'status': 'approved'}),
                      child: const Text('Approve'),
                    ),
                    TextButton(
                      onPressed: () => api.post('/v1/sp/${s['id']}/kyc', {'status': 'rejected'}),
                      child: const Text('Reject'),
                    ),
                  ],
                ),
              ),
          ],
        );
      },
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
    return FutureBuilder(
      future: widget.api.get('/v1/sp/profile'),
      builder: (context, snap) {
        if (!snap.hasData) return const Center(child: CircularProgressIndicator());
        final p = snap.data as Map<String, dynamic>;
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text('KYC: ${p['kyc_status']}'),
            Text('Pincodes: ${p['pincodes']}'),
            if (_msg != null) Text(_msg!),
            FxPrimaryButton(
              label: 'Submit KYC (demo paths)',
              testId: 'sp_kyc_submit',
              onPressed: () async {
                try {
                  await widget.api.put('/v1/sp/profile', {
                    'pincodes': p['pincodes'] is List && (p['pincodes'] as List).isNotEmpty ? p['pincodes'] : ['682001'],
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
        );
      },
    );
  }
}
