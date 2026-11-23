# Cross-Asset Lead–Lag Arbitrage Using Hawkes Processes

A local research terminal for comparing ES futures and SPY, modelling signed trade arrivals, and testing whether a short-lived price gap survives routing latency, the bid–ask spread and fees.

## Open the terminal

In the downloaded project bundle, open **Phase-demo.html** directly in Chrome or Edge for a portable synthetic presentation. This version has three precomputed execution scenarios. You can switch scenarios, inspect trades, and recalculate fees and impact in the browser. The synthetic generator intentionally plants a futures lead. Only the Python terminal reads the historical files and runs new execution paths.

For the historical terminal, open PowerShell in the original project directory (the one containing your downloaded `data` folder).

```powershell
python -m pip install -r requirements.txt
python study.py dashboard
```

Open http://127.0.0.1:8765 after the fit finishes. To use another port, add `--port 8766`. Stop the server with Ctrl+C. To demonstrate the full engine on another machine without market data, use `python study.py dashboard --synthetic`. Both versions work offline once dependencies are installed.

## React dashboard and benchmarks

The browser UI uses React 19 and Plotly. Flask serves the compiled client locally. For frontend changes, run `npm install --prefix ui` and `npm run build --prefix ui`, then refresh. The committed production bundle lets a fresh Python installation start the dashboard without a Node build. On a fresh checkout, `python portable_demo.py` creates `results/Phase-demo.html` with embedded scripts and synthetic data.

Run `python study.py benchmark` in the project folder to reproduce the historical comparisons, or add `--synthetic` to run without purchased data. Open **Benchmarks** to see the model scores, seven execution scenarios, and five timed warm simulations. Each warm timing covers signal generation, fills, costs, and ledger construction with quotes and parameters already in memory. Machine timings vary between runs.

## Three-minute interview walkthrough

1. **Market replay.** Compare ESH5 and SPY in basis points, then switch to SPY midpoint candles. Zoom to a one-minute window. The overview uses one-second bars. The fill inspector below resolves individual ticks.
2. **Hawkes model.** Hover over ES buy → SPY buy. Compare that cross-market excitation with SPY buy → SPY buy. The selected common kernel half-life is a trade-arrival parameter. Use the response chart to discuss how quickly the price signal was realized.
3. **Execution log.** Select a round trip and inspect the quotes around its decision timestamp. Increase the per-side fee from $0.003 to $0.01, rerun, and compare net P&L. Switch to passive entry to see how often displayed queue depth prevents a simulated fill. The table shows the first 100 trades, and CSV export includes every closed trade.

## Model and execution assumptions

- **Arrival model.** Four event streams represent buyer- and seller-initiated trades in ES and SPY. Group prints with the same instrument, side, and nanosecond into one arrival. Omit unknown aggressor sides. Simultaneous streams share the same pre-event history. Fit constant backgrounds and a nonnegative 4 × 4 exponential kernel using continuous-time maximum likelihood. A cell in row i, column j is the integrated excitation from j to i. Row sums are capped at 0.99, a sufficient stability restriction. Estimate one common half-life on a 1, 5, 20, 100, 500 ms grid using training likelihood.
- **Evaluation.** Fit the first 20 minutes and freeze parameters for the last 10. Carry training history into the held-out likelihood and compare with four constant-rate Poisson streams estimated on the same training data. This is an intraday time split. The full half hour was explored in the earlier descriptive baseline. Replication on unseen days is still outstanding.
- **Dislocation.** On arrival of an ES midpoint change, subtract SPY’s trailing 50 ms log return from the trailing 50 ms ES log return using only the quotes available to the strategy. Trigger when the absolute difference exceeds the configured basis-point threshold. The optional direction filter uses the sign of the fitted ES contribution to SPY buy intensity minus SPY sell intensity at the latest available ES timestamp. The strategy trades one SPY share and uses ES as a signal. It carries directional risk.
- **Signal decay.** Compute signed SPY midpoint returns at 1–250 ms after every eligible signal, including those while already in a trade. The per-ms view differences consecutive average returns and divides by the interval length. It measures how quickly additional return accumulates. The Hawkes exponential half-life measures decay in arrival intensity. Overlapping windows make individual observations dependent.
- **Clocks and execution.** Model a strategy at the SPY capture location. Delay ES observation by the feed setting and apply the order-route setting to both SPY orders. Nasdaq capture time approximates the order-arrival clock. Use the prevailing displayed ask to buy and bid to sell. At most one one-share position or entry order may be outstanding. Timed exits cross the spread. In passive mode, join behind the displayed size, credit only later opposite-side prints at the posted price, and expire after 5 ms. Cancel on loss of the price level, including ambiguous same-timestamp level changes. Quote changes from cancellations do not advance the simulated order. Actual queue position, hidden orders, and venue acknowledgments are unobserved in MBP-1.
- **Costs.** Gross P&L already includes the spread through execution prices. Net subtracts fees per share per side and the chosen impact allowance in bp of each fill. Impact is a user-set sensitivity assumption. The simulator does not feed its hypothetical orders back into the market. Fees and latency defaults are illustrative. SPY quotes cover Nasdaq alone.

Run `python study.py research` to regenerate the historical Hawkes parameters and full trade ledger under `results/20250204_1500-1530Z_mbp-1/`. Run `python portable_demo.py` to regenerate the offline HTML under `results/`. Run `python -m unittest -v` to verify event timing, likelihood integration, queue priority assumptions and cost accounting.

Model reference: [Bacry, Mastromatteo & Muzy, Hawkes Processes in Finance](https://arxiv.org/abs/1502.04592).

## First session

February 4, 2025, 10:00–10:30 a.m. New York time (15:00–15:30 UTC).

| Symbol | Instrument | Feed |
| --- | --- | --- |
| ESH5 | March 2025 E-mini S&P 500 futures contract | CME Globex, GLBX.MDP3 |
| SPY | SPDR S&P 500 ETF, Nasdaq venue quotes | Nasdaq TotalView, XNAS.ITCH |

Both requests use MBP-1. The files retain exchange event time, feed receive time, prices, sizes and the other original CSV fields. Timestamps are integer nanoseconds and prices use the original fixed-point scale of one billion units per price unit.

## Run on Windows

Use Python 3.11 or later. The acquisition, replay and midpoint response commands use the standard library. Open PowerShell in the project folder.

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

Replay reads both files locally, merges them by capture receive timestamp, prints the first three valid two-sided quotes from each feed and counts every record. It preserves source order within each feed. Equal timestamps across feeds use the input order for display. The capture points are in different locations. A later execution simulator must model when both feeds reach a common strategy location. The event study below uses the same receive-time clock.

## Measure the lead and lag

Run `python study.py analyze` after downloading the session. It writes `results/20250204_1500-1530Z_mbp-1/response.csv`. Run `python -m unittest -v` for timing and quote-handling checks. To regenerate the accompanying figure, use `python plot_response.py` in an environment with matplotlib installed.

Each change in a source midpoint triggers one observation, weighted equally regardless of size. For each feed, use the final completed event (F_LAST) at a given receive timestamp. A usable quote has positive sizes and prices on both sides and bid at or below ask. An invalid quote interrupts the series. The first quote after an interruption establishes a fresh baseline.

At trigger time t, take the most recent target quote at or before t. Repeat at t + h. The post-event response in basis points is 10,000 times the target percentage change expressed as a fraction, multiplied by +1 for a source uptick or -1 for a downtick. The pre-event column applies the same rule from t - h to t. An update exactly at t is already in the baseline. An unchanged target contributes zero. Each horizon uses the same triggers with a full second of target coverage on either side and no intervening invalid state.

The CSV also reports the percentage of all triggers followed by a same-direction or unchanged target midpoint, and the number of five-minute trigger-time blocks with a positive average post-event response. Windows may overlap. The six block signs summarize consistency within this session and do not establish statistical significance.

Provider references: [historical API](https://databento.com/docs/api-historical), [cost estimates](https://databento.com/docs/api-historical/metadata/metadata-get-cost), [MBP-1 fields](https://databento.com/docs/schemas/mbp-1).
