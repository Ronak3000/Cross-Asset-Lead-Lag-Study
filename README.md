# ES–SPY lead–lag study

This starter downloads and replays historical top-of-book events for one matched half hour. The first research milestone is to measure the average response in each instrument after a mid-price move in the other.

## First session

February 4, 2025, 10:00–10:30 a.m. New York time (15:00–15:30 UTC).

| Symbol | Instrument | Feed |
| --- | --- | --- |
| ESH5 | March 2025 E-mini S&P 500 futures contract | CME Globex, GLBX.MDP3 |
| SPY | SPDR S&P 500 ETF, Nasdaq venue quotes | Nasdaq TotalView, XNAS.ITCH |

Both requests use MBP-1. The files retain exchange event time, feed receive time, prices, sizes and the other original CSV fields. Timestamps are integer nanoseconds and prices use the original fixed-point scale of one billion units per price unit.

## Run on Windows

Use Python 3.11 or later. The starter uses the standard library. Open PowerShell in the project folder.

Run `python study.py demo` for an offline setup check. It replays three synthetic quotes per instrument through the same CSV reader and time merge used for historical data. The expected final line is `Records replayed: ESH5 3, SPY 3`.

To download the historical session, run the following command.

```powershell
python study.py fetch
```

Paste your Databento API key at the hidden prompt. The script also accepts the DATABENTO_API_KEY environment variable. It prints the estimated cost for each missing file and their total. Compare the amount with the available credit in your Databento billing portal. Type DOWNLOAD to fetch the data, or press Enter to cancel. To request only an estimate, run `python study.py estimate`. Billing is based on the data delivered.

The two CSVs go under `data/20250204_1500-1530Z_mbp-1/`. Completed files are reused on later runs. If the process is forcibly killed and leaves a .part file, confirm that the downloader has stopped before removing that partial file and retrying.

```powershell
python study.py replay
```

Replay reads both files locally, merges them by capture receive timestamp, prints the first three valid two-sided quotes from each feed and counts every record. It preserves source order within each feed. Equal timestamps across feeds use the input order for display. The capture points are in different locations. A later execution simulator must model when both feeds reach a common strategy location. This starter performs data acquisition and offline replay. The response curves, Hawkes fit and simulated fills are subsequent milestones.

Provider references: [historical API](https://databento.com/docs/api-historical), [cost estimates](https://databento.com/docs/api-historical/metadata/metadata-get-cost), [MBP-1 fields](https://databento.com/docs/schemas/mbp-1).
