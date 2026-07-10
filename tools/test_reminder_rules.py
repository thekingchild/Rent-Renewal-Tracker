import unittest
from types import SimpleNamespace

from rent_renewal_tracker.reminder_rules import determine_due_threshold


def make_policy(cadence=7):
    thresholds = [
        SimpleNamespace(days_before_expiry=days, enabled=True)
        for days in (90, 60, 30, 14, 7, 0)
    ]
    return SimpleNamespace(thresholds=thresholds, overdue_cadence_days=cadence)


class TestReminderRules(unittest.TestCase):
    def setUp(self):
        self.policy = make_policy()

    def test_exact_thresholds(self):
        self.assertEqual(determine_due_threshold(self.policy, 90), (90, "before:90"))
        self.assertEqual(determine_due_threshold(self.policy, 0), (0, "expiry:0"))

    def test_nearest_crossed_threshold_is_used_for_catch_up(self):
        self.assertEqual(determine_due_threshold(self.policy, 59), (60, "before:60"))
        self.assertEqual(determine_due_threshold(self.policy, 2), (7, "before:7"))

    def test_sent_nearest_threshold_does_not_replay_older_thresholds(self):
        self.assertIsNone(determine_due_threshold(self.policy, 59, {"before:60"}))

    def test_future_threshold_is_not_due(self):
        self.assertIsNone(determine_due_threshold(self.policy, 91))

    def test_overdue_day_one_and_cadence(self):
        self.assertEqual(determine_due_threshold(self.policy, -1), (-1, "overdue:1"))
        self.assertIsNone(determine_due_threshold(self.policy, -2))
        self.assertEqual(determine_due_threshold(self.policy, -7), (-7, "overdue:7"))

    def test_overdue_deduplication(self):
        self.assertIsNone(determine_due_threshold(self.policy, -7, {"overdue:7"}))


if __name__ == "__main__":
    unittest.main()

