from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from rent_renewal_tracker.reminder_rules import determine_due_threshold
from rent_renewal_tracker.reminders import deliver_reminder, process_due_reminders
from rent_renewal_tracker.weekly_digest import send_weekly_management_digest


class TestReminderEngine(IntegrationTestCase):
    def setUp(self):
        department = frappe.get_doc(
            {"doctype": "Lease Department", "department_name": frappe.generate_hash(length=10)}
        ).insert()
        property_doc = frappe.get_doc(
            {
                "doctype": "Property",
                "property_name": f"Reminder Property {frappe.generate_hash(length=8)}",
                "property_type": "Office",
            }
        ).insert()
        landlord = frappe.get_doc(
            {
                "doctype": "Landlord",
                "legal_name": f"Reminder Landlord {frappe.generate_hash(length=8)}",
            }
        ).insert()
        self.lease = frappe.get_doc(
            {
                "doctype": "Lease",
                "lease_title": "Reminder Test Lease",
                "property": property_doc.name,
                "landlord": landlord.name,
                "lease_type": "Commercial",
                "responsible_department": department.name,
                "responsible_officer": "Administrator",
                "start_date": add_days(today(), -365),
                "end_date": add_days(today(), 60),
                "notice_period_days": 30,
                "currency": "NGN",
                "rent_basis": "Monthly",
                "monthly_rent": 100000,
                "payment_frequency": "Monthly",
                "lease_status": "Active",
            }
        ).insert()
        self.policy = frappe.get_doc("Reminder Policy", "Default Lease Expiry Policy")

    def test_selects_nearest_crossed_threshold(self):
        self.assertEqual(determine_due_threshold(self.policy, 90), (90, "before:90"))
        self.assertEqual(determine_due_threshold(self.policy, 59), (60, "before:60"))
        self.assertIsNone(determine_due_threshold(self.policy, 59, {"before:60"}))
        self.assertEqual(determine_due_threshold(self.policy, 0), (0, "expiry:0"))

    def test_overdue_cadence_starts_on_day_one(self):
        self.assertEqual(determine_due_threshold(self.policy, -1), (-1, "overdue:1"))
        self.assertIsNone(determine_due_threshold(self.policy, -2))
        self.assertEqual(determine_due_threshold(self.policy, -7), (-7, "overdue:7"))

    def test_repeat_processing_does_not_duplicate_intents(self):
        process_due_reminders(queue_deliveries=False)
        first_count = frappe.db.count("Reminder Log", {"lease": self.lease.name})
        process_due_reminders(queue_deliveries=False)
        second_count = frappe.db.count("Reminder Log", {"lease": self.lease.name})

        self.assertEqual(first_count, 2)
        self.assertEqual(second_count, first_count)

    def test_contact_type_recipient_receives_email_intent(self):
        self.lease.append(
            "lease_contacts",
            {
                "contact_type": "Legal",
                "contact_name": "External Counsel",
                "email": "counsel@example.com",
                "receives_reminders": 1,
            },
        )
        self.lease.save()
        self.policy.append(
            "recipients",
            {
                "recipient_type": "Lease Contact Type",
                "recipient_value": "Legal",
                "scope": "All",
            },
        )
        self.policy.save()

        process_due_reminders(queue_deliveries=False)

        self.assertTrue(
            frappe.db.exists(
                "Reminder Log",
                {
                    "lease": self.lease.name,
                    "channel": "Email",
                    "recipient": "counsel@example.com",
                },
            )
        )

    def test_completed_lease_is_excluded(self):
        frappe.db.set_value(
            "Lease",
            self.lease.name,
            {"lease_status": "Renewed", "renewal_status": "Completed"},
        )
        process_due_reminders(queue_deliveries=False)

        self.assertFalse(frappe.db.exists("Reminder Log", {"lease": self.lease.name}))

    def test_auto_created_renewal_becomes_the_reminder_cycle(self):
        settings = frappe.get_single("Rent Renewal Settings")
        settings.auto_create_renewal_request = 1
        settings.save()
        self.lease.end_date = add_days(today(), 90)
        self.lease.save()

        process_due_reminders(queue_deliveries=False)
        renewal_name = frappe.db.get_value(
            "Renewal Request", {"lease": self.lease.name, "open_cycle_key": self.lease.name}, "name"
        )
        cycles = frappe.get_all(
            "Reminder Log", filters={"lease": self.lease.name}, pluck="renewal_cycle"
        )

        self.assertTrue(renewal_name)
        self.assertEqual(set(cycles), {renewal_name})

    def test_system_notification_delivery_finalizes_log(self):
        log_names = process_due_reminders(queue_deliveries=False)
        log_name = frappe.db.get_value(
            "Reminder Log",
            {"name": ["in", log_names], "channel": "System Notification"},
            "name",
        )
        deliver_reminder(log_name)
        log = frappe.get_doc("Reminder Log", log_name)

        self.assertEqual(log.status, "Sent")
        self.assertTrue(log.sent_at)
        self.assertTrue(frappe.db.exists("Notification Log", log.message_id))

    def test_email_failure_exhausts_configured_retries(self):
        log_names = process_due_reminders(queue_deliveries=False)
        log_name = frappe.db.get_value(
            "Reminder Log",
            {"name": ["in", log_names], "channel": "Email"},
            "name",
        )
        with patch("frappe.sendmail", side_effect=RuntimeError("SMTP unavailable")) as sendmail:
            deliver_reminder(log_name)

        log = frappe.get_doc("Reminder Log", log_name)
        self.assertEqual(sendmail.call_count, 3)
        self.assertEqual(log.status, "Failed")
        self.assertEqual(log.retry_count, 2)
        self.assertIn("SMTP unavailable", log.error_summary)

    def test_ordinary_save_cannot_modify_audit_log(self):
        log_name = process_due_reminders(queue_deliveries=False)[0]
        log = frappe.get_doc("Reminder Log", log_name)
        log.error_summary = "tampered"

        self.assertRaises(frappe.ValidationError, log.save)

    def test_weekly_digest_is_opt_in(self):
        settings = frappe.get_single("Rent Renewal Settings")
        settings.weekly_digest_enabled = 0
        settings.save()

        with patch("frappe.sendmail") as sendmail:
            self.assertIsNone(send_weekly_management_digest())

        sendmail.assert_not_called()

    def test_weekly_digest_sends_summary_to_configured_recipients(self):
        settings = frappe.get_single("Rent Renewal Settings")
        settings.weekly_digest_enabled = 1
        settings.weekly_digest_recipients = "management@example.com"
        settings.save()

        with patch("frappe.sendmail") as sendmail:
            context = send_weekly_management_digest()

        self.assertTrue(context.expiring)
        sendmail.assert_called_once()
        self.assertEqual(sendmail.call_args.kwargs["recipients"], ["management@example.com"])
