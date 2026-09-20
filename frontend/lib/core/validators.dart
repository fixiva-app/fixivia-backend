class Validators {
  static String? mobile(String value) {
    final digits = value.replaceAll(RegExp(r'\D'), '');
    if (digits.length < 10 || digits.length > 12) {
      return 'invalid_mobile';
    }
    return null;
  }

  static String? otp(String value) {
    if (!RegExp(r'^\d{6}$').hasMatch(value)) {
      return 'invalid_otp';
    }
    return null;
  }

  static String? pincode(String value) {
    if (!RegExp(r'^\d{6}$').hasMatch(value)) {
      return 'invalid_pincode';
    }
    return null;
  }

  static bool featuredRankOk(Iterable<int?> ranks) {
    final used = ranks.whereType<int>().toList();
    if (used.any((r) => r < 1 || r > 5)) return false;
    return used.toSet().length == used.length;
  }
}
