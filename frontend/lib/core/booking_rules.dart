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
