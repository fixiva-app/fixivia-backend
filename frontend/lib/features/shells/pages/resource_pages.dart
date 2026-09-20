import 'package:flutter/material.dart';

import '../../../api/client.dart';
import '../../../core/theme/components/components.dart';
import 'workspace_page.dart';

class PartnersPage extends StatefulWidget {
  const PartnersPage({required this.api, super.key});

  final ApiClient api;

  @override
  State<PartnersPage> createState() => _PartnersPageState();
}

class _PartnersPageState extends State<PartnersPage> {
  late Future<dynamic> _future = widget.api.get('/v1/partners');

  void _reload() => setState(() => _future = widget.api.get('/v1/partners'));

  @override
  Widget build(BuildContext context) {
    return WorkspacePage(
      title: 'Operation partners',
      subtitle: 'One approved partner per pincode territory.',
      testId: 'master_partners',
      child: FetchBody(
        future: _future,
        builder: (data) {
          final items = asMapList(data);
          if (items.isEmpty) return const EmptyHint('No partners yet.');
          return Column(
            children: [
              for (final p in items) ...[
                AppCard(
                  title: field(p, 'trade_name'),
                  description: field(p, 'legal_name', field(p, 'org_type')),
                  trailing: StatusBadge(field(p, 'status')),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      InfoRow('Office pin', field(p, 'office_pincode')),
                      InfoRow('Email', field(p, 'personal_email')),
                      InfoRow('License fee', money(p['license_fee_amount'])),
                      InfoRow(
                        'Commission',
                        '${field(p, 'commission_percent')}%',
                      ),
                      if (p['pincodes'] is List &&
                          (p['pincodes'] as List).isNotEmpty)
                        InfoRow('Pincodes', (p['pincodes'] as List).join(', ')),
                      if (field(p, 'status') != 'approved') ...[
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 8,
                          children: [
                            AppButton(
                              text: 'Approve',
                              testId: 'master_partner_approve_${p['id']}',
                              expands: false,
                              onPressed: () async {
                                await widget.api.post(
                                  '/v1/partners/${p['id']}/review',
                                  {
                                    'status': 'approved',
                                    'pincodes': [
                                      if (p['office_pincode'] != null)
                                        p['office_pincode'],
                                    ],
                                  },
                                );
                                _reload();
                              },
                            ),
                            const SizedBox(width: 8),
                            AppButton(
                              text: 'Reject',
                              testId: 'master_partner_reject_${p['id']}',
                              variant: AppButtonVariant.outline,
                              expands: false,
                              onPressed: () async {
                                await widget.api.post(
                                  '/v1/partners/${p['id']}/review',
                                  {'status': 'rejected'},
                                );
                                _reload();
                              },
                            ),
                          ],
                        ),
                      ],
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

class CategoriesPage extends StatelessWidget {
  const CategoriesPage({required this.api, super.key});

  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    return WorkspacePage(
      title: 'Service categories',
      subtitle: 'Catalog shown to customers when they book.',
      testId: 'master_categories',
      child: FetchBody(
        future: api.get('/v1/categories'),
        builder: (data) {
          final items = asMapList(data);
          if (items.isEmpty) return const EmptyHint('No categories yet.');
          return Column(
            children: [
              for (final c in items) ...[
                AppCard(
                  title: field(c, 'name_en'),
                  description: field(c, 'name_ml', field(c, 'description_en')),
                  trailing: c['featured_rank'] != null
                      ? StatusBadge('featured #${c['featured_rank']}')
                      : StatusBadge(
                          c['is_active'] == false ? 'inactive' : 'active',
                        ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      InfoRow('Slug', field(c, 'slug')),
                      InfoRow(
                        'Visit time',
                        '${field(c, 'estimated_minutes', '60')} min',
                      ),
                      if (c['problems'] is List)
                        InfoRow(
                          'Problems',
                          '${(c['problems'] as List).length} templates',
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

class AdminRequestsPage extends StatefulWidget {
  const AdminRequestsPage({required this.api, super.key});

  final ApiClient api;

  @override
  State<AdminRequestsPage> createState() => _AdminRequestsPageState();
}

class _AdminRequestsPageState extends State<AdminRequestsPage> {
  late Future<dynamic> _future = widget.api.get('/v1/partner-admin-requests');

  void _reload() =>
      setState(() => _future = widget.api.get('/v1/partner-admin-requests'));

  @override
  Widget build(BuildContext context) {
    return WorkspacePage(
      title: 'Partner admin requests',
      subtitle: 'Owners request extra admins; you approve the account.',
      testId: 'master_admin_reqs',
      child: FetchBody(
        future: _future,
        builder: (data) {
          final items = asMapList(data);
          if (items.isEmpty) {
            return const EmptyHint('No partner-admin requests.');
          }
          return Column(
            children: [
              for (final r in items) ...[
                AppCard(
                  title: field(r, 'full_name'),
                  description: field(r, 'email', field(r, 'mobile')),
                  trailing: StatusBadge(field(r, 'status')),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      InfoRow('Mobile', field(r, 'mobile')),
                      if (field(r, 'status') == 'submitted') ...[
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            AppButton(
                              text: 'Approve',
                              testId: 'master_admin_approve_${r['id']}',
                              expands: false,
                              onPressed: () async {
                                await widget.api.post(
                                  '/v1/partner-admin-requests/${r['id']}/review',
                                  {'status': 'approved'},
                                );
                                _reload();
                              },
                            ),
                            const SizedBox(width: 8),
                            AppButton(
                              text: 'Reject',
                              testId: 'master_admin_reject_${r['id']}',
                              variant: AppButtonVariant.outline,
                              expands: false,
                              onPressed: () async {
                                await widget.api.post(
                                  '/v1/partner-admin-requests/${r['id']}/review',
                                  {'status': 'rejected'},
                                );
                                _reload();
                              },
                            ),
                          ],
                        ),
                      ],
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

class InvoicesPage extends StatelessWidget {
  const InvoicesPage({required this.api, super.key});

  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    return WorkspacePage(
      title: 'SaaS invoices',
      subtitle: 'License fees — not job GMV.',
      testId: 'master_invoices',
      child: FetchBody(
        future: api.get('/v1/invoices'),
        builder: (data) {
          final items = asMapList(data);
          if (items.isEmpty) return const EmptyHint('No invoices yet.');
          return Column(
            children: [
              for (final inv in items) ...[
                AppCard(
                  title: money(inv['amount']),
                  description:
                      '${field(inv, 'period_start')} → ${field(inv, 'period_end')}',
                  trailing: StatusBadge(field(inv, 'status')),
                  child: InfoRow('Partner', field(inv, 'partner_id')),
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

class AnalyticsPage extends StatelessWidget {
  const AnalyticsPage({required this.api, required this.testId, super.key});

  final ApiClient api;
  final String testId;

  @override
  Widget build(BuildContext context) {
    return WorkspacePage(
      title: 'Analytics',
      subtitle: 'Last 30 days. Job GMV is separate from SaaS license fees.',
      testId: testId,
      child: FetchBody(
        future: api.get('/v1/analytics'),
        builder: (data) {
          final a = asMap(data);
          final saas = asMap(a['saas_license_fees']);
          final partners = asMapList(a['by_partner']);
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  _metric('Created', field(a, 'created', '0')),
                  _metric('Open', field(a, 'still_open', '0')),
                  _metric('Accepted', field(a, 'accepted', '0')),
                  _metric('Completed', field(a, 'completed', '0')),
                  _metric('Cancelled', field(a, 'cancelled', '0')),
                  _metric('Job GMV', money(a['gmv_completed'])),
                  _metric('Commission', money(a['commission_completed'])),
                  _metric(
                    'Median accept',
                    a['median_accept_minutes'] == null
                        ? '—'
                        : '${a['median_accept_minutes']} min',
                  ),
                ],
              ),
              const SizedBox(height: 16),
              AppCard(
                title: 'SaaS license fees',
                description: field(saas, 'note', field(a, 'gmv_note')),
                child: Column(
                  children: [
                    InfoRow('Invoiced', money(saas['invoiced'])),
                    InfoRow('Collected', money(saas['collected'])),
                    InfoRow('Overdue', money(saas['overdue'])),
                  ],
                ),
              ),
              if (partners.isNotEmpty) ...[
                const SizedBox(height: 16),
                AppCard(
                  title: 'By partner',
                  child: Column(
                    children: [
                      for (final p in partners)
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text(field(p, 'trade_name')),
                          subtitle: Text(
                            '${field(p, 'created')} created · ${field(p, 'completed')} completed',
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ],
          );
        },
      ),
    );
  }

  Widget _metric(String label, String value) {
    return SizedBox(
      width: 200,
      child: MetricCard(label: label, value: value),
    );
  }
}

class BookingsListPage extends StatelessWidget {
  const BookingsListPage({
    required this.api,
    required this.testId,
    required this.title,
    this.path = '/v1/bookings',
    this.onOpen,
    super.key,
  });

  final ApiClient api;
  final String testId;
  final String title;
  final String path;
  final void Function(String id)? onOpen;

  @override
  Widget build(BuildContext context) {
    return WorkspacePage(
      title: title,
      testId: testId,
      child: FetchBody(
        future: api.get(path),
        builder: (data) {
          final items = asMapList(data);
          if (items.isEmpty) return const EmptyHint('No bookings yet.');
          return Column(
            children: [
              for (final b in items) ...[
                AppCard(
                  title: field(b, 'category_name', 'Booking'),
                  description:
                      '${field(b, 'service_date')} · ${pretty(field(b, 'slot'))} · ${field(b, 'pincode')}',
                  trailing: StatusBadge(field(b, 'status')),
                  onTap: b['id'] != null && onOpen != null
                      ? () => onOpen!(b['id'] as String)
                      : null,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      InfoRow('Quote', money(b['quoted_amount'])),
                      if (b['technician_name'] != null)
                        InfoRow('Technician', field(b, 'technician_name')),
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

class PricingPage extends StatelessWidget {
  const PricingPage({required this.api, super.key});

  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    return WorkspacePage(
      title: 'Visit pricing',
      subtitle: 'Charges you set per service category.',
      testId: 'partner_pricing',
      child: FetchBody(
        future: Future.wait([
          api.get('/v1/partner/pricing'),
          api.get('/v1/categories'),
        ]),
        builder: (data) {
          final pair = data as List<dynamic>;
          final prices = asMapList(pair[0]);
          final cats = {
            for (final c in asMapList(pair[1]))
              field(c, 'id'): field(c, 'name_en'),
          };
          if (prices.isEmpty) return const EmptyHint('No pricing rows yet.');
          return Column(
            children: [
              for (final p in prices) ...[
                AppCard(
                  title:
                      cats[field(p, 'category_id')] ?? field(p, 'category_id'),
                  trailing: StatusBadge(
                    p['enabled'] == false ? 'disabled' : 'enabled',
                  ),
                  child: InfoRow('Visit charge', money(p['visit_charge'])),
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

class SchedulePage extends StatelessWidget {
  const SchedulePage({required this.api, super.key});

  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    return WorkspacePage(
      title: 'Tomorrow’s schedule',
      testId: 'sp_schedule',
      child: FetchBody(
        future: api.get('/v1/sp/schedule'),
        builder: (data) {
          final s = asMap(data);
          final morning = asMapList(s['morning']);
          final evening = asMapList(s['evening']);
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Date ${field(s, 'date')}',
                style: const TextStyle(color: Color(0xFF737373)),
              ),
              const SizedBox(height: 16),
              _slot('Morning', morning),
              const SizedBox(height: 12),
              _slot('Evening', evening),
            ],
          );
        },
      ),
    );
  }

  Widget _slot(String label, List<Map<String, dynamic>> jobs) {
    return AppCard(
      title: label,
      description: jobs.isEmpty ? 'No jobs' : '${jobs.length} job(s)',
      child: Column(
        children: [
          for (final j in jobs)
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(field(j, 'pincode')),
              trailing: StatusBadge(field(j, 'status')),
            ),
        ],
      ),
    );
  }
}

class EarningsPage extends StatelessWidget {
  const EarningsPage({required this.api, super.key});

  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    return WorkspacePage(
      title: 'Earnings',
      testId: 'sp_earnings',
      child: FetchBody(
        future: api.get('/v1/sp/earnings'),
        builder: (data) {
          final e = asMap(data);
          return Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              SizedBox(
                width: 200,
                child: MetricCard(label: 'Pending', value: money(e['pending'])),
              ),
              SizedBox(
                width: 200,
                child: MetricCard(label: 'Paid', value: money(e['paid'])),
              ),
              SizedBox(
                width: 200,
                child: MetricCard(label: 'Jobs', value: field(e, 'jobs', '0')),
              ),
            ],
          );
        },
      ),
    );
  }
}
