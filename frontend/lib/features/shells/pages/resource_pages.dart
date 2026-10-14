import 'package:flutter/material.dart';

import '../../../api/client.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/theme/components/components.dart';
import 'workspace_page.dart';

/// Shared booking row: date badge, category, slot/pincode, quote, status.
class BookingRowCard extends StatelessWidget {
  const BookingRowCard({
    required this.booking,
    this.testId,
    this.onTap,
    super.key,
  });

  final Map<String, dynamic> booking;
  final String? testId;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final b = booking;
    return AppCard(
      testId: testId,
      onTap: onTap,
      padding: const EdgeInsets.all(14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _DateBadge(raw: field(b, 'service_date', '')),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Text(
                        field(b, 'category_name', 'Booking'),
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    StatusBadge(field(b, 'status')),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  '${pretty(field(b, 'slot'))} · ${field(b, 'pincode')}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Text(
                      money(b['quoted_amount']),
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                        color: AppColors.deepOrange,
                      ),
                    ),
                    if (b['technician_name'] != null) ...[
                      const SizedBox(width: 8),
                      const Icon(
                        Icons.person_rounded,
                        size: 13,
                        color: AppColors.muted,
                      ),
                      const SizedBox(width: 3),
                      Expanded(
                        child: Text(
                          field(b, 'technician_name'),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ),
                    ],
                    if (onTap != null)
                      const Icon(
                        Icons.arrow_forward_ios_rounded,
                        size: 14,
                        color: AppColors.brightOrange,
                      ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _DateBadge extends StatelessWidget {
  const _DateBadge({required this.raw});

  final String raw;

  static const _mo = [
    'JAN',
    'FEB',
    'MAR',
    'APR',
    'MAY',
    'JUN',
    'JUL',
    'AUG',
    'SEP',
    'OCT',
    'NOV',
    'DEC',
  ];

  @override
  Widget build(BuildContext context) {
    var day = '—';
    var mon = '';
    try {
      final d = DateTime.parse(raw);
      day = '${d.day}';
      mon = _mo[d.month - 1];
    } catch (_) {}
    return Container(
      width: 56,
      padding: const EdgeInsets.symmetric(vertical: 9),
      decoration: BoxDecoration(
        gradient: AppColors.primaryGradientDiagonal,
        borderRadius: BorderRadius.circular(AppRadii.md),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            day,
            style: const TextStyle(
              color: AppColors.white,
              fontSize: 19,
              fontWeight: FontWeight.w800,
              height: 1,
            ),
          ),
          if (mon.isNotEmpty) ...[
            const SizedBox(height: 3),
            Text(
              mon,
              style: const TextStyle(
                color: Color(0xE6FFFFFF),
                fontSize: 10,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.6,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

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
        onRetry: _reload,
        builder: (data) {
          final items = asMapList(data);
          if (items.isEmpty) {
            return const AppCard(
              child: EmptyState(
                title: 'No partners yet',
                hint: 'Invited operation partners will appear here.',
                icon: Icons.apartment_outlined,
              ),
            );
          }
          return Column(
            children: [
              for (final p in items) ...[
                AppCard(
                  leading: const FxServiceTile(
                    icon: Icons.apartment_rounded,
                  ),
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
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 8,
                          children: [
                            AppButton(
                              text: 'Approve',
                              testId: 'master_partner_approve_${p['id']}',
                              size: AppButtonSize.sm,
                              expands: false,
                              leading: const Icon(
                                Icons.check_rounded,
                                size: 15,
                              ),
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
                            AppButton(
                              text: 'Reject',
                              testId: 'master_partner_reject_${p['id']}',
                              variant: AppButtonVariant.outline,
                              size: AppButtonSize.sm,
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
          if (items.isEmpty) {
            return const AppCard(
              child: EmptyState(
                title: 'No categories yet',
                icon: Icons.category_outlined,
              ),
            );
          }
          return Column(
            children: [
              for (final c in items) ...[
                AppCard(
                  leading: FxServiceTile(
                    icon: categoryIcon(field(c, 'slug', '')),
                  ),
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
        onRetry: _reload,
        builder: (data) {
          final items = asMapList(data);
          if (items.isEmpty) {
            return const AppCard(
              child: EmptyState(
                title: 'No partner-admin requests',
                icon: Icons.person_add_outlined,
              ),
            );
          }
          return Column(
            children: [
              for (final r in items) ...[
                AppCard(
                  leading: FxAvatar(name: field(r, 'full_name', '?')),
                  title: field(r, 'full_name'),
                  description: field(r, 'email', field(r, 'mobile')),
                  trailing: StatusBadge(field(r, 'status')),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      InfoRow('Mobile', field(r, 'mobile')),
                      if (field(r, 'status') == 'submitted') ...[
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 8,
                          children: [
                            AppButton(
                              text: 'Approve',
                              testId: 'master_admin_approve_${r['id']}',
                              size: AppButtonSize.sm,
                              expands: false,
                              leading: const Icon(
                                Icons.check_rounded,
                                size: 15,
                              ),
                              onPressed: () async {
                                await widget.api.post(
                                  '/v1/partner-admin-requests/${r['id']}/review',
                                  {'status': 'approved'},
                                );
                                _reload();
                              },
                            ),
                            AppButton(
                              text: 'Reject',
                              testId: 'master_admin_reject_${r['id']}',
                              variant: AppButtonVariant.outline,
                              size: AppButtonSize.sm,
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
          if (items.isEmpty) {
            return const AppCard(
              child: EmptyState(
                title: 'No invoices yet',
                icon: Icons.receipt_long_outlined,
              ),
            );
          }
          return Column(
            children: [
              for (final inv in items) ...[
                AppCard(
                  leading: const FxServiceTile(
                    icon: Icons.receipt_long_rounded,
                  ),
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
        skeletonRows: 4,
        builder: (data) {
          final a = asMap(data);
          final saas = asMap(a['saas_license_fees']);
          final partners = asMapList(a['by_partner']);
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              LayoutBuilder(
                builder: (context, constraints) {
                  final wide = constraints.maxWidth > 640;
                  final w = wide
                      ? (constraints.maxWidth - 24) / 4
                      : (constraints.maxWidth - 12) / 2;
                  Widget cell(Widget c) =>
                      SizedBox(width: w, child: c);
                  return Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: [
                      cell(_metric(
                        'Created',
                        field(a, 'created', '0'),
                        Icons.add_circle_outline_rounded,
                        AppColors.info,
                      )),
                      cell(_metric(
                        'Open',
                        field(a, 'still_open', '0'),
                        Icons.pending_actions_rounded,
                        AppColors.deepOrange,
                      )),
                      cell(_metric(
                        'Accepted',
                        field(a, 'accepted', '0'),
                        Icons.task_alt_rounded,
                        AppColors.warning,
                      )),
                      cell(_metric(
                        'Completed',
                        field(a, 'completed', '0'),
                        Icons.verified_rounded,
                        AppColors.successDeep,
                      )),
                      cell(_metric(
                        'Cancelled',
                        field(a, 'cancelled', '0'),
                        Icons.cancel_outlined,
                        AppColors.danger,
                      )),
                      cell(_metric(
                        'Job GMV',
                        money(a['gmv_completed']),
                        Icons.currency_rupee_rounded,
                        AppColors.ember,
                      )),
                      cell(_metric(
                        'Commission',
                        money(a['commission_completed']),
                        Icons.percent_rounded,
                        AppColors.brightOrange,
                      )),
                      cell(_metric(
                        'Median accept',
                        a['median_accept_minutes'] == null
                            ? '—'
                            : '${a['median_accept_minutes']} min',
                        Icons.timer_outlined,
                        AppColors.charcoal,
                      )),
                    ],
                  );
                },
              ),
              const SizedBox(height: 16),
              AppCard(
                leading: const FxServiceTile(
                  icon: Icons.account_balance_rounded,
                ),
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
                  description: 'Completion rate per operation partner.',
                  child: Column(
                    children: [
                      for (var i = 0; i < partners.length; i++) ...[
                        if (i > 0) const SizedBox(height: 14),
                        _PartnerBar(partner: partners[i]),
                      ],
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

  Widget _metric(String label, String value, IconData icon, Color tint) {
    return MetricCard(label: label, value: value, icon: icon, tint: tint);
  }
}

class _PartnerBar extends StatelessWidget {
  const _PartnerBar({required this.partner});

  final Map<String, dynamic> partner;

  @override
  Widget build(BuildContext context) {
    final created = int.tryParse(field(partner, 'created', '0')) ?? 0;
    final completed = int.tryParse(field(partner, 'completed', '0')) ?? 0;
    final ratio = created <= 0 ? 0.0 : (completed / created).clamp(0.0, 1.0);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                field(partner, 'trade_name'),
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            Text(
              '$completed / $created done',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
        const SizedBox(height: 7),
        ClipRRect(
          borderRadius: BorderRadius.circular(6),
          child: LinearProgressIndicator(
            value: ratio,
            minHeight: 9,
            backgroundColor: AppColors.peachSoft,
            valueColor: const AlwaysStoppedAnimation<Color>(
              AppColors.deepOrange,
            ),
          ),
        ),
      ],
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
          if (items.isEmpty) {
            return const AppCard(
              child: EmptyState(
                title: 'No bookings yet',
                icon: Icons.event_available_outlined,
              ),
            );
          }
          return Column(
            children: [
              for (final b in items) ...[
                BookingRowCard(
                  booking: b,
                  testId: '${testId}_item_${b['id']}',
                  onTap: b['id'] != null && onOpen != null
                      ? () => onOpen!(b['id'] as String)
                      : null,
                ),
                const SizedBox(height: 10),
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
              field(c, 'id'): c,
          };
          if (prices.isEmpty) {
            return const AppCard(
              child: EmptyState(
                title: 'No pricing rows yet',
                icon: Icons.sell_outlined,
              ),
            );
          }
          return Column(
            children: [
              for (final p in prices) ...[
                _PricingCard(price: p, category: cats[field(p, 'category_id')]),
                const SizedBox(height: 12),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _PricingCard extends StatelessWidget {
  const _PricingCard({required this.price, this.category});

  final Map<String, dynamic> price;
  final Map<String, dynamic>? category;

  @override
  Widget build(BuildContext context) {
    final name = category == null
        ? field(price, 'category_id')
        : field(category!, 'name_en');
    return AppCard(
      leading: FxServiceTile(
        icon: categoryIcon(category == null ? null : field(category!, 'slug')),
      ),
      title: name,
      description: 'Per visit',
      trailing: StatusBadge(price['enabled'] == false ? 'disabled' : 'enabled'),
      child: Text(
        money(price['visit_charge']),
        style: Theme.of(
          context,
        ).textTheme.headlineSmall?.copyWith(color: AppColors.deepOrange),
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
      subtitle: 'Route order per session.',
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
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 10,
                ),
                decoration: BoxDecoration(
                  color: AppColors.surfaceOf(context),
                  borderRadius: BorderRadius.circular(AppRadii.pill),
                  border: Border.all(color: AppColors.lineOf(context)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(
                      Icons.calendar_month_rounded,
                      size: 17,
                      color: AppColors.brightOrange,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Date ${field(s, 'date')}',
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 13.5,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              _slot(
                context,
                'Morning',
                '09:00 – 13:00',
                Icons.wb_sunny_rounded,
                morning,
              ),
              const SizedBox(height: 12),
              _slot(
                context,
                'Evening',
                '13:00 – 18:00',
                Icons.nights_stay_rounded,
                evening,
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _slot(
    BuildContext context,
    String label,
    String time,
    IconData icon,
    List<Map<String, dynamic>> jobs,
  ) {
    return AppCard(
      leading: FxServiceTile(icon: icon),
      title: label,
      description: jobs.isEmpty ? 'No jobs · $time' : '${jobs.length} job(s) · $time',
      child: jobs.isEmpty
          ? const Text(
              'Nothing scheduled — enjoy the breather.',
              style: TextStyle(color: AppColors.muted, fontSize: 13.5),
            )
          : Column(
              children: [
                for (var i = 0; i < jobs.length; i++) ...[
                  if (i > 0) const Divider(height: 18),
                  _JobStop(index: i, job: jobs[i]),
                ],
              ],
            ),
    );
  }
}

class _JobStop extends StatelessWidget {
  const _JobStop({required this.index, required this.job});

  final int index;
  final Map<String, dynamic> job;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 28,
          height: 28,
          decoration: const BoxDecoration(
            gradient: AppColors.primaryGradient,
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: Text(
            '${index + 1}',
            style: const TextStyle(
              color: AppColors.white,
              fontWeight: FontWeight.w800,
              fontSize: 13,
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                field(job, 'category_name', field(job, 'pincode')),
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
              Text(
                field(job, 'pincode'),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
        StatusBadge(field(job, 'status')),
      ],
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
      subtitle: 'Partner-defined payouts for completed jobs.',
      testId: 'sp_earnings',
      child: FetchBody(
        future: api.get('/v1/sp/earnings'),
        skeletonRows: 2,
        builder: (data) {
          final e = asMap(data);
          return LayoutBuilder(
            builder: (context, constraints) {
              final wide = constraints.maxWidth > 560;
              final w = wide
                  ? (constraints.maxWidth - 24) / 3
                  : (constraints.maxWidth - 12) / 2;
              return Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  SizedBox(
                    width: w,
                    child: MetricCard(
                      label: 'Pending',
                      value: money(e['pending']),
                      icon: Icons.hourglass_top_rounded,
                      tint: AppColors.warning,
                    ),
                  ),
                  SizedBox(
                    width: w,
                    child: MetricCard(
                      label: 'Paid',
                      value: money(e['paid']),
                      icon: Icons.verified_rounded,
                      tint: AppColors.successDeep,
                    ),
                  ),
                  SizedBox(
                    width: w,
                    child: MetricCard(
                      label: 'Jobs',
                      value: field(e, 'jobs', '0'),
                      icon: Icons.work_rounded,
                      tint: AppColors.deepOrange,
                    ),
                  ),
                ],
              );
            },
          );
        },
      ),
    );
  }
}
