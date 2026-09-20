import 'package:flutter/material.dart';

import '../app_theme.dart';
import 'app_button.dart';
import 'app_test_id.dart';

class AppNavDest {
  const AppNavDest({required this.label, required this.icon, this.testId});

  final String label;
  final IconData icon;
  final String? testId;
}

/// Logged-in chrome: white header, orange selected nav, gray canvas.
class AppWorkspaceFrame extends StatelessWidget {
  const AppWorkspaceFrame({
    required this.destinations,
    required this.selectedIndex,
    required this.onSelect,
    required this.body,
    required this.account,
    required this.brand,
    super.key,
  });

  final List<AppNavDest> destinations;
  final int selectedIndex;
  final ValueChanged<int> onSelect;
  final Widget body;
  final Widget account;
  final Widget brand;

  @override
  Widget build(BuildContext context) {
    final compact = appIsCompact(context);
    return Scaffold(
      backgroundColor: AppColors.lightGray,
      body: Column(
        children: [
          _Header(account: account, brand: brand),
          Expanded(
            child: compact
                ? body
                : Row(
                    children: [
                      _SideNav(
                        destinations: destinations,
                        selectedIndex: selectedIndex,
                        onSelect: onSelect,
                      ),
                      Expanded(child: body),
                    ],
                  ),
          ),
          if (compact)
            _BottomNav(
              destinations: destinations,
              selectedIndex: selectedIndex,
              onSelect: onSelect,
            ),
        ],
      ),
    );
  }
}

class AppSubpageScaffold extends StatelessWidget {
  const AppSubpageScaffold({
    required this.title,
    required this.child,
    this.footer,
    super.key,
  });

  final String title;
  final Widget child;
  final Widget? footer;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.lightGray,
      body: Column(
        children: [
          Material(
            color: AppColors.white,
            child: SafeArea(
              bottom: false,
              child: SizedBox(
                height: 64,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: Row(
                    children: [
                      AppButton(
                        text: 'Back',
                        testId: 'app_subpage_back',
                        variant: AppButtonVariant.ghost,
                        expands: false,
                        onPressed: () => Navigator.maybePop(context),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          title,
                          style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 16,
                            color: AppColors.charcoal,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          const Divider(height: 1, color: AppColors.border),
          Expanded(child: child),
          if (footer != null)
            Material(
              color: AppColors.white,
              child: SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                  child: footer,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.account, required this.brand});

  final Widget account;
  final Widget brand;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.white,
      child: SafeArea(
        bottom: false,
        child: Column(
          children: [
            SizedBox(
              height: 64,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Row(children: [brand, const Spacer(), account]),
              ),
            ),
            const Divider(height: 1, color: AppColors.border),
          ],
        ),
      ),
    );
  }
}

class _SideNav extends StatelessWidget {
  const _SideNav({
    required this.destinations,
    required this.selectedIndex,
    required this.onSelect,
  });

  final List<AppNavDest> destinations;
  final int selectedIndex;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 248,
      color: AppColors.white,
      child: Column(
        children: [
          Expanded(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(12, 16, 12, 16),
              children: [
                for (var i = 0; i < destinations.length; i++) ...[
                  _NavTile(
                    dest: destinations[i],
                    selected: i == selectedIndex,
                    onTap: () => onSelect(i),
                    expanded: true,
                  ),
                  const SizedBox(height: 6),
                ],
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                gradient: AppColors.primaryGradient,
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Text(
                'Fixiva\nHome services',
                style: TextStyle(
                  color: AppColors.white,
                  fontWeight: FontWeight.w600,
                  height: 1.35,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _BottomNav extends StatelessWidget {
  const _BottomNav({
    required this.destinations,
    required this.selectedIndex,
    required this.onSelect,
  });

  final List<AppNavDest> destinations;
  final int selectedIndex;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.white,
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Divider(height: 1, color: AppColors.border),
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 8, 8, 8),
              child: Row(
                children: [
                  for (var i = 0; i < destinations.length; i++)
                    Expanded(
                      child: _NavTile(
                        dest: destinations[i],
                        selected: i == selectedIndex,
                        onTap: () => onSelect(i),
                        expanded: false,
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NavTile extends StatelessWidget {
  const _NavTile({
    required this.dest,
    required this.selected,
    required this.onTap,
    required this.expanded,
  });

  final AppNavDest dest;
  final bool selected;
  final VoidCallback onTap;
  final bool expanded;

  @override
  Widget build(BuildContext context) {
    final fg = selected ? AppColors.white : AppColors.charcoal;
    final child = DecoratedBox(
      decoration: BoxDecoration(
        gradient: selected ? AppColors.primaryGradient : null,
        color: selected ? null : Colors.transparent,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Padding(
        padding: EdgeInsets.symmetric(
          horizontal: expanded ? 12 : 4,
          vertical: expanded ? 10 : 8,
        ),
        child: expanded
            ? Row(
                children: [
                  Icon(dest.icon, size: 18, color: fg),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      dest.label,
                      style: TextStyle(
                        color: fg,
                        fontWeight: selected
                            ? FontWeight.w600
                            : FontWeight.w500,
                        fontSize: 14,
                      ),
                    ),
                  ),
                ],
              )
            : Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(dest.icon, size: 18, color: fg),
                  const SizedBox(height: 4),
                  Text(
                    dest.label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: fg,
                      fontSize: 10,
                      fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                    ),
                  ),
                ],
              ),
      ),
    );

    final tappable = MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(onTap: onTap, child: child),
    );
    if (dest.testId == null) return tappable;
    return AppTestId(testId: dest.testId!, child: tappable);
  }
}
