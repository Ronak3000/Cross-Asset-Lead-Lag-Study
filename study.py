"""Download and replay the first matched ES/SPY quote sample."""

import argparse
import base64
import csv
import getpass
import heapq
import json
import os
import shutil
import sys
from contextlib import ExitStack
from datetime import datetime, timezone
from decimal import Decimal
from http.client import HTTPException
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from response import load_midpoints, responses, write_curve


START = "2025-02-04T15:00:00Z"
END = "2025-02-04T15:30:00Z"
FEEDS = {"ESH5": "GLBX.MDP3", "SPY": "XNAS.ITCH"}
DATA = Path(__file__).resolve().parent / "data" / "20250204_1500-1530Z_mbp-1"
FIELDS = {"ts_recv", "ts_event", "instrument_id", "bid_px_00", "ask_px_00",
          "bid_sz_00", "ask_sz_00"}
UNDEF_PRICE = (1 << 63) - 1


def request(method, key, symbol, **options):
    fields = dict(dataset=FEEDS[symbol], symbols=symbol, stype_in="raw_symbol",
                  schema="mbp-1", start=START, end=END, **options)
    token = base64.b64encode(f"{key}:".encode()).decode()
    req = Request(f"https://hist.databento.com/v0/{method}",
                  data=urlencode(fields).encode(),
                  headers={"Authorization": f"Basic {token}"})
    return urlopen(req, timeout=90)


def records(stream):
    reader = csv.DictReader(stream)
    if not FIELDS.issubset(reader.fieldnames or []):
        raise ValueError(f"Expected Databento MBP-1 columns in {stream.name}")
    last_timestamp = -1
    for row in reader:
        timestamp = int(row["ts_recv"])
        if timestamp < last_timestamp:
            raise ValueError(f"Receive timestamps out of order in {stream.name}")
        last_timestamp = timestamp
        yield timestamp, row


def save_feed(key, symbol):
    path = DATA / f"{symbol}.csv"
    partial = path.with_suffix(".part")
    # Exclusive creation also prevents concurrent downloads of the same leg.
    output = partial.open("xb")
    try:
        with output:
            if path.exists():
                output.close()
                partial.unlink()
                return
            with request("timeseries.get_range", key, symbol, encoding="csv",
                         compression="none", pretty_ts="false", pretty_px="false",
                         map_symbols="false") as response:
                shutil.copyfileobj(response, output)
        with partial.open(newline="", encoding="utf-8") as stream:
            count = sum(1 for _ in records(stream))
        if count == 0:
            raise ValueError(f"No records returned for {symbol}")
        partial.replace(path)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    print(f"Saved {symbol}: {count:,} records")


def acquire(command):
    pending = [s for s in FEEDS if not (DATA / f"{s}.csv").is_file()]
    if not pending:
        print("Both feeds are saved. Run: python study.py replay")
        return
    key = os.environ.get("DATABENTO_API_KEY", "").strip()
    if not key and sys.stdin.isatty():
        key = getpass.getpass("Databento API key (hidden): ").strip()
    if not key:
        raise ValueError("Run in an interactive terminal or set DATABENTO_API_KEY.")
    print(f"Historical MBP-1 | {START} to {END}")
    total = Decimal(0)
    for symbol in pending:
        with request("metadata.get_cost", key, symbol) as response:
            cost = Decimal(str(json.load(response)))
        if not cost.is_finite() or cost < 0:
            raise ValueError(f"Invalid cost estimate for {symbol}")
        total += cost
        print(f"{symbol} on {FEEDS[symbol]}: USD {cost}")
    print(f"Estimated total for missing files: USD {total}")
    if command == "estimate":
        return
    if input("Check your available credit. Type DOWNLOAD to continue: ").strip() != "DOWNLOAD":
        print("Cancelled.")
        return
    DATA.mkdir(parents=True, exist_ok=True)
    for symbol in pending:
        save_feed(key, symbol)


def tagged_records(stream, symbol):
    for timestamp, row in records(stream):
        yield timestamp, symbol, row


def replay(directory=DATA):
    with ExitStack() as stack:
        streams = []
        for symbol in FEEDS:
            path = directory / f"{symbol}.csv"
            if not path.is_file():
                raise ValueError(f"Missing {path.name}. Run: python study.py fetch")
            stream = stack.enter_context(path.open(newline="", encoding="utf-8"))
            streams.append(tagged_records(stream, symbol))
        counts = dict.fromkeys(FEEDS, 0)
        shown = dict.fromkeys(FEEDS, 0)
        for timestamp, symbol, row in heapq.merge(*streams, key=lambda item: item[0]):
            counts[symbol] += 1
            if shown[symbol] >= 3:
                continue
            bid = int(row["bid_px_00"] or UNDEF_PRICE)
            ask = int(row["ask_px_00"] or UNDEF_PRICE)
            if not 0 < bid <= ask < UNDEF_PRICE:
                continue
            seconds, ns = divmod(timestamp, 10**9)
            clock = datetime.fromtimestamp(seconds, timezone.utc).strftime("%H:%M:%S")
            print(f"{clock}.{ns:09d} UTC  {symbol:4}  "
                  f"bid {bid / 1e9:.2f} x {row['bid_sz_00']}  "
                  f"ask {ask / 1e9:.2f} x {row['ask_sz_00']}")
            shown[symbol] += 1
        print("Records replayed:", ", ".join(f"{s} {n:,}" for s, n in counts.items()))
        if not all(shown.values()):
            raise ValueError("At least one feed has no valid two-sided quote.")


def demo():
    print("Offline demo with synthetic quotes")
    with TemporaryDirectory() as temp:
        directory = Path(temp)
        for offset, (symbol, bid) in enumerate([("ESH5", 6050000000000), ("SPY", 605000000000)]):
            with (directory / f"{symbol}.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=sorted(FIELDS))
                writer.writeheader()
                tick = 250000000 if symbol == "ESH5" else 10000000
                for step in range(3):
                    timestamp = 1738681200000000000 + (2 * step + offset) * 1000000
                    writer.writerow(dict(ts_recv=timestamp, ts_event=timestamp - 1000,
                                         instrument_id=offset + 1, bid_px_00=bid + step * tick,
                                         ask_px_00=bid + (step + 1) * tick, bid_sz_00=5, ask_sz_00=8))
        replay(directory)


def analyze():
    books = {}
    for symbol in FEEDS:
        with (DATA / f"{symbol}.csv").open(newline="", encoding="utf-8") as stream:
            books[symbol] = load_midpoints(records(stream))
    start, end = (int(datetime.fromisoformat(t).timestamp()) * 10**9 for t in (START, END))
    result = []
    es, spy = FEEDS
    for source, target in ((es, spy), (spy, es)):
        for row in responses(books[source], books[target], start, end):
            result.append(dict(source=source, target=target, **row))
            print(f"{source} -> {target}  {row['horizon_ms']:4} ms  "
                  f"{row['post_bps']:+.4f} bp  ({row['events']:,} moves)")
    directory = DATA.parents[1] / "results" / DATA.name
    directory.mkdir(parents=True, exist_ok=True)
    write_curve(result, directory / "response.csv")
    print(f"Saved {directory / 'response.csv'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["demo", "estimate", "fetch", "replay", "analyze", "research", "dashboard", "benchmark"])
    parser.add_argument("--port", type=int, default=8765, help="local dashboard port")
    parser.add_argument("--synthetic", action="store_true", help="use generated quotes for research or the dashboard")
    args = parser.parse_args()
    command = args.command
    if command == "demo":
        demo()
    elif command == "replay":
        replay()
    elif command == "analyze":
        analyze()
    elif command in ("research", "dashboard", "benchmark"):
        from research import run
        run(DATA, START, END, records, dashboard=command == "dashboard", port=args.port, synthetic=args.synthetic,
            benchmark=command == "benchmark")
    else:
        acquire(command)


if __name__ == "__main__":
    try:
        main()
    except HTTPError as exc:
        sys.exit(f"Databento HTTP {exc.code}: {exc.reason}. Check account access and retry.")
    except (OSError, HTTPException, ValueError, EOFError) as exc:
        sys.exit(str(exc))
