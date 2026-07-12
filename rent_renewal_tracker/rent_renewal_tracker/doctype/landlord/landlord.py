from frappe.model.document import Document


class Landlord(Document):
    def validate(self):
        self.legal_name = (self.legal_name or "").strip()
        self.primary_contact_email = (self.primary_contact_email or "").strip().lower()
        self.registration_identifier = (self.registration_identifier or "").strip() or None
