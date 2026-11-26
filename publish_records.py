"""Build the dashboard archive from saved research and the original MBP-1 CSVs."""
import csv
import gzip
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from study import records
from response import load_midpoints

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / "archive"
CHUNK_ROWS = 50000


def write_json(path, data):
    path.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False), encoding="utf-8")


def pack_feed(path, dest):
    # The original Databento CSV has one physical line per record. Only the first
    # gzip member includes the header, so concatenating members restores the file.
    digest = hashlib.sha256()
    chunks = []
    count = 0
    with path.open("rb") as source:
        header = source.readline()
        columns = next(csv.reader([header.decode().strip()]))
        digest.update(header)
        while first := source.readline():
            name = f"{path.stem}-{len(chunks):03d}.gz"
            with (dest / name).open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0, compresslevel=5) as compressed:
                if not chunks:
                    compressed.write(header)
                line = first
                for i in range(CHUNK_ROWS):
                    if i:
                        line = source.readline()
                    if not line:
                        break
                    compressed.write(line)
                    digest.update(line)
                    count += 1
            chunks.append(name)
    return dict(symbol=path.stem, rows=count, columns=columns, chunks=chunks,
                chunk_rows=CHUNK_ROWS, sha256=digest.hexdigest())


def main():
    sessions = []
    for folder in sorted((ROOT / "results").glob("20*/response.csv"), reverse=True):
        source = folder.parent
        dest = ARCHIVE / source.name
        dest.mkdir(parents=True, exist_ok=True)
        feeds = [pack_feed(p, dest) for p in sorted((ROOT / "data" / source.name).glob("*.csv"))]
        if len(feeds) != 2:
            raise ValueError(f"Expected ES and SPY files for {source.name}")
        for name in ("response.csv", "benchmarks.json", "hawkes.json", "backtest.json"):
            shutil.copyfile(source / name, dest / name)
        with folder.open(newline="", encoding="utf-8") as f:
            responses = list(csv.DictReader(f))
        day = source.name[:8]
        clock = datetime.strptime(day + source.name.split("_")[1][:4], "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
        bars = {}
        for feed in feeds:
            symbol = feed["symbol"]
            with (ROOT / "data" / source.name / f"{symbol}.csv").open(newline="", encoding="utf-8") as f:
                quotes = load_midpoints(records(f))
            candles = {}
            for timestamp, doubled_mid in zip(quotes.times, quotes.prices):
                if not doubled_mid:
                    continue
                second = timestamp // 10**9
                price = doubled_mid / (2 * 10**9)
                candle = candles.setdefault(second, [second, price, price, price, price])
                candle[2] = max(candle[2], price)
                candle[3] = min(candle[3], price)
                candle[4] = price
            bars[symbol] = list(candles.values())
        write_json(dest / "candles.json", bars)
        sessions.append(dict(id=source.name, date=f"{day[:4]}-{day[4:6]}-{day[6:]}",
                             start=clock.isoformat(), contract=feeds[0]["symbol"], feeds=feeds, responses=responses))
    write_json(ARCHIVE / "sessions.json", sessions)


if __name__ == "__main__":
    main()
