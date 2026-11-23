"""ES signal generation and a one-share, single-position SPY execution replay."""
from bisect import bisect_right
from dataclasses import asdict, dataclass
from itertools import groupby
from math import exp, isfinite, log

from response import LAST, UNDEFINED

MS = 1_000_000
SEC = 1000 * MS


class Tape:
    def __init__(self, rows, start, end):
        self.times, self.quotes, self.moves, self.trades = [], [], [], []
        self.arrivals, self.invalid, self.unknown = [], [], 0
        self.last_seen = -1
        previous = None
        for stamp, group in groupby(rows, key=lambda item: item[0]):
            t = stamp - start
            if t < 0 or t >= end - start:
                continue
            final = None
            sides = set()
            for _, row in group:
                if row["action"] == "T":
                    if row["side"] in ("A", "B"):
                        side = 1 if row["side"] == "B" else -1
                        self.trades.append((t, side, int(row["price"]), int(row["size"])))
                        sides.add(side)
                    else:
                        self.unknown += 1
                if int(row["flags"]) & LAST:
                    final = row
            self.arrivals.extend((t, side) for side in sorted(sides))
            if final is None:
                continue
            self.last_seen = t
            bid, ask, bs, az = (int(final[k] or 0) for k in
                                ("bid_px_00", "ask_px_00", "bid_sz_00", "ask_sz_00"))
            quote = (bid, ask, bs, az) if 0 < bid <= ask < UNDEFINED and min(bs, az) > 0 else None
            if not self.times or quote != previous:
                self.times.append(t)
                self.quotes.append(quote)
                if quote is None:
                    self.invalid.append(t)
                elif previous and sum(quote[:2]) != sum(previous[:2]):
                    self.moves.append(t)
            previous = quote
        self.trade_times = [trade[0] for trade in self.trades]

    def at(self, t):
        i = bisect_right(self.times, t) - 1
        return self.quotes[i] if i >= 0 and t <= self.last_seen else None

    def continuous(self, a, b):
        return bisect_right(self.invalid, a) == bisect_right(self.invalid, b)


def mid(quote):
    return (quote[0] + quote[1]) / 2e9


@dataclass(frozen=True)
class Settings:
    feed_ms: float = 4
    order_ms: float = 0.5
    hold_ms: float = 50
    threshold_bp: float = 0.25
    fee: float = 0.003
    impact_bp: float = 0
    style: str = "market"
    filter_flow: bool = True

    def __post_init__(self):
        for name, low, high in (("feed_ms", 0, 100), ("order_ms", 0, 100),
                                ("hold_ms", 1, 1000), ("threshold_bp", .01, 10),
                                ("fee", 0, .1), ("impact_bp", 0, 10)):
            value = getattr(self, name)
            if type(value) not in (int, float) or not isfinite(value) or not low <= value <= high:
                raise ValueError(f"{name} must be between {low} and {high}")
        if self.style not in ("market", "passive") or type(self.filter_flow) is not bool:
            raise ValueError("Invalid entry style or Hawkes filter")


def signals(es, spy, fit, config, split, end):
    beta = fit["beta_per_s"]
    weights = [fit["kernel_mass"][2][j] - fit["kernel_mass"][3][j] for j in (0, 1)]
    flow, prev, idx = 0., 0, 0
    delay = round(config.feed_ms * MS)
    lookback = 50 * MS
    for t in es.moves:
        decision = t + delay
        if decision < split or decision + SEC >= end:
            continue
        while idx < len(es.arrivals) and es.arrivals[idx][0] <= t:
            arrival, side = es.arrivals[idx]
            flow = flow * exp(-beta * (arrival - prev) / SEC) + beta * weights[int(side < 0)]
            prev, idx = arrival, idx + 1
        score = flow * exp(-beta * (t - prev) / SEC)
        e0, e1 = es.at(t-lookback), es.at(t)
        s0, s1 = spy.at(decision-lookback), spy.at(decision)
        if not all((e0, e1, s0, s1)) or not es.continuous(t-lookback, t) or not spy.continuous(decision-lookback, decision):
            continue
        gap = 1e4 * (log(mid(e1)/mid(e0)) - log(mid(s1)/mid(s0)))
        if abs(gap) < config.threshold_bp or (config.filter_flow and score * gap <= 0):
            continue
        yield decision, 1 if gap > 0 else -1, gap, score


def entry(spy, arrival, side, style):
    q = spy.at(arrival)
    if not q:
        return None, arrival
    if style == "market":
        return (arrival, q[int(side > 0)] / 1e9), arrival
    # Join behind displayed shares. Only opposite signed prints at our price consume the queue.
    slot = int(side < 0)
    price, ahead = q[slot], q[2 + slot]
    expiry = arrival + 5 * MS
    qi = bisect_right(spy.times, arrival)
    for tr in spy.trades[bisect_right(spy.trade_times, arrival):bisect_right(spy.trade_times, expiry)]:
        time, aggressor, traded, size = tr
        while qi < len(spy.times) and spy.times[qi] <= time:
            quote = spy.quotes[qi]
            if not quote or quote[slot] != price:
                return None, spy.times[qi]
            qi += 1
        if aggressor == -side and traded == price:
            ahead -= size
            if ahead < 0:
                return (time, price / 1e9), time
    while qi < len(spy.times) and spy.times[qi] <= expiry:
        quote = spy.quotes[qi]
        if not quote or quote[slot] != price:
            return None, spy.times[qi]
        qi += 1
    return None, expiry


def simulate(es, spy, fit, config, split, end):
    ledger = []
    gaps = []
    horizons = (1, 2, 5, 10, 20, 50, 100, 250)
    markouts = {h: [] for h in horizons}
    busy = split - 1
    attempts = unclosed = missed = 0
    route = round(config.order_ms * MS)
    for t, side, gap, score in signals(es, spy, fit, config, split, end):
        gaps.append(abs(gap))
        initial = mid(spy.at(t))
        for h in horizons:
            later = t + h * MS
            quote = spy.at(later)
            if quote and spy.continuous(t, later):
                markouts[h].append(side * (mid(quote) / initial - 1) * 10000)
        if t <= busy:
            continue
        attempts += 1
        fill, busy = entry(spy, t + route, side, config.style)
        if fill is None:
            missed += 1
            continue
        entered, price = fill
        exit_time = entered + round(config.hold_ms * MS) + route
        q = spy.at(exit_time)
        # A market exit retries on the next valid quote if the book is unavailable.
        qi = bisect_right(spy.times, exit_time)
        while not q and qi < len(spy.times):
            exit_time, q = spy.times[qi], spy.quotes[qi]
            qi += 1
        if not q:
            unclosed += 1
            busy = end
            continue
        busy = exit_time
        exit_price = q[int(side < 0)] / 1e9
        gross = side * (exit_price - price)
        cost = 2 * config.fee + (price + exit_price) * config.impact_bp / 10000
        ledger.append(dict(signal_s=t/SEC, entry_s=entered/SEC, exit_s=exit_time/SEC,
                           side="LONG" if side > 0 else "SHORT", gap_bp=gap, flow=score,
                           entry=price, exit=exit_price, gross=gross, cost=cost, net=gross-cost))
    total = sum(r["net"] for r in ledger)
    return dict(settings=asdict(config), signals=len(gaps), attempts=attempts, missed=missed,
                unclosed=unclosed, trades=len(ledger), gross=sum(r["gross"] for r in ledger),
                net=total, avg_net=total/len(ledger) if ledger else None,
                markout=[dict(ms=h, count=len(v), bp=sum(v)/len(v) if v else None)
                         for h, v in markouts.items()], ledger=ledger)
