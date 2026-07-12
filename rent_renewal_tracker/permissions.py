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
LEASE_CHILD_DOCTYPES = {"Lease Document": "lease", "Rent Schedule": "lease", "Renewal Request": "lease", "Reminder Log": "lease"}

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

def lease_query_condition(user=None, alias="`tabLease`"):
    user = user or frappe.session.user
    if user == "Guest": return "1=0"
    if _is_unrestricted(user): return ""
    clearance = _clearance(user)
    if not clearance: return "1=0"
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
    if not condition: return ""
    field = LEASE_CHILD_DOCTYPES[doctype]
    return f"exists (select 1 from `tabLease` authorized_lease where authorized_lease.name = `tab{doctype}`.`{field}` and {condition})"

def renewal_request_query(user=None): return dependent_query_condition("Renewal Request", user)
def rent_schedule_query(user=None): return dependent_query_condition("Rent Schedule", user)
def lease_document_query(user=None): return dependent_query_condition("Lease Document", user)
def reminder_log_query(user=None): return dependent_query_condition("Reminder Log", user)

def can_access_lease(lease_name, user=None):
    user = user or frappe.session.user
    if not lease_name or user == "Guest": return False
    if _is_unrestricted(user): return True
    lease = frappe.db.get_value("Lease", lease_name, ["responsible_department", "responsible_officer", "contract_owner", "backup_officer", "confidentiality_classification"], as_dict=True)
    if not lease or lease.confidentiality_classification not in _clearance(user): return False
    if user in {lease.responsible_officer, lease.contract_owner, lease.backup_officer}: return True
    return bool(frappe.db.exists("User Permission", {"user": user, "allow": "Lease Department", "for_value": lease.responsible_department, "applicable_for": ["in", (None, "", "Lease")]}))

def lease_has_permission(doc, user=None, permission_type=None):
    return None if can_access_lease(doc.name, user) else False

def dependent_has_permission(doc, user=None, permission_type=None):
    return None if can_access_lease(doc.lease, user) else False

def can_approve_renewal(doc, user=None):
    return _is_unrestricted(user) or can_access_lease(doc.lease, user)
