import unittest

from response import Midpoints, NS_PER_MS, load_midpoints, responses


def book(points):
    series = Midpoints()
    for ms, price in points:
        series.add(ms * NS_PER_MS, price)
    return series


class ResponseTests(unittest.TestCase):
    def test_completed_event_final_state_and_quote_gap(self):
        def quote(time, price, flag=128):
            return time, dict(flags=flag, bid_px_00=price, ask_px_00=price,
                              bid_sz_00=1, ask_sz_00=1)
        series = load_midpoints([quote(1, 99), quote(1, 100), quote(2, 110, 0),
                                 quote(3, 0), quote(4, 100), quote(5, 100)])
        self.assertEqual(series.times, [1, 3, 4])
        self.assertEqual(series.prices, [200, 0, 200])
        self.assertEqual(series.gaps, [3])
        self.assertEqual(series.last_seen, 5)

    def test_asof_tie_endpoint_and_down_move(self):
        source = book([(0, 102), (10, 101)])
        target = book([(0, 101), (10, 100), (13, 99), (14, 98), (20, 98)])
        short, long = responses(source, target, 0, 21 * NS_PER_MS, (2, 3))
        self.assertEqual(short["events"], 1)
        self.assertEqual(short["unchanged_pct"], 100)
        self.assertEqual(long["post_bps"], 100)
        self.assertAlmostEqual(long["pre_bps"], 10_000 / 101)

    def test_excludes_incomplete_windows_and_gap_crossings(self):
        source = book([(0, 100), (1, 101), (10, 100), (15, 101), (19, 100)])
        target = book([(0, 100), (9, 0), (10, 100), (16, 101), (20, 101)])
        row, = responses(source, target, 0, 20 * NS_PER_MS, (2,))
        self.assertEqual(row["events"], 1)
        self.assertEqual(row["post_bps"], 100)
