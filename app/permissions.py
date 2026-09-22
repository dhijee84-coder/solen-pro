from .models import RoleName

ALL_PERMISSIONS = [
    "users.view", "users.create", "users.edit", "users.delete",
    "admins.create", "admins.edit", "admins.remove",
    "super_admins.create", "super_admins.edit", "super_admins.remove",
    "clients.view", "clients.create", "clients.edit", "clients.delete",
    "clients.services.view", "clients.services.manage",
    "projects.view", "projects.create", "projects.edit", "projects.delete",
    "panels.view", "panels.create", "panels.edit", "panels.allocate",
    "payments.view", "payments.create", "payments.edit",
    "documents.view", "documents.upload", "documents.delete", "documents.verify",
    "notifications.view", "notifications.create",
    "reports.view", "reports.export",
    "audit_logs.view",
    "system.settings",
    "website.settings",
    "warranty.view", "warranty.manage", "warranty.claims.manage",
    "enquiries.view", "enquiries.manage",
    "faqs.manage",
    "roles.view", "roles.manage",
]

# Role -> permission codes. PRIMARY_ADMIN implicitly has everything (checked in code).
ROLE_PERMISSIONS = {
    RoleName.PRIMARY_ADMIN: ALL_PERMISSIONS,
    RoleName.SUPER_ADMIN: [
        "clients.view", "clients.create", "clients.edit", "clients.delete",
        "clients.services.view", "clients.services.manage",
        "admins.create", "admins.edit", "admins.remove",
        "projects.view", "projects.create", "projects.edit", "projects.delete",
        "panels.view", "panels.create", "panels.edit", "panels.allocate",
        "payments.view", "payments.create", "payments.edit",
        "documents.view", "documents.upload", "documents.delete", "documents.verify",
        "notifications.view", "notifications.create",
        "reports.view", "reports.export",
        "audit_logs.view",
        "users.view",
        "warranty.view", "warranty.manage", "warranty.claims.manage",
        "enquiries.view", "enquiries.manage",
        "faqs.manage",
    ],
    RoleName.ADMIN: [
        "clients.view", "clients.create", "clients.edit",
        "clients.services.view", "clients.services.manage",
        "projects.view",
        "panels.view", "panels.allocate",
        "payments.view", "payments.create", "payments.edit",
        "documents.view", "documents.upload", "documents.verify",
        "notifications.view", "notifications.create",
        "reports.view",
        "warranty.view", "warranty.claims.manage",
        "enquiries.view", "enquiries.manage",
    ],
    RoleName.CLIENT: [],
}


def role_has_permission(role: RoleName, code: str) -> bool:
    if role == RoleName.PRIMARY_ADMIN:
        return True
    return code in ROLE_PERMISSIONS.get(role, [])


def permission_matrix() -> dict:
    """Return a role × permission matrix for the Roles & Permissions UI."""
    roles = [RoleName.CLIENT, RoleName.ADMIN, RoleName.SUPER_ADMIN, RoleName.PRIMARY_ADMIN]
    matrix = {}
    for code in ALL_PERMISSIONS:
        matrix[code] = {r.value: role_has_permission(r, code) for r in roles}
    return matrix
