import 'package:flutter/material.dart';

import '../app_theme.dart';
import 'app_button.dart';
import 'app_test_id.dart';
import 'app_visual.dart';

class AppNavDest {
  const AppNavDest({required this.label, required this.icon, this.testId});

  final String label;
  final IconData icon;
  final String? testId;
}

/// Logged-in chrome: charcoal sidebar on desktop, floating bottom bar on
/// compact, white header with the account menu.
class AppWorkspaceFrame extends StatelessWidget {
  const AppWorkspaceFrame({
    required this.destinations,
    required this.selectedIndex,
    required this.onSelect,
    required this.body,
    required this.account,
    required this.brand,
    this.darkBrand,
    this.roleLabel,
    super.key,
  });

  final List<AppNavDest> destinations;
  final int selectedIndex;
  final ValueChanged<int> onSelect;
  final Widget body;
  final Widget account;
  final Widget brand;

  /// Brand mark for the dark sidebar. Defaults to [brand].
  final Widget? darkBrand;

  /// Small badge shown next to the brand on compact (e.g. role name).
  final String? roleLabel;

  @override
  Widget build(BuildContext context) {
    final compact = appIsCompact(context);
    return Scaffold(
      backgroundColor: AppColors.canvasOf(context),
      body: compact
          ? Column(
              children: [
                _Header(
                  account: account,
                  brand: brand,
                  roleLabel: roleLabel,
                ),
                Expanded(child: body),
                _BottomNav(
                  destinations: destinations,
                  selectedIndex: selectedIndex,
                  onSelect: onSelect,
                ),
              ],
            )
          : Row(
              children: [
                _SideNav(
                  destinations: destinations,
                  selectedIndex: selectedIndex,
                  onSelect: onSelect,
                  brand: darkBrand ?? brand,
                  account: account,
                ),
                Expanded(
                  child: body,
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
    this.subtitle,
    this.footer,
    super.key,
  });

  final String title;
  final String? subtitle;
  final Widget child;
  final Widget? footer;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.canvasOf(context),
      body: Column(
        children: [
          Material(
            color: AppColors.surfaceOf(context),
            child: SafeArea(
              bottom: false,
              child: Column(
                children: [
                  SizedBox(
                    height: 72,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Row(
                        children: [
                          AppButton.iconOnly(
                            testId: 'app_subpage_back',
                            icon: Icons.arrow_back_rounded,
                            onPressed: () => Navigator.maybePop(context),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  title,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: Theme.of(context).textTheme.titleLarge,
                                ),
                                if (subtitle != null)
                                  Text(
                                    subtitle!,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: Theme.of(
                                      context,
                                    ).textTheme.bodySmall,
                                  ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  Divider(height: 1, color: AppColors.lineOf(context)),
                ],
              ),
            ),
          ),
          Expanded(child: child),
          if (footer != null)
            Material(
              color: AppColors.surfaceOf(context),
              child: SafeArea(
                top: false,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Divider(height: 1, color: AppColors.lineOf(context)),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                      child: footer,
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

class _Header extends StatelessWidget {
  const _Header({required this.account, required this.brand, this.roleLabel});

  final Widget account;
  final Widget brand;
  final String? roleLabel;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.surfaceOf(context),
      child: SafeArea(
        bottom: false,
        child: Column(
          children: [
            SizedBox(
              height: 64,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Row(
                  children: [
                    brand,
                    if (roleLabel != null) ...[
                      const SizedBox(width: 10),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 9,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          gradient: AppColors.primaryGradient,
                          borderRadius: BorderRadius.circular(AppRadii.pill),
                        ),
                        child: Text(
                          roleLabel!,
                          style: const TextStyle(
                            color: AppColors.white,
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                    const Spacer(),
                    account,
                  ],
                ),
              ),
            ),
            Divider(height: 1, color: AppColors.lineOf(context)),
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
    required this.brand,
    required this.account,
  });

  final List<AppNavDest> destinations;
  final int selectedIndex;
  final ValueChanged<int> onSelect;
  final Widget brand;
  final Widget account;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 264,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.charcoalDeep, AppColors.charcoalSoft],
        ),
      ),
      child: SafeArea(
        right: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 22, 20, 8),
              child: Align(alignment: Alignment.centerLeft, child: brand),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(14, 8, 14, 8),
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
              padding: const EdgeInsets.fromLTRB(14, 8, 14, 12),
              child: Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  gradient: AppColors.primaryGradientDiagonal,
                  borderRadius: BorderRadius.circular(AppRadii.md),
                ),
                child: Stack(
                  children: [
                    const Positioned.fill(
                      child: FxRings(opacity: 0.22),
                    ),
                    Row(
                      children: [
                        Container(
                          width: 38,
                          height: 38,
                          decoration: BoxDecoration(
                            color: AppColors.white.withValues(alpha: 0.2),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Icon(
                            Icons.bolt_rounded,
                            color: AppColors.white,
                            size: 20,
                          ),
                        ),
                        const SizedBox(width: 10),
                        const Expanded(
                          child: Text(
                            'Fixiva\nHome services',
                            style: TextStyle(
                              color: AppColors.white,
                              fontWeight: FontWeight.w600,
                              height: 1.35,
                              fontSize: 13.5,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 0, 14, 16),
              child: account,
            ),
          ],
        ),
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
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 6, 14, 12),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
          decoration: BoxDecoration(
            color: AppColors.charcoal,
            borderRadius: BorderRadius.circular(26),
            boxShadow: AppShadows.lift,
          ),
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
    final fg = selected ? AppColors.white : const Color(0xFFB8B0A6);
    final tile = AnimatedContainer(
      duration: const Duration(milliseconds: 180),
      curve: Curves.easeOut,
      decoration: BoxDecoration(
        gradient: selected ? AppColors.primaryGradient : null,
        borderRadius: BorderRadius.circular(expanded ? 12 : 18),
        boxShadow: selected ? AppShadows.glowSoft : const [],
      ),
      padding: EdgeInsets.symmetric(
        horizontal: expanded ? 14 : 4,
        vertical: expanded ? 12 : 8,
      ),
      child: expanded
          ? Row(
              children: [
                Icon(dest.icon, size: 19, color: fg),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    dest.label,
                    style: TextStyle(
                      color: fg,
                      fontWeight: selected
                          ? FontWeight.w700
                          : FontWeight.w500,
                      fontSize: 14.5,
                    ),
                  ),
                ),
                if (selected)
                  const Icon(
                    Icons.arrow_forward_rounded,
                    size: 15,
                    color: AppColors.white,
                  ),
              ],
            )
          : Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(dest.icon, size: 20, color: fg),
                const SizedBox(height: 3),
                Text(
                  dest.label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: fg,
                    fontSize: 10,
                    fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                  ),
                ),
              ],
            ),
    );

    final tappable = MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(onTap: onTap, child: tile),
    );
    if (dest.testId == null) return tappable;
    return AppTestId(testId: dest.testId!, child: tappable);
  }
}
