app_name = "rent_renewal_tracker"
app_title = "Rent Renewal Tracker"
app_publisher = "Rent Renewal Tracker contributors"
app_description = "Lease lifecycle and rent renewal management"
app_license = "MIT"
app_version = "0.1.0"

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
    ]
}
