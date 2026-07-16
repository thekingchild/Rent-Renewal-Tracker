from rent_renewal_tracker.install import setup_dashboard_defaults


def execute():
    """Normalize count and monetary Number Card formats on existing sites."""
    setup_dashboard_defaults()
