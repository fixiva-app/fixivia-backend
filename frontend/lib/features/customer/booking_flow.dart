import 'package:flutter/material.dart';

import '../../api/client.dart';
import '../../core/booking_rules.dart';
import '../../core/theme/app_theme.dart';
import '../../core/theme/components/components.dart';
import '../../l10n/app_localizations.dart';

class BookingFlow extends StatefulWidget {
  const BookingFlow({required this.api, this.initialCategoryId, super.key});

  final ApiClient api;

  /// Preselects a category (used when jumping in from the home grid).
  final String? initialCategoryId;

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
  var _loaded = false;

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
    _categoryId = widget.initialCategoryId;
    _load();
  }

  Future<void> _load() async {
    try {
      final cats = await widget.api.get('/v1/categories') as List<dynamic>;
      final addrs = await widget.api.get('/v1/addresses') as List<dynamic>;
      if (!mounted) return;
      setState(() {
        _cats = cats;
        _addresses = addrs;
        if (addrs.isNotEmpty) _addressId = addrs.first['id'] as String;
        _loaded = true;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loaded = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AppSubpageScaffold(
      title: l10n.bookAService,
      subtitle: _stepSubtitle(),
      footer: Row(
        children: [
          if (_step > 0)
            AppButton.iconOnly(
              testId: 'customer_booking_back',
              icon: Icons.arrow_back_rounded,
              onPressed: () => setState(() {
                _error = null;
                _step -= 1;
              }),
            ),
          if (_step > 0) const SizedBox(width: 10),
          Expanded(
            child: AppButton(
              text: _step == 3 ? 'Confirm booking' : 'Next',
              testId: 'customer_booking_next',
              showArrow: _step < 3,
              size: AppButtonSize.lg,
              onPressed: _loaded ? _next : null,
            ),
          ),
        ],
      ),
      child: !_loaded
          ? const Padding(
              padding: EdgeInsets.fromLTRB(20, 20, 20, 24),
              child: LoadingSkeleton(rows: 4),
            )
          : ListView(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
              children: [
                Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 760),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _Stepper(step: _step),
                        const SizedBox(height: 18),
                        AnimatedSwitcher(
                          duration: const Duration(milliseconds: 220),
                          switchInCurve: Curves.easeOut,
                          child: KeyedSubtree(
                            key: ValueKey(_step),
                            child: _body(),
                          ),
                        ),
                        if (_error != null) ...[
                          const SizedBox(height: 12),
                          AppAlert(title: _error!, destructive: true),
                        ],
                      ],
                    ),
                  ),
                ),
              ],
            ),
    );
  }

  String _stepSubtitle() {
    return switch (_step) {
      0 => 'Step 1 of 4 · Choose a service',
      1 => 'Step 2 of 4 · Describe the problem',
      2 => 'Step 3 of 4 · Review your request',
      _ => 'Step 4 of 4 · Pick a visit slot',
    };
  }

  Widget _body() {
    if (_step == 0) return _categoryStep();
    if (_step == 1) return _problemStep();
    if (_step == 2) return _reviewStep();
    return _whenStep();
  }

  Widget _categoryStep() {
    final featured = _featuredCats;
    final other = _otherCats;
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'What do you need?',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 6),
          Text(
            'Pick a featured service or another category.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 16),
          LayoutBuilder(
            builder: (context, constraints) {
              final w = constraints.maxWidth;
              final cols = w > 640 ? 4 : w > 420 ? 3 : 2;
              return GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: cols,
                  mainAxisSpacing: 6,
                  crossAxisSpacing: 6,
                  childAspectRatio: 4.0,
                ),
                itemCount: featured.length,
                itemBuilder: (context, i) {
                  final c = featured[i] as Map<String, dynamic>;
                  final id = c['id'] as String;
                  final selected = _categoryId == id;
                  return _ServiceCard(
                    name: '${c['name_en']}',
                    slug: '${c['slug'] ?? ''}',
                    testId: 'customer_booking_category_${c['slug']}',
                    selected: selected,
                    onTap: () => setState(() => _categoryId = id),
                  );
                },
              );
            },
          ),
          if (other.isNotEmpty) ...[
            const SizedBox(height: 16),
            AppSelect<String>(
              testId: 'customer_booking_category_other',
              label: 'Other categories',
              placeholder: 'Choose another service',
              initialValue: other.any((c) => c['id'] == _categoryId)
                  ? _categoryId
                  : null,
              items: [
                for (final c in other)
                  AppSelectItem(
                    value: c['id'] as String,
                    label: '${c['name_en']}',
                  ),
              ],
              selectedOptionBuilder: (context, value) {
                for (final c in other) {
                  if (c['id'] == value) return Text('${c['name_en']}');
                }
                return Text(value);
              },
              onChanged: (v) => setState(() => _categoryId = v),
            ),
          ],
        ],
      ),
    );
  }

  Widget _problemStep() {
    final cat = _cat;
    if (cat == null) {
      return const AppCard(
        child: EmptyState(
          title: 'Pick a category first',
          icon: Icons.category_outlined,
        ),
      );
    }
    final problems = cat['problems'] as List<dynamic>;
    final featured = problems.where((p) => p['featured_rank'] != null);
    final other = problems.where((p) => p['featured_rank'] == null);
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              FxServiceTile(icon: categoryIcon('${cat['slug']}'), size: 44),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'What’s wrong?',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    Text(
                      '${cat['name_en']} · tap all that apply',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 5,
                ),
                decoration: BoxDecoration(
                  gradient: _problems.isEmpty
                      ? null
                      : AppColors.primaryGradient,
                  color: _problems.isEmpty
                      ? AppColors.lightGray
                      : null,
                  borderRadius: BorderRadius.circular(AppRadii.pill),
                ),
                child: Text(
                  '${_problems.length} picked',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: _problems.isEmpty
                        ? AppColors.muted
                        : AppColors.white,
                  ),
                ),
              ),
            ],
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
                  onTap: () => _toggleProblem(p['id'] as String),
                ),
            ],
          ),
          if (other.isNotEmpty) ...[
            const SizedBox(height: 18),
            Text('Other issues', style: Theme.of(context).textTheme.labelMedium),
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
                    onTap: () => _toggleProblem(p['id'] as String),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  void _toggleProblem(String id) {
    setState(() {
      if (_problems.contains(id)) {
        _problems.remove(id);
      } else {
        _problems.add(id);
      }
    });
  }

  Widget _reviewStep() {
    final cat = _cat;
    final names = <String>[];
    for (final p in (cat?['problems'] as List<dynamic>? ?? [])) {
      if (_problems.contains(p['id'])) names.add('${p['text_en']}');
    }
    return Column(
      children: [
        AppCard(
          gradient: AppColors.primaryGradientDiagonal,
          child: Row(
            children: [
              FxServiceTile(
                icon: categoryIcon('${cat?['slug']}'),
                size: 52,
                onBrand: true,
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'YOUR REQUEST',
                      style: TextStyle(
                        color: Color(0xE6FFFFFF),
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.1,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${cat?['name_en'] ?? '—'}',
                      style: const TextStyle(
                        color: AppColors.white,
                        fontSize: 21,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        AppCard(
          child: Column(
            children: [
              _ReviewRow(
                icon: Icons.build_outlined,
                label: 'Problems',
                value: names.isEmpty ? '—' : names.join(', '),
                editTestId: 'customer_booking_edit_problems',
                onEdit: () => setState(() => _step = 1),
              ),
              const Divider(height: 20),
              _ReviewRow(
                icon: Icons.place_outlined,
                label: 'Address',
                value: _addressLabel(),
                editTestId: 'customer_booking_edit_address',
                onEdit: () => setState(() => _step = 3),
              ),
              const Divider(height: 20),
              _ReviewRow(
                icon: Icons.schedule_rounded,
                label: 'Visit',
                value:
                    '${_date.toIso8601String().split('T').first} · ${_slot == 'morning' ? 'Morning 09–13' : 'Evening 13–18'}',
                editTestId: 'customer_booking_edit_schedule',
                onEdit: () => setState(() => _step = 3),
              ),
            ],
          ),
        ),
      ],
    );
  }

  String _addressLabel() {
    for (final a in _addresses) {
      if (a['id'] == _addressId) {
        return '${a['label'] ?? ''} ${a['pincode'] ?? ''}'.trim();
      }
    }
    return '—';
  }

  Widget _whenStep() {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'When should we visit?',
            style: Theme.of(context).textTheme.titleLarge,
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
          if (_addresses.isNotEmpty) const SizedBox(height: 18),
          Row(
            children: [
              Expanded(
                child: Text(
                  'Pick a day',
                  style: Theme.of(context).textTheme.labelMedium,
                ),
              ),
              AppButton(
                text: 'Calendar',
                testId: 'customer_booking_date',
                variant: AppButtonVariant.outline,
                size: AppButtonSize.sm,
                expands: false,
                leading: const Icon(Icons.calendar_month_rounded, size: 15),
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
            ],
          ),
          const SizedBox(height: 10),
          _DayStrip(
            selected: _date,
            onPick: (d) => setState(() => _date = d),
          ),
          const SizedBox(height: 18),
          Text('Pick a slot', style: Theme.of(context).textTheme.labelMedium),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: _SlotCard(
                  label: 'Morning',
                  time: '09:00 – 13:00',
                  icon: Icons.wb_sunny_rounded,
                  testId: 'customer_booking_slot_morning',
                  selected: _slot == 'morning',
                  onTap: () => setState(() => _slot = 'morning'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _SlotCard(
                  label: 'Evening',
                  time: '13:00 – 18:00',
                  icon: Icons.nights_stay_rounded,
                  testId: 'customer_booking_slot_evening',
                  selected: _slot == 'evening',
                  onTap: () => setState(() => _slot = 'evening'),
                ),
              ),
            ],
          ),
        ],
      ),
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

class _Stepper extends StatelessWidget {
  const _Stepper({required this.step});

  final int step;

  static const _labels = ['Service', 'Problem', 'Review', 'Schedule'];
  static const _icons = [
    Icons.grid_view_rounded,
    Icons.build_rounded,
    Icons.receipt_long_rounded,
    Icons.schedule_rounded,
  ];

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      child: Row(
        children: [
          for (var i = 0; i < _labels.length; i++) ...[
            if (i > 0)
              Expanded(
                child: Container(
                  height: 2,
                  margin: const EdgeInsets.symmetric(horizontal: 6),
                  decoration: BoxDecoration(
                    gradient: i <= step ? AppColors.primaryGradient : null,
                    color: i <= step ? null : AppColors.border,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
            _StepDot(
              index: i,
              current: step,
              label: _labels[i],
              icon: _icons[i],
            ),
          ],
        ],
      ),
    );
  }
}

class _StepDot extends StatelessWidget {
  const _StepDot({
    required this.index,
    required this.current,
    required this.label,
    required this.icon,
  });

  final int index;
  final int current;
  final String label;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final done = index < current;
    final active = index == current;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            gradient: (active || done) ? AppColors.primaryGradient : null,
            color: (active || done) ? null : AppColors.lightGray,
            shape: BoxShape.circle,
            boxShadow: active ? AppShadows.glowSoft : const [],
            border: (active || done)
                ? null
                : Border.all(color: AppColors.border),
          ),
          child: Icon(
            done ? Icons.check_rounded : icon,
            size: 18,
            color: (active || done) ? AppColors.white : AppColors.muted,
          ),
        ),
        const SizedBox(height: 5),
        Text(
          label,
          style: TextStyle(
            fontSize: 11,
            fontWeight: active ? FontWeight.w700 : FontWeight.w500,
            color: active ? AppColors.deepOrange : AppColors.muted,
          ),
        ),
      ],
    );
  }
}

class _ServiceCard extends StatelessWidget {
  const _ServiceCard({
    required this.name,
    required this.slug,
    required this.testId,
    required this.selected,
    required this.onTap,
  });

  final String name;
  final String slug;
  final String testId;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return AppTestId(
      testId: testId,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        child: GestureDetector(
          onTap: onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 160),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              gradient: selected ? AppColors.primaryGradientDiagonal : null,
              color: selected
                  ? null
                  : (dark ? AppColors.charcoalSoft : AppColors.peachSoft),
              borderRadius: BorderRadius.circular(AppRadii.md),
              border: Border.all(
                color: selected ? Colors.transparent : AppColors.peach,
                width: 1.2,
              ),
              boxShadow: selected ? AppShadows.glowSoft : const [],
            ),
            child: Row(
              children: [
                FxServiceTile(
                  icon: categoryIcon(slug),
                  size: 24,
                  selected: selected,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      height: 1.2,
                      color: selected
                          ? AppColors.white
                          : AppColors.inkOf(context),
                    ),
                  ),
                ),
                if (selected)
                  const Icon(
                    Icons.check_circle_rounded,
                    size: 13,
                    color: AppColors.white,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ReviewRow extends StatelessWidget {
  const _ReviewRow({
    required this.icon,
    required this.label,
    required this.value,
    required this.editTestId,
    required this.onEdit,
  });

  final IconData icon;
  final String label;
  final String value;
  final String editTestId;
  final VoidCallback onEdit;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        FxServiceTile(icon: icon, size: 40),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: Theme.of(context).textTheme.labelSmall),
              const SizedBox(height: 2),
              Text(
                value,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  height: 1.4,
                ),
              ),
            ],
          ),
        ),
        AppTestId(
          testId: editTestId,
          child: MouseRegion(
            cursor: SystemMouseCursors.click,
            child: GestureDetector(
              onTap: onEdit,
              child: const Padding(
                padding: EdgeInsets.all(4),
                child: Text(
                  'Edit',
                  style: TextStyle(
                    color: AppColors.deepOrange,
                    fontWeight: FontWeight.w700,
                    fontSize: 13,
                  ),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _DayStrip extends StatelessWidget {
  const _DayStrip({required this.selected, required this.onPick});

  final DateTime selected;
  final ValueChanged<DateTime> onPick;

  static const _wd = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  static const _mo = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];

  @override
  Widget build(BuildContext context) {
    final start = earliestServiceDate(DateTime.now());
    final days = [for (var i = 0; i < 14; i++) start.add(Duration(days: i))];
    final dark = Theme.of(context).brightness == Brightness.dark;
    return SizedBox(
      height: 72,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: days.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final d = days[i];
          final sel =
              d.year == selected.year &&
              d.month == selected.month &&
              d.day == selected.day;
          return AppTestId(
            testId: 'customer_booking_day_$i',
            child: MouseRegion(
              cursor: SystemMouseCursors.click,
              child: GestureDetector(
                onTap: () => onPick(d),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 160),
                  width: 56,
                  decoration: BoxDecoration(
                    gradient: sel ? AppColors.primaryGradient : null,
                    color: sel
                        ? null
                        : (dark
                              ? AppColors.charcoalSoft
                              : AppColors.surfaceOf(context)),
                    borderRadius: BorderRadius.circular(AppRadii.md),
                    border: sel
                        ? null
                        : Border.all(color: AppColors.lineOf(context)),
                    boxShadow: sel ? AppShadows.glowSoft : const [],
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        _wd[d.weekday - 1],
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: sel
                              ? AppColors.white.withValues(alpha: 0.85)
                              : AppColors.subOf(context),
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '${d.day}',
                        style: TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w800,
                          color: sel ? AppColors.white : AppColors.inkOf(context),
                        ),
                      ),
                      Text(
                        _mo[d.month - 1],
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: sel
                              ? AppColors.white.withValues(alpha: 0.85)
                              : AppColors.subOf(context),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _SlotCard extends StatelessWidget {
  const _SlotCard({
    required this.label,
    required this.time,
    required this.icon,
    required this.testId,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final String time;
  final IconData icon;
  final String testId;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return AppTestId(
      testId: testId,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        child: GestureDetector(
          onTap: onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 160),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              gradient: selected ? AppColors.primaryGradientDiagonal : null,
              color: selected
                  ? null
                  : (dark
                        ? AppColors.charcoalSoft
                        : AppColors.surfaceOf(context)),
              borderRadius: BorderRadius.circular(AppRadii.md),
              border: Border.all(
                color: selected ? Colors.transparent : AppColors.peach,
                width: 1.2,
              ),
              boxShadow: selected ? AppShadows.glowSoft : const [],
            ),
            child: Row(
              children: [
                Icon(
                  icon,
                  size: 18,
                  color: selected
                      ? AppColors.white
                      : AppColors.brightOrange,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        label,
                        style: TextStyle(
                          fontSize: 13.5,
                          fontWeight: FontWeight.w700,
                          color: selected
                              ? AppColors.white
                              : AppColors.inkOf(context),
                        ),
                      ),
                      Text(
                        time,
                        style: TextStyle(
                          fontSize: 11.5,
                          fontWeight: FontWeight.w500,
                          color: selected
                              ? AppColors.white.withValues(alpha: 0.85)
                              : AppColors.subOf(context),
                        ),
                      ),
                    ],
                  ),
                ),
                if (selected)
                  const Icon(
                    Icons.check_circle_rounded,
                    size: 16,
                    color: AppColors.white,
                  ),
              ],
            ),
          ),
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
            child: Text(
              label,
              style: TextStyle(color: AppColors.subOf(context)),
            ),
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
