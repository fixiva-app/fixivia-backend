import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import 'app_button.dart';
import 'app_test_id.dart';

/// Header account control: tap the name, then Logout.
class AppAccountMenu extends StatefulWidget {
  const AppAccountMenu({
    required this.name,
    required this.onLogout,
    this.logoutLabel = 'Log out',
    this.subtitle,
    super.key,
  });

  final String name;
  final String? subtitle;
  final String logoutLabel;
  final VoidCallback onLogout;

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
    return AppTestId(
      testId: 'shell_account_menu',
      child: ShadPopover(
        controller: _popover,
        popover: (_) => SizedBox(
          width: 220,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 4, 8, 8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.name,
                      style: ShadTheme.of(
                        context,
                      ).textTheme.small.copyWith(fontWeight: FontWeight.w600),
                    ),
                    if (widget.subtitle != null)
                      Text(
                        widget.subtitle!,
                        style: ShadTheme.of(context).textTheme.muted,
                      ),
                  ],
                ),
              ),
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
        child: AppButton(
          text: widget.name,
          testId: 'shell_account_name',
          variant: AppButtonVariant.ghost,
          expands: false,
          trailing: const Icon(LucideIcons.chevronDown, size: 16),
          onPressed: _popover.toggle,
        ),
      ),
    );
  }
}
