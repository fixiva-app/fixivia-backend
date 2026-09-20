import 'package:flutter/material.dart';

import '../../api/client.dart';
import '../../core/booking_rules.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/components/components.dart';
import '../../l10n/app_localizations.dart';

class BookingFlow extends StatefulWidget {
  const BookingFlow({required this.api, super.key});
  final ApiClient api;

  @override
  State<BookingFlow> createState() => _BookingFlowState();
}

class _BookingFlowState extends State<BookingFlow> {
  var _step = 0;
  List<dynamic> _cats = [];
  String? _categoryId;
  final _problems = <String>{};
  List<dynamic> _addresses = [];
  String? _addressId;
  DateTime _date = earliestServiceDate(DateTime.now());
  var _slot = 'morning';
  String? _error;

  List<dynamic> get _featuredCats =>
      _cats.where((c) => c['featured_rank'] != null).toList();
  List<dynamic> get _otherCats =>
      _cats.where((c) => c['featured_rank'] == null).toList();

  Map<String, dynamic>? get _cat {
    for (final c in _cats) {
      if (c['id'] == _categoryId) return c as Map<String, dynamic>;
    }
    return null;
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final cats = await widget.api.get('/v1/categories') as List<dynamic>;
    final addrs = await widget.api.get('/v1/addresses') as List<dynamic>;
    setState(() {
      _cats = cats;
      _addresses = addrs;
      if (addrs.isNotEmpty) _addressId = addrs.first['id'] as String;
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AppSubpageScaffold(
      title: l10n.bookAService,
      footer: Row(
        children: [
          if (_step > 0)
            AppButton(
              text: 'Back',
              testId: 'customer_booking_back',
              variant: AppButtonVariant.ghost,
              expands: false,
              onPressed: () => setState(() => _step -= 1),
            ),
          if (_step > 0) const SizedBox(width: 8),
          Expanded(
            child: AppButton(
              text: _step == 3 ? 'Confirm booking' : 'Next',
              testId: 'customer_booking_next',
              showArrow: _step < 3,
              onPressed: _next,
            ),
          ),
        ],
      ),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
        children: [
          _StepPills(step: _step),
          const SizedBox(height: 16),
          AppCard(child: _body()),
          if (_error != null) ...[
            const SizedBox(height: 12),
            AppAlert(title: _error!, destructive: true),
          ],
        ],
      ),
    );
  }

  Widget _body() {
    if (_step == 0) return _categoryStep();
    if (_step == 1) return _problemStep();
    if (_step == 2) return _reviewStep();
    return _whenStep();
  }

  Widget _categoryStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'What do you need?',
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
        ),
        const SizedBox(height: 6),
        const Text(
          'Pick a featured service or another category.',
          style: TextStyle(color: AppColors.muted),
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final c in _featuredCats)
              AppChoice(
                label: '${c['name_en']}',
                selected: _categoryId == c['id'],
                testId: 'customer_booking_category_${c['slug']}',
                onTap: () => setState(() => _categoryId = c['id'] as String),
              ),
          ],
        ),
        if (_otherCats.isNotEmpty) ...[
          const SizedBox(height: 16),
          AppSelect<String>(
            testId: 'customer_booking_category_other',
            label: 'Other categories',
            placeholder: 'Choose another service',
            initialValue: _otherCats.any((c) => c['id'] == _categoryId)
                ? _categoryId
                : null,
            items: [
              for (final c in _otherCats)
                AppSelectItem(
                  value: c['id'] as String,
                  label: '${c['name_en']}',
                ),
            ],
            selectedOptionBuilder: (context, value) {
              for (final c in _otherCats) {
                if (c['id'] == value) return Text('${c['name_en']}');
              }
              return Text(value);
            },
            onChanged: (v) => setState(() => _categoryId = v),
          ),
        ],
      ],
    );
  }

  Widget _problemStep() {
    final cat = _cat;
    if (cat == null) {
      return const Text('Pick a category first');
    }
    final problems = cat['problems'] as List<dynamic>;
    final featured = problems.where((p) => p['featured_rank'] != null);
    final other = problems.where((p) => p['featured_rank'] == null);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'What’s wrong?',
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final p in featured)
              AppChoice(
                label: '${p['text_en']}',
                selected: _problems.contains(p['id']),
                testId: 'customer_booking_problem_${p['id']}',
                onTap: () => setState(() {
                  final id = p['id'] as String;
                  if (_problems.contains(id)) {
                    _problems.remove(id);
                  } else {
                    _problems.add(id);
                  }
                }),
              ),
          ],
        ),
        if (other.isNotEmpty) ...[
          const SizedBox(height: 16),
          const Text('Other', style: TextStyle(color: AppColors.muted)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final p in other)
                AppChoice(
                  label: '${p['text_en']}',
                  selected: _problems.contains(p['id']),
                  testId: 'customer_booking_problem_other_${p['id']}',
                  onTap: () => setState(() {
                    final id = p['id'] as String;
                    if (_problems.contains(id)) {
                      _problems.remove(id);
                    } else {
                      _problems.add(id);
                    }
                  }),
                ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _reviewStep() {
    final cat = _cat;
    final names = <String>[];
    for (final p in (cat?['problems'] as List<dynamic>? ?? [])) {
      if (_problems.contains(p['id'])) names.add('${p['text_en']}');
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Review',
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
        ),
        const SizedBox(height: 12),
        InfoLine(label: 'Category', value: '${cat?['name_en'] ?? ''}'),
        InfoLine(label: 'Problems', value: names.join(', ')),
      ],
    );
  }

  Widget _whenStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'When should we visit?',
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
        ),
        const SizedBox(height: 16),
        if (_addresses.isNotEmpty)
          AppSelect<String>(
            testId: 'customer_booking_address',
            label: 'Address',
            initialValue: _addressId,
            items: [
              for (final a in _addresses)
                AppSelectItem(
                  value: a['id'] as String,
                  label: '${a['label']} ${a['pincode']}',
                ),
            ],
            selectedOptionBuilder: (context, value) {
              for (final a in _addresses) {
                if (a['id'] == value) {
                  return Text('${a['label']} ${a['pincode']}');
                }
              }
              return Text(value);
            },
            onChanged: (v) => setState(() => _addressId = v),
          ),
        const SizedBox(height: 16),
        Text(
          'Date: ${_date.toIso8601String().split('T').first}',
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        AppButton(
          text: 'Pick date',
          testId: 'customer_booking_date',
          variant: AppButtonVariant.outline,
          expands: false,
          onPressed: () async {
            final picked = await showDatePicker(
              context: context,
              firstDate: earliestServiceDate(DateTime.now()),
              lastDate: DateTime.now().add(const Duration(days: 90)),
              initialDate: _date,
            );
            if (picked != null) setState(() => _date = picked);
          },
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 8,
          children: [
            AppChoice(
              label: 'Morning 09–13',
              selected: _slot == 'morning',
              testId: 'customer_booking_slot_morning',
              onTap: () => setState(() => _slot = 'morning'),
            ),
            AppChoice(
              label: 'Evening 13–18',
              selected: _slot == 'evening',
              testId: 'customer_booking_slot_evening',
              onTap: () => setState(() => _slot = 'evening'),
            ),
          ],
        ),
      ],
    );
  }

  Future<void> _next() async {
    setState(() => _error = null);
    if (_step == 0 && _categoryId == null) {
      setState(() => _error = 'Pick a category');
      return;
    }
    if (_step == 1 && _problems.isEmpty) {
      setState(() => _error = 'Pick at least one problem');
      return;
    }
    if (_step < 3) {
      setState(() => _step += 1);
      return;
    }
    try {
      await widget.api.post('/v1/bookings', {
        'address_id': _addressId,
        'category_id': _categoryId,
        'issue_template_ids': _problems.toList(),
        'service_date': _date.toIso8601String().split('T').first,
        'slot': _slot,
      });
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      setState(() => _error = e.toString());
    }
  }
}

class _StepPills extends StatelessWidget {
  const _StepPills({required this.step});

  final int step;

  @override
  Widget build(BuildContext context) {
    const labels = ['Service', 'Problem', 'Review', 'Schedule'];
    return DecoratedBox(
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Padding(
        padding: const EdgeInsets.all(4),
        child: Row(
          children: [
            for (var i = 0; i < labels.length; i++)
              Expanded(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: i == step ? AppColors.primaryGradient : null,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Text(
                      labels[i],
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: i == step ? AppColors.white : AppColors.muted,
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class InfoLine extends StatelessWidget {
  const InfoLine({required this.label, required this.value, super.key});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(label, style: const TextStyle(color: AppColors.muted)),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}
