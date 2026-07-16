"""Central record-level authorization for lease data."""

from __future__ import annotations

import frappe

UNRESTRICTED_ROLES = {"System Manager", "Rent Renewal System Manager", "Lease Administrator"}
ALL_CLASSIFICATIONS = {"Public", "Internal", "Confidential", "Restricted"}
ROLE_CLEARANCE = {
    "Lease Viewer": {"Public", "Internal"},
    "Responsible Officer": {"Public", "Internal", "Confidential"},
    "Department Head": {"Public", "Internal", "Confidential"},
    "Finance Approver": {"Public", "Internal", "Confidential"},
    "Legal Approver": ALL_CLASSIFICATIONS,
    "Management Approver": ALL_CLASSIFICATIONS,
    "Lease Auditor": ALL_CLASSIFICATIONS,
}
LEASE_CHILD_DOCTYPES = {
    "Lease Document": "lease",
    "Rent Schedule": "lease",
    "Renewal Request": "lease",
    "Reminder Log": "lease",
}


def _roles(user=None):
    return set(frappe.get_roles(user or frappe.session.user))


def _is_unrestricted(user=None):
    user = user or frappe.session.user
    return user == "Administrator" or bool(_roles(user) & UNRESTRICTED_ROLES)


def _clearance(user=None):
    allowed = set()
    for role in _roles(user):
        allowed.update(ROLE_CLEARANCE.get(role, ()))
    return allowed


def _sql_values(values):
    return ", ".join(frappe.db.escape(value) for value in sorted(values)) or "NULL"


def _has_department_access(department, user):
    if not department:
        return False
    return bool(
        frappe.db.exists(
            "User Permission",
            {
                "user": user,
                "allow": "Lease Department",
                "for_value": department,
                "applicable_for": ["in", (None, "", "Lease")],
            },
        )
    )


def lease_query_condition(user=None, alias="`tabLease`"):
    user = user or frappe.session.user
    if user == "Guest":
        return "1=0"
    if _is_unrestricted(user):
        return ""
    clearance = _clearance(user)
    if not clearance:
        return "1=0"
    escaped_user = frappe.db.escape(user)
    return f"""{alias}.confidentiality_classification in ({_sql_values(clearance)}) and (
        {alias}.responsible_officer = {escaped_user} or {alias}.contract_owner = {escaped_user}
        or {alias}.backup_officer = {escaped_user} or exists (
            select 1 from `tabUser Permission` up where up.user = {escaped_user}
            and up.allow = 'Lease Department' and up.for_value = {alias}.responsible_department
            and ifnull(up.applicable_for, '') in ('', 'Lease')
        ))"""


def dependent_query_condition(doctype, user=None):
    condition = lease_query_condition(user, "authorized_lease")
    if not condition:
        return ""
    field = LEASE_CHILD_DOCTYPES[doctype]
    return (
        f"exists (select 1 from `tabLease` authorized_lease where "
        f"authorized_lease.name = `tab{doctype}`.`{field}` and {condition})"
    )


def renewal_request_query(user=None):
    return dependent_query_condition("Renewal Request", user)


def rent_schedule_query(user=None):
    return dependent_query_condition("Rent Schedule", user)


def lease_document_query(user=None):
    user = user or frappe.session.user
    if _is_unrestricted(user):
        return ""
    clearance = _clearance(user)
    if not clearance:
        return "1=0"
    parent_condition = dependent_query_condition("Lease Document", user)
    return (
        f"({parent_condition}) and `tabLease Document`.confidentiality "
        f"in ({_sql_values(clearance)})"
    )


def reminder_log_query(user=None):
    return dependent_query_condition("Reminder Log", user)


def can_access_lease(lease_name, user=None):
    user = user or frappe.session.user
    if not lease_name or user == "Guest":
        return False
    lease = frappe.db.get_value(
        "Lease",
        lease_name,
        [
            "responsible_department",
            "responsible_officer",
            "contract_owner",
            "backup_officer",
            "confidentiality_classification",
        ],
        as_dict=True,
    )
    return can_access_lease_doc(lease, user)


def can_access_lease_doc(doc, user=None):
    """Evaluate access from lease values, including values on an unsaved lease."""
    user = user or frappe.session.user
    if not doc or user == "Guest":
        return False
    if _is_unrestricted(user):
        return True

    classification = doc.get("confidentiality_classification") or "Internal"
    if classification not in _clearance(user):
        return False
    if user in {
        doc.get("responsible_officer"),
        doc.get("contract_owner"),
        doc.get("backup_officer"),
    }:
        return True
    return _has_department_access(doc.get("responsible_department"), user)


def lease_has_permission(doc, user=None, ptype=None, permission_type=None, **kwargs):
    """Deny out-of-scope leases without overriding the role permission table."""
    ptype = ptype or permission_type
    if ptype == "create" and (doc.get("__islocal") or not doc.get("name")):
        return can_access_lease_doc(doc, user)
    return can_access_lease(doc.name, user)


def dependent_has_permission(doc, user=None, ptype=None, permission_type=None, **kwargs):
    """Apply the linked lease scope while leaving role grants to Frappe."""
    return can_access_lease(doc.get("lease"), user)


def lease_document_has_permission(doc, user=None, ptype=None, permission_type=None, **kwargs):
    """Apply parent Lease scope and the document's own confidentiality clearance."""
    ptype = ptype or permission_type
    user = user or frappe.session.user

    # Frappe checks "write" against a blank new document before uploading an
    # attachment to a temporary "new-lease-document-..." name. Let the normal
    # DocType permission matrix decide that probe; the actual insert still has
    # a Lease value and receives the full linked-record checks below.
    if ptype == "write" and doc.is_new() and not doc.get("lease"):
        return True

    if not can_access_lease(doc.get("lease"), user):
        return False
    if _is_unrestricted(user):
        return True
    classification = doc.get("confidentiality") or "Confidential"
    return classification in _clearance(user)


def can_approve_renewal(doc, user=None):
    return _is_unrestricted(user) or can_access_lease(doc.lease, user)
