"""Event-triggered returns on two asynchronous, receive-time quote streams."""

import csv
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from itertools import groupby
from statistics import fmean


HORIZONS_MS = (1, 2, 5, 10, 20, 50, 100, 250, 500, 1000)
NS_PER_MS = 1_000_000
BLOCK_NS = 300_000 * NS_PER_MS
LAST = 128
UNDEFINED = (1 << 63) - 1


@dataclass
class Midpoints:
    times: list = field(default_factory=list)
    prices: list = field(default_factory=list)
    gaps: list = field(default_factory=list)
    last_seen: int = -1

    def add(self, time, price):
        self.last_seen = time
        if self.prices and self.prices[-1] == price:
            return
        self.times.append(time)
        self.prices.append(price)
        if price == 0:
            self.gaps.append(time)


def load_midpoints(rows):
    book = Midpoints()
    for time, group in groupby(rows, key=lambda pair: pair[0]):
        # Use the last completed book event at this timestamp.
        final = None
        for _, row in group:
            if int(row["flags"]) & LAST:
                final = row
        if final is None:
            continue
        bid = int(final["bid_px_00"] or UNDEFINED)
        ask = int(final["ask_px_00"] or UNDEFINED)
        valid = (0 < bid <= ask < UNDEFINED and int(final["bid_sz_00"]) > 0
                 and int(final["ask_sz_00"]) > 0)
        # Twice the midpoint in fixed-point units keeps half ticks exact.
        book.add(time, bid + ask if valid else 0)
    if not any(book.prices):
        raise ValueError("Feed contains no usable completed two-sided quotes.")
    return book


def responses(source, target, start_ns, end_ns, horizons=HORIZONS_MS):
    margin = max(horizons) * NS_PER_MS
    samples = {ms: [] for ms in horizons}
    for i in range(1, len(source.times)):
        time = source.times[i]
        old, new = source.prices[i-1:i+1]
        if not old or not new:
            continue
        # One common sample across horizons, entirely inside the observed window.
        if time - margin < max(start_ns, target.times[0]) or time + margin > min(end_ns - 1, target.last_seen):
            continue
        if bisect_right(target.gaps, time + margin) != bisect_left(target.gaps, time - margin):
            continue
        base_idx = bisect_right(target.times, time) - 1
        base = target.prices[base_idx]
        if not base or not target.prices[bisect_right(target.times, time - margin) - 1]:
            continue
        sign = 1 if new > old else -1
        block = (time - start_ns) // BLOCK_NS
        for ms in horizons:
            delta = ms * NS_PER_MS
            before = target.prices[bisect_right(target.times, time - delta) - 1]
            after = target.prices[bisect_right(target.times, time + delta) - 1]
            post = sign * (after - base) / base * 10_000
            pre = sign * (base - before) / before * 10_000
            samples[ms].append((block, pre, post))
    for ms, sample in samples.items():
        if not sample:
            raise ValueError("No eligible midpoint moves with full target coverage.")
        blocks = {}
        for block, _, post in sample:
            blocks.setdefault(block, []).append(post)
        yield dict(horizon_ms=ms, events=len(sample),
                   pre_bps=fmean(pre for _, pre, _ in sample),
                   post_bps=fmean(post for _, _, post in sample),
                   same_direction_pct=100 * sum(post > 0 for _, _, post in sample) / len(sample),
                   unchanged_pct=100 * sum(post == 0 for _, _, post in sample) / len(sample),
                   positive_blocks=sum(fmean(values) > 0 for values in blocks.values()),
                   populated_blocks=len(blocks))


def write_curve(rows, destination):
    with destination.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
