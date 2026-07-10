from rent_renewal_tracker.install import (
    setup_reminder_defaults,
    setup_renewal_workflow,
    setup_roles_and_workflow_primitives,
)


def execute():
    setup_roles_and_workflow_primitives()
    setup_renewal_workflow()
    setup_reminder_defaults()

