import frappe
from frappe import _
from frappe.model.document import Document


class Property(Document):
    def validate(self):
        if self.latitude is not None and not -90 <= self.latitude <= 90:
            frappe.throw(_("Latitude must be between -90 and 90."))
        if self.longitude is not None and not -180 <= self.longitude <= 180:
            frappe.throw(_("Longitude must be between -180 and 180."))
