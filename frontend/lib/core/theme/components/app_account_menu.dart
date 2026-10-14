import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../app_theme.dart';
import 'app_button.dart';
import 'app_test_id.dart';
import 'app_visual.dart';

/// Header account control: gradient avatar + name pill, tap for the menu.
class AppAccountMenu extends StatefulWidget {
  const AppAccountMenu({
    required this.name,
    required this.onLogout,
    this.logoutLabel = 'Log out',
    this.subtitle,
    this.dark = false,
    super.key,
  });

  final String name;
  final String? subtitle;
  final String logoutLabel;
  final VoidCallback onLogout;

  /// Render for dark surfaces (charcoal sidebar).
  final bool dark;

  @override
  State<AppAccountMenu> createState() => _AppAccountMenuState();
}

class _AppAccountMenuState extends State<AppAccountMenu> {
  final _popover = ShadPopoverController();

  @override
  void dispose() {
    _popover.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final fg = widget.dark ? AppColors.white : AppColors.charcoal;
    return AppTestId(
      testId: 'shell_account_menu',
      child: ShadPopover(
        controller: _popover,
        popover: (_) => SizedBox(
          width: 240,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 4, 8, 8),
                child: Row(
                  children: [
                    FxAvatar(name: widget.name, size: 38),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            widget.name,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontWeight: FontWeight.w600,
                              fontSize: 14,
                            ),
                          ),
                          if (widget.subtitle != null)
                            Text(
                              widget.subtitle!,
                              style: const TextStyle(
                                fontSize: 12,
                                color: AppColors.muted,
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const Divider(height: 16),
              AppButton(
                text: widget.logoutLabel,
                testId: 'shell_logout',
                variant: AppButtonVariant.ghost,
                expands: true,
                leading: const Icon(LucideIcons.logOut, size: 16),
                onPressed: () {
                  _popover.hide();
                  widget.onLogout();
                },
              ),
            ],
          ),
        ),
        child: AppTestId(
          testId: 'shell_account_name',
          child: MouseRegion(
            cursor: SystemMouseCursors.click,
            child: GestureDetector(
              onTap: _popover.toggle,
              child: Container(
                padding: const EdgeInsets.fromLTRB(4, 4, 12, 4),
                decoration: BoxDecoration(
                  color: widget.dark
                      ? AppColors.white.withValues(alpha: 0.08)
                      : AppColors.lightGray,
                  borderRadius: BorderRadius.circular(AppRadii.pill),
                  border: Border.all(
                    color: widget.dark
                        ? AppColors.white.withValues(alpha: 0.12)
                        : AppColors.border,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    FxAvatar(name: widget.name, size: 30),
                    const SizedBox(width: 8),
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 140),
                      child: Text(
                        widget.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 13.5,
                          color: fg,
                        ),
                      ),
                    ),
                    const SizedBox(width: 4),
                    Icon(
                      LucideIcons.chevronDown,
                      size: 15,
                      color: fg.withValues(alpha: 0.7),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
