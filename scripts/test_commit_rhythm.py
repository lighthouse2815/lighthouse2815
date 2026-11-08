import datetime as dt
import unittest
import xml.etree.ElementTree as ET

from update_commit_rhythm import month_ranges, render, streaks


class CommitRhythmTests(unittest.TestCase):
    def test_streak_can_continue_from_yesterday(self):
        start = dt.date(2026, 1, 1)
        end = dt.date(2026, 1, 6)
        counts = {start + dt.timedelta(days=day): 1 for day in (0, 1, 3, 4)}
        self.assertEqual(streaks(counts, start, end), (2, 2))
        self.assertEqual(streaks(counts, start, end + dt.timedelta(days=1)), (0, 2))

    def test_month_ranges_cover_leap_day(self):
        self.assertEqual(list(month_ranges(dt.date(2024, 2, 28), dt.date(2024, 3, 2))), [
            (dt.date(2024, 2, 28), dt.date(2024, 2, 29)),
            (dt.date(2024, 3, 1), dt.date(2024, 3, 2)),
        ])

    def test_card_is_valid_svg_with_commit_counts(self):
        day = dt.date(2026, 1, 1)
        svg = render({day: 3}, day, day)
        self.assertEqual(ET.fromstring(svg).tag, "{http://www.w3.org/2000/svg}svg")
        self.assertIn("3 PUBLIC COMMITS", svg)
        self.assertIn("2026-01-01: 3 commits", svg)


if __name__ == "__main__":
    unittest.main()
