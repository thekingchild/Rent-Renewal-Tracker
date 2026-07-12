app_name = "rent_renewal_tracker"
app_title = "Rent Renewal Tracker"
app_publisher = "Rent Renewal Tracker contributors"
app_description = "Lease lifecycle and rent renewal management"
app_license = "MIT"
app_version = "0.2.0"

required_apps = ["frappe"]

add_to_apps_screen = [
    {
        "name": "rent_renewal_tracker",
        "logo": "/assets/rent_renewal_tracker/images/rent-renewal-tracker.svg",
        "title": "Rent Renewal Tracker",
        "route": "/app/rent-renewal-tracker",
        "has_permission": "rent_renewal_tracker.api.has_app_permission",
    }
]

before_install = "rent_renewal_tracker.install.before_install"
after_install = "rent_renewal_tracker.install.after_install"

scheduler_events = {
    "daily": [
        "rent_renewal_tracker.scheduled_tasks.refresh_lease_statuses",
        "rent_renewal_tracker.scheduled_tasks.refresh_rent_schedule_statuses",
        "rent_renewal_tracker.reminders.process_due_reminders",
    ],
    "weekly": ["rent_renewal_tracker.weekly_digest.send_weekly_management_digest"],
}

permission_query_conditions = {
    "Lease": "rent_renewal_tracker.permissions.lease_query_condition",
    "Lease Document": "rent_renewal_tracker.permissions.lease_document_query",
    "Rent Schedule": "rent_renewal_tracker.permissions.rent_schedule_query",
    "Renewal Request": "rent_renewal_tracker.permissions.renewal_request_query",
    "Reminder Log": "rent_renewal_tracker.permissions.reminder_log_query",
}
has_permission = {
    "Lease": "rent_renewal_tracker.permissions.lease_has_permission",
    "Lease Document": "rent_renewal_tracker.permissions.dependent_has_permission",
    "Rent Schedule": "rent_renewal_tracker.permissions.dependent_has_permission",
    "Renewal Request": "rent_renewal_tracker.permissions.dependent_has_permission",
    "Reminder Log": "rent_renewal_tracker.permissions.dependent_has_permission",
}
