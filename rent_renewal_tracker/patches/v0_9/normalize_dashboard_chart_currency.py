from rent_renewal_tracker.install import setup_dashboard_defaults


def execute():
    """Remove monetary formatting from count-based dashboard charts."""
    setup_dashboard_defaults()
