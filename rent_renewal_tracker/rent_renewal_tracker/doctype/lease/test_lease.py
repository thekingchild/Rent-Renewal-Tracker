import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from rent_renewal_tracker.rent_renewal_tracker.doctype.lease.lease import (
    sync_lease_overlap_review_flags,
)


class TestLease(IntegrationTestCase):
    def setUp(self):
        self.department = frappe.get_doc(
            {"doctype": "Lease Department", "department_name": frappe.generate_hash(length=10)}
        ).insert()
        self.property = frappe.get_doc(
            {
                "doctype": "Property",
                "property_name": f"Test Property {frappe.generate_hash(length=8)}",
                "property_type": "Office",
                "region": "West",
            }
        ).insert()
        self.landlord = frappe.get_doc(
            {
                "doctype": "Landlord",
                "legal_name": f"Test Landlord {frappe.generate_hash(length=8)}",
            }
        ).insert()

    def make_lease(self, **overrides):
        values = {
            "doctype": "Lease",
            "lease_title": "Test Lease",
            "property": self.property.name,
            "landlord": self.landlord.name,
            "lease_type": "Commercial",
            "responsible_department": self.department.name,
            "responsible_officer": "Administrator",
            "start_date": add_days(today(), -30),
            "end_date": add_days(today(), 180),
            "notice_period_days": 60,
            "currency": "NGN",
            "rent_basis": "Monthly",
            "monthly_rent": 100000,
            "payment_frequency": "Monthly",
            "lease_status": "Active",
        }
        values.update(overrides)
        return frappe.get_doc(values)

    def test_calculates_notice_and_annual_cost(self):
        lease = self.make_lease(annual_service_charge=50000, annual_tax=25000).insert()

        self.assertEqual(lease.notice_deadline, add_days(lease.end_date, -60))
        self.assertEqual(lease.annual_rent, 1200000)
        self.assertEqual(lease.total_annual_occupancy_cost, 1275000)
        self.assertEqual(lease.region, "West")

    def test_marks_lease_expiring_soon(self):
        lease = self.make_lease(end_date=add_days(today(), 45)).insert()

        self.assertEqual(lease.lease_status, "Expiring Soon")

    def test_monthly_basis_recalculates_annual_rent_after_edit(self):
        lease = self.make_lease().insert()
        lease.monthly_rent = 125000
        lease.save()

        self.assertEqual(lease.annual_rent, 1500000)

    def test_earliest_contract_action_becomes_next_action(self):
        lease = self.make_lease(
            renewal_option_deadline=add_days(today(), 75),
            break_clause_date=add_days(today(), 60),
        ).insert()

        self.assertEqual(lease.next_action_date, add_days(today(), 60))

    def test_rejects_invalid_term(self):
        lease = self.make_lease(start_date=today(), end_date=add_days(today(), -1))

        self.assertRaises(frappe.ValidationError, lease.insert)

    def test_rejects_negative_rent(self):
        lease = self.make_lease(monthly_rent=-1)

        self.assertRaises(frappe.ValidationError, lease.insert)

    def test_rejects_overlapping_ongoing_lease_for_same_property(self):
        first = self.make_lease().insert()
        with self.assertRaises(frappe.ValidationError):
            self.make_lease(
                lease_title="Overlapping Lease",
                start_date=add_days(today(), 30),
                end_date=add_days(today(), 90),
            ).insert()

        self.assertTrue(frappe.db.exists("Lease", first.name))

    def test_allows_next_lease_after_existing_term_ends(self):
        first = self.make_lease(end_date=add_days(today(), 30)).insert()
        second = self.make_lease(
            lease_title="Adjacent Lease",
            start_date=add_days(first.end_date, 1),
            end_date=add_days(first.end_date, 90),
        ).insert()

        self.assertTrue(frappe.db.exists("Lease", second.name))

    def test_legacy_overlap_allows_unrelated_edit_and_clears_after_resolution(self):
        legacy = self.make_lease(
            lease_title="Legacy Conflict",
            lease_status="Draft",
        ).insert()
        current = self.make_lease(lease_title="Current Conflict").insert()
        frappe.db.set_value("Lease", legacy.name, "lease_status", "Active")

        legacy = frappe.get_doc("Lease", legacy.name)
        legacy.comments = "Reviewed without changing the property or term."
        legacy.save()
        self.assertTrue(legacy.overlap_review_required)

        frappe.db.set_value("Lease", current.name, "lease_status", "Terminated")
        sync_lease_overlap_review_flags()
        self.assertEqual(
            frappe.db.get_value("Lease", legacy.name, "overlap_review_required"),
            0,
        )
        self.assertEqual(
            frappe.db.get_value("Lease", current.name, "overlap_review_required"),
            0,
        )

    def test_legacy_overlap_can_be_resolved_by_terminating_one_lease(self):
        legacy = self.make_lease(
            lease_title="Legacy Conflict to End",
            lease_status="Draft",
        ).insert()
        current = self.make_lease(lease_title="Current Conflict to Keep").insert()
        frappe.db.set_value("Lease", legacy.name, "lease_status", "Active")

        sync_lease_overlap_review_flags()
        legacy = frappe.get_doc("Lease", legacy.name)
        legacy.lease_status = "Terminated"
        legacy.save()
        sync_lease_overlap_review_flags()

        self.assertEqual(legacy.overlap_review_required, 0)
        self.assertEqual(
            frappe.db.get_value("Lease", current.name, "overlap_review_required"),
            0,
        )

    def test_assigns_document_id(self):
        lease = self.make_lease(lease_status="Draft").insert()

        self.assertEqual(lease.lease_id, lease.name)
        self.assertTrue(lease.lease_id.startswith("LEASE-"))

    def test_submit_activates_lease(self):
        lease = self.make_lease(lease_status="Draft").insert()

        lease.submit()

        self.assertEqual(lease.docstatus, 1)
        self.assertIn(lease.lease_status, {"Active", "Expiring Soon"})

    def test_cancelled_lease_can_be_amended_and_resubmitted(self):
        migration_source_id = f"MIG-{frappe.generate_hash(length=10)}"
        lease = self.make_lease(
            lease_status="Draft", migration_source_id=migration_source_id
        ).insert()
        lease.submit()
        lease.cancel()

        amendment = frappe.copy_doc(lease)
        amendment.docstatus = 0
        amendment.amended_from = lease.name
        amendment.insert()
        amendment.submit()

        self.assertEqual(amendment.amended_from, lease.name)
        self.assertEqual(amendment.name, f"{lease.name}-1")
        self.assertEqual(amendment.docstatus, 1)
        self.assertEqual(amendment.lease_id, amendment.name)
        self.assertIsNone(amendment.migration_source_id)
        self.assertEqual(lease.migration_source_id, migration_source_id)

    def test_cancelled_successor_lease_can_be_amended(self):
        predecessor = self.make_lease(lease_title="Predecessor Lease").insert()
        successor = self.make_lease(
            lease_title="Successor Lease",
            lease_status="Draft",
            predecessor_lease=predecessor.name,
            start_date=add_days(predecessor.end_date, 1),
            end_date=add_days(predecessor.end_date, 365),
        ).insert()
        successor.submit()
        successor.cancel()

        amendment = frappe.copy_doc(successor)
        amendment.docstatus = 0
        amendment.amended_from = successor.name
        amendment.insert()

        self.assertEqual(amendment.predecessor_lease, predecessor.name)
        self.assertEqual(amendment.amended_from, successor.name)

    def test_predecessor_has_only_one_current_successor(self):
        predecessor = self.make_lease(lease_title="Unique Predecessor").insert()
        first = self.make_lease(
            lease_title="First Successor",
            predecessor_lease=predecessor.name,
            start_date=add_days(predecessor.end_date, 1),
            end_date=add_days(predecessor.end_date, 365),
        ).insert()

        with self.assertRaises(frappe.ValidationError):
            self.make_lease(
                lease_title="Second Successor",
                predecessor_lease=predecessor.name,
                start_date=add_days(predecessor.end_date, 1),
                end_date=add_days(predecessor.end_date, 365),
            ).insert()

        self.assertTrue(frappe.db.exists("Lease", first.name))
