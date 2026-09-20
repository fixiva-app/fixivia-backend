import 'package:flutter/material.dart';

import '../../api/client.dart';
import '../../core/booking_rules.dart';
import '../../l10n/app_localizations.dart';
import '../../shared/widgets/fx_choice_button.dart';
import '../../shared/widgets/fx_primary_button.dart';
import '../../shared/widgets/fx_secondary_button.dart';

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
    return Scaffold(
      appBar: AppBar(title: Text(l10n.bookAService)),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Step ${_step + 1} of 4'),
            const SizedBox(height: 12),
            Expanded(child: _body()),
            if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
            Row(
              children: [
                if (_step > 0)
                  FxSecondaryButton(
                    label: 'Back',
                    testId: 'customer_booking_back',
                    onPressed: () => setState(() => _step -= 1),
                  ),
                const Spacer(),
                FxPrimaryButton(
                  label: _step == 3 ? 'Confirm booking' : 'Next',
                  testId: 'customer_booking_next',
                  onPressed: _next,
                ),
              ],
            ),
          ],
        ),
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
    return ListView(
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final c in _featuredCats)
              FxChoiceButton(
                label: '${c['name_en']}',
                selected: _categoryId == c['id'],
                testId: 'customer_booking_category_${c['slug']}',
                onTap: () => setState(() => _categoryId = c['id'] as String),
              ),
          ],
        ),
        const SizedBox(height: 16),
        const Text('Other'),
        DropdownButton<String>(
          key: const Key('customer_booking_category_other'),
          hint: const Text('Other categories'),
          value: _otherCats.any((c) => c['id'] == _categoryId) ? _categoryId : null,
          items: [
            for (final c in _otherCats)
              DropdownMenuItem(value: c['id'] as String, child: Text('${c['name_en']}')),
          ],
          onChanged: (v) => setState(() => _categoryId = v),
        ),
      ],
    );
  }

  Widget _problemStep() {
    final cat = _cat;
    if (cat == null) return const Text('Pick a category first');
    final problems = (cat['problems'] as List<dynamic>);
    final featured = problems.where((p) => p['featured_rank'] != null);
    final other = problems.where((p) => p['featured_rank'] == null);
    return ListView(
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final p in featured)
              FxChoiceButton(
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
        const SizedBox(height: 12),
        const Text('Other'),
        for (final p in other)
          CheckboxListTile(
            key: Key('customer_booking_problem_other_${p['id']}'),
            title: Text('${p['text_en']}'),
            value: _problems.contains(p['id']),
            onChanged: (_) => setState(() {
              final id = p['id'] as String;
              if (_problems.contains(id)) {
                _problems.remove(id);
              } else {
                _problems.add(id);
              }
            }),
          ),
      ],
    );
  }

  Widget _reviewStep() {
    final cat = _cat;
    final names = <String>[];
    for (final p in (cat?['problems'] as List<dynamic>? ?? [])) {
      if (_problems.contains(p['id'])) names.add('${p['text_en']}');
    }
    return ListView(
      children: [
        Text('Category: ${cat?['name_en'] ?? ''}'),
        const SizedBox(height: 8),
        Text('Problems: ${names.join(', ')}'),
      ],
    );
  }

  Widget _whenStep() {
    return ListView(
      children: [
        const Text('Address'),
        DropdownButton<String>(
          key: const Key('customer_booking_address'),
          value: _addressId,
          items: [
            for (final a in _addresses)
              DropdownMenuItem(
                value: a['id'] as String,
                child: Text('${a['label']} ${a['pincode']}'),
              ),
          ],
          onChanged: (v) => setState(() => _addressId = v),
        ),
        const SizedBox(height: 12),
        Text('Date: ${_date.toIso8601String().split('T').first}'),
        FxSecondaryButton(
          label: 'Pick date',
          testId: 'customer_booking_date',
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
        const SizedBox(height: 12),
        Row(
          children: [
            FxChoiceButton(
              label: 'Morning 09–13',
              selected: _slot == 'morning',
              testId: 'customer_booking_slot_morning',
              onTap: () => setState(() => _slot = 'morning'),
            ),
            const SizedBox(width: 8),
            FxChoiceButton(
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
