"""Refresh the daily stock-pair filter outputs used by the Kalman dashboard."""
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np

PAIRS = [
    ("PEP", "PepsiCo", "KO", "Coca-Cola"),
    ("XOM", "Exxon Mobil", "CVX", "Chevron"),
    ("JPM", "JPMorgan Chase", "BAC", "Bank of America"),
    ("V", "Visa", "MA", "Mastercard"),
    ("HD", "Home Depot", "LOW", "Lowe's"),
]


def adjusted_closes(chart):
    values = chart["indicators"]["adjclose"][0]["adjclose"]
    return {datetime.fromtimestamp(t, timezone.utc).date().isoformat(): v
            for t, v in zip(chart["timestamp"], values, strict=True)
            if v is not None and np.isfinite(v) and v > 0}


def daily_chart(symbol):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           "?period1=1577836800&period2=1704067200&interval=1d&includeAdjustedClose=true")
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as response:
        return json.load(response)["chart"]["result"][0]


def snapshot(target, reference):
    dates = sorted(target.keys() & reference.keys())
    if len(dates) < 60:
        raise ValueError("The pair needs at least 60 overlapping trading days.")
    # Parameters and update order from Ronak3000/alpha-research-kalman/kalman.py.
    state = np.zeros(2)
    covariance = np.eye(2) * 1000
    beta, spread = [], []
    for day in dates:
        h = np.array([1, reference[day]])
        covariance += np.eye(2) * 0.0001
        innovation = target[day] - h @ state
        gain = covariance @ h / (h @ covariance @ h + 0.01)
        state += gain * innovation
        covariance = (np.eye(2) - np.outer(gain, h)) @ covariance
        beta.append(float(state[1]))
        spread.append(float(target[day] - h @ state))
    target_close = np.array([target[day] for day in dates])
    reference_close = np.array([reference[day] for day in dates])
    target_returns = np.diff(target_close) / target_close[:-1]
    reference_returns = np.diff(reference_close) / reference_close[:-1]
    correlation = None
    if np.ptp(target_returns) > 0 and np.ptp(reference_returns) > 0:
        correlation = float(np.corrcoef(target_returns, reference_returns)[0, 1])
    return dict(dates=dates, beta=beta, spread=spread, targetClose=target_close.tolist(),
                referenceClose=reference_close.tolist(), dailyReturnCorrelation=correlation)


def build_catalog(load_chart=daily_chart):
    catalog = {}
    for target, target_name, reference, reference_name in PAIRS:
        series = snapshot(adjusted_closes(load_chart(target)), adjusted_closes(load_chart(reference)))
        catalog[f"{target}/{reference}"] = dict(target=target, targetName=target_name,
                                                reference=reference, referenceName=reference_name, **series)
    return catalog


if __name__ == "__main__":
    out = Path(__file__).parent / "ui/src/kalman-snapshot.json"
    out.write_text(json.dumps(build_catalog(), separators=(",", ":"), allow_nan=False), encoding="utf-8")
