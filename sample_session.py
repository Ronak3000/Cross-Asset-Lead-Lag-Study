"""Seeded, shareable presentation feed with an intentionally planted ES lead."""
from random import Random

from simulation import MS, SEC, Tape


def sample_books(start, end):
    rng = Random(427)
    tape = [[], []]
    time = start + MS
    while time < end - SEC:
        side = rng.choice((-1, 1))
        tape[0].append((time, side))
        tape[1].append((time + rng.randint(3, 14)*MS, side if rng.random()<.8 else -side))
        if rng.random()<.6:
            tape[0].append((time + rng.randint(1, 12)*MS, side))
        time += max(MS, int(rng.expovariate(7)*SEC))

    def rows(index):
        tick = (250_000_000, 10_000_000)[index]
        bid = (6035_000_000_000, 599_000_000_000)[index]
        def row(side, action, size):
            return dict(flags=128, action=action, side=side, price=bid+tick if side=="B" else bid,
                        size=size, bid_px_00=bid, ask_px_00=bid+tick, bid_sz_00=5, ask_sz_00=7)
        yield start, row("N","A",1)
        for t,side in sorted(tape[index]):
            bid += tick*side
            yield t, row("B" if side>0 else "A", "T", rng.randint(1,25))
        yield end-1, row("N","A",1)

    return [Tape(rows(i), start, end) for i in (0,1)]
