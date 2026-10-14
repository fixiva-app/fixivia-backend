/// Mirrors backend `earliest_service_date` (Asia/Kolkata, +48 hours).
DateTime earliestServiceDate(DateTime now) {
  return now.add(const Duration(hours: 48));
}

bool isServiceDateAllowed(DateTime serviceDate, DateTime now) {
  final earliest = DateTime(
    earliestServiceDate(now).year,
    earliestServiceDate(now).month,
    earliestServiceDate(now).day,
  );
  final day = DateTime(serviceDate.year, serviceDate.month, serviceDate.day);
  return !day.isBefore(earliest);
}

/// Partner fallback gate, mirrors backend `force_assign_ready`.
///
/// The server is authoritative; this only decides whether to show the
/// Assign section. Ready = still open and either a full 3h window elapsed
/// since creation or two dispatch pools ran with no accept.
bool forceAssignReady(Map<String, dynamic> booking, DateTime now) {
  if (booking['status'] != 'open') return false;
  if (booking['force_assign_ready'] == true) return true;
  final refreshes = booking['dispatch_refresh_count'];
  if (refreshes is int && refreshes >= 2) return true;
  final created = DateTime.tryParse('${booking['created_at'] ?? ''}');
  if (created == null) return false;
  return now.difference(created.toLocal()) >= const Duration(hours: 3);
}
