/// In-house Shadcn wrappers. Feature screens import this barrel — not `shadcn_ui`.
///
/// ```
/// lib/core/theme/
///   app_theme.dart              ShadThemeData light/dark + Fixiva colors
///   components/
///     app_test_id.dart
///     app_button.dart           AppButton
///     app_card.dart             AppCard
///     app_input_field.dart      AppInputField
///     app_dialog.dart           AppDialog.show
///     app_choice.dart           AppChoice
///     app_alert.dart            AppAlert
///     app_select.dart           AppSelect
///     app_account_menu.dart     AppAccountMenu
///     app_workspace.dart        AppWorkspaceFrame, AppSubpageScaffold
///     components.dart           this file
/// ```
library;

export 'app_account_menu.dart';
export 'app_alert.dart';
export 'app_button.dart';
export 'app_card.dart';
export 'app_choice.dart';
export 'app_dialog.dart';
export 'app_input_field.dart';
export 'app_select.dart';
export 'app_workspace.dart';
export 'app_test_id.dart';
