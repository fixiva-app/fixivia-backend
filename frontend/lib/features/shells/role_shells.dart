import 'package:flutter/widgets.dart';

import '../../api/client.dart';
import '../../core/session.dart';
import 'workspace_shell.dart';

export 'workspace_shell.dart';

Widget shellFor(SessionUser user, ApiClient api) => WorkspaceShell(api: api, user: user);
