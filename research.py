"""Fit the arrival model, run the held-out simulation, and serve the local workstation."""
import json
from bisect import bisect_right
from datetime import datetime
from pathlib import Path

from hawkes import calibrate
from simulation import MS, SEC, Settings, Tape, mid, simulate


class Session:
    def __init__(self, books, start, end, synthetic=False):
        self.synthetic = synthetic
        self.duration = end - start
        self.split = self.duration * 2 // 3
        self.books = books
        self.events = sorted((t/SEC, 2*i + int(side < 0)) for i, book in enumerate(self.books)
                             for t, side in book.arrivals)
        self.fit = calibrate(self.events, self.split/SEC, self.duration/SEC)
        self.fit["unknown_side_rows"] = [book.unknown for book in self.books]
        self.start = start

    def run(self, config):
        return simulate(*self.books, self.fit, config, self.split, self.duration)

    def chart(self, start_s, end_s, step_s):
        series = []
        for book in self.books:
            points = []
            for second in range(start_s, end_s, step_s):
                t = second * SEC
                right = min(t + step_s * SEC, end_s * SEC)
                first = book.at(t)
                quotes = book.quotes[bisect_right(book.times, t):bisect_right(book.times, right-1)]
                prices = [mid(q) for q in [first, *quotes] if q]
                if prices:
                    points.append([second, prices[0], max(prices), min(prices), prices[-1]])
            series.append(points)
        return series

    def detail(self, second):
        low, high = max(0, int(second * SEC)-50*MS), min(self.duration-1, int(second*SEC)+100*MS)
        result = []
        for book in self.books:
            times = [low, *book.times[bisect_right(book.times, low):bisect_right(book.times, high)], high]
            points = []
            for time in times:
                q = book.at(time)
                val = mid(q) if q else None
                if not points or val != points[-1][1] or time == high:
                    points.append([time/SEC, val])
            result.append(points)
        return result


def prepare(directory, start_iso, end_iso, reader, synthetic=False, benchmark=False):
    start, end = (int(datetime.fromisoformat(s).timestamp()) * SEC for s in (start_iso, end_iso))
    if synthetic:
        from sample_session import sample_books
        books = sample_books(start, end)
    else:
        books = []
        for symbol in ("ESH5", "SPY"):
            with (directory / f"{symbol}.csv").open(newline="", encoding="utf-8") as f:
                books.append(Tape(reader(f), start, end))
    session = Session(books, start, end, synthetic)
    result = session.run(Settings())
    output = directory.parents[1] / "results" / ("synthetic" if synthetic else directory.name)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "hawkes.json").open("w") as f:
        json.dump(session.fit, f, indent=2)
    with (output / "backtest.json").open("w") as f:
        json.dump(result, f, indent=2)
    print(f"Held-out trades: {result['trades']:,} | Net USD {result['net']:.2f} | "
          f"Hawkes half-life: {session.fit['half_life_ms']} ms", flush=True)
    comparisons = None
    if benchmark:
        from benchmarks import measure
        comparisons = measure(session)
        (output / "benchmarks.json").write_text(json.dumps(comparisons, indent=2), encoding="utf-8")
        print(f"Cross-asset gain over within-asset Hawkes: {comparisons['incremental_gain']:.5f} nats/event", flush=True)
    return session, result, comparisons


def run(directory, start_iso, end_iso, reader, dashboard=False, port=8765, synthetic=False, benchmark=False):
    prepared = prepare(directory, start_iso, end_iso, reader, synthetic, benchmark or dashboard)
    if dashboard:
        import uvicorn
        from api import dashboard_app

        uvicorn.run(dashboard_app(*prepared), host="127.0.0.1", port=port)
