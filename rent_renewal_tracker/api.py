import frappe


APP_ROLES = {
    "Rent Renewal System Manager",
    "Lease Administrator",
    "Responsible Officer",
    "Department Head",
    "Finance Approver",
    "Legal Approver",
    "Management Approver",
    "Lease Auditor",
    "Lease Viewer",
}


def has_app_permission():
    if frappe.session.user == "Guest":
        return False
    return bool(APP_ROLES.intersection(frappe.get_roles()))

