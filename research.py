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


def run(directory, start_iso, end_iso, reader, dashboard=False, port=8765, synthetic=False, benchmark=False):
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
    if benchmark or dashboard:
        from benchmarks import measure
        comparisons = measure(session)
        (output / "benchmarks.json").write_text(json.dumps(comparisons, indent=2), encoding="utf-8")
        print(f"Cross-asset gain over within-asset Hawkes: {comparisons['incremental_gain']:.5f} nats/event", flush=True)
        if dashboard:
            serve(session, result, port, comparisons)


def serve(session, initial, port, comparisons):
    from flask import Flask, jsonify, request, send_from_directory
    from plotly.offline import get_plotlyjs

    static = Path(__file__).resolve().parent / "ui"
    app = Flask(__name__, static_folder=str(static), static_url_path="/ui")
    app.config["MAX_CONTENT_LENGTH"] = 4096
    chart = session.chart(session.split//SEC, session.duration//SEC, 1)
    bundle = get_plotlyjs()

    @app.get("/")
    def index():
        return send_from_directory(static, "index.html")

    @app.get("/plot.js")
    def plot():
        return app.response_class(bundle, mimetype="application/javascript")

    @app.get("/api/session")
    def view():
        return jsonify(start=session.start//SEC, split=session.split//SEC, end=session.duration//SEC, synthetic=session.synthetic,
                       model=session.fit, result=initial, bars=chart, benchmarks=comparisons)

    @app.post("/api/run")
    def replay():
        try:
            body = request.get_json()
            if not isinstance(body, dict):
                raise ValueError("Expected a settings object")
            return jsonify(session.run(Settings(**body)))
        except (ValueError, TypeError) as exc:
            return jsonify(error=str(exc)), 400

    @app.get("/api/detail")
    def detail():
        second = request.args.get("t", type=float)
        if second is None or not session.split/SEC <= second < session.duration/SEC:
            return jsonify(error="Choose a time in the evaluation window"), 400
        return jsonify(session.detail(second))

    print(f"Open http://127.0.0.1:{port}", flush=True)
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
