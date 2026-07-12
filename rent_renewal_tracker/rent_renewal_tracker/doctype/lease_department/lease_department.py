from frappe.model.document import Document


class LeaseDepartment(Document):
    def validate(self):
        self.department_name = (self.department_name or "").strip()
        self.department_code = (self.department_code or "").strip().upper() or None
