enum UserRole {
  masterAdmin,
  partnerOwner,
  partnerAdmin,
  servicePartner,
  customer,
}

UserRole roleFromApi(String value) {
  return switch (value) {
    'master_admin' => UserRole.masterAdmin,
    'partner_owner' => UserRole.partnerOwner,
    'partner_admin' => UserRole.partnerAdmin,
    'service_partner' => UserRole.servicePartner,
    _ => UserRole.customer,
  };
}

class SessionUser {
  const SessionUser({
    required this.id,
    required this.role,
    required this.fullName,
    this.partnerId,
  });

  final String id;
  final UserRole role;
  final String fullName;
  final String? partnerId;
}
