def determine_due_threshold(policy, days_to_expiry, existing_threshold_keys=None):
    """Return the nearest crossed threshold without replaying older missed reminders."""
    existing_threshold_keys = set(existing_threshold_keys or ())
    if days_to_expiry >= 0:
        thresholds = sorted(
            {
                row.days_before_expiry
                for row in policy.thresholds
                if row.enabled and row.days_before_expiry >= days_to_expiry
            }
        )
        if not thresholds:
            return None
        threshold = thresholds[0]
        key = "expiry:0" if threshold == 0 else f"before:{threshold}"
        return None if key in existing_threshold_keys else (threshold, key)

    overdue_days = abs(days_to_expiry)
    cadence = max(1, policy.overdue_cadence_days or 1)
    if overdue_days != 1 and overdue_days % cadence:
        return None
    key = f"overdue:{overdue_days}"
    return None if key in existing_threshold_keys else (-overdue_days, key)

