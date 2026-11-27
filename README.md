# Cross-Asset Lead–Lag Arbitrage Using Hawkes Processes

A local research terminal for comparing ES futures and SPY, modelling signed trade arrivals, and testing whether a short-lived price gap survives routing latency, the bid–ask spread and fees.

## Historical dashboard

[Open the published historical dashboard](https://phase-es-spy-research.mysticmill6.chatgpt.site)

The local dashboard lets you switch between three recorded 10:00–10:30 New York sessions. **Overview** charts one-second midpoint candles and the two directional response curves. **Arrivals** and **Benchmarks** show the fitted model and held-out comparisons. **Executions** includes each simulated round trip and a fee sensitivity control. **Market records** pages through the original Databento fields and downloads the complete feed as a gzip-compressed CSV. The FastAPI dashboard also offers the execution simulator.

| Session | Futures records | SPY records | Simulated trades | Net simulated P&L |
| --- | ---: | ---: | ---: | ---: |
| 2025-02-04 · ESH5 | 565,130 | 216,110 | 1,230 | −$34.06 |
| 2026-11-23 · ESZ6 | 1,802,570 | 526,742 | 4,033 | −$185.50 |
| 2026-11-25 · ESZ6 | 2,180,854 | 645,952 | 4,145 | −$207.12 |

The dashboard reads the versioned files under `archive/`. Each session includes model parameters, all benchmark scenarios, the backtest with its full ledger, midpoint candles and the event-study CSV. Gzip members reconstruct each original feed in manifest order. The manifest includes the uncompressed SHA-256 for each CSV. Run `python publish_records.py` to rebuild the archive from the matching local `data/` and `results/` directories.

## Open the terminal

In the downloaded project bundle, open **Phase-demo.html** directly in Chrome or Edge for a portable synthetic presentation. This version has three precomputed execution scenarios. You can switch scenarios, inspect trades, and recalculate fees and impact in the browser. The synthetic generator intentionally plants a futures lead. Only the Python terminal reads the historical files and runs new execution paths.

For the historical terminal, open PowerShell in the original project directory (the one containing your downloaded `data` folder).

```powershell
python -m pip install -r requirements.txt
python study.py dashboard
```

Open http://127.0.0.1:8765 after the fit finishes. To use another port, add `--port 8766`. Stop the server with Ctrl+C. To demonstrate the full engine on another machine without market data, use `python study.py dashboard --synthetic`. Both versions work offline once dependencies are installed.

## Develop with React hot reload

Open two PowerShell terminals in the project root. Use Node.js 22.12 or newer for the frontend.

**Terminal 1** starts the FastAPI backend on port 8765 using the project's Python environment.

```powershell
.\.venv\Scripts\python.exe study.py dashboard
```

**Terminal 2** starts Vite and React Fast Refresh. Run `npm ci` on first setup and when the lockfile changes.

```powershell
cd ui
npm ci
npm run dev
```

Open http://127.0.0.1:5173 and edit the JSX in `ui/src/`. Vite forwards `/api` and `/plot.js` to the local backend. For a generated session, add `--synthetic` to the backend command.

## Host an interactive demo on Render Free

### Split deployment with a Vercel frontend

1. Push the deployment files to GitHub. In [Vercel](https://vercel.com/new), import this repository under your personal Hobby account. Use the repository root (`.`) and the **Other** framework preset. Leave install, build and output overrides off. Click **Deploy** with `RENDER_API_ORIGIN` unset to publish all three historical sessions immediately.
2. In [Render](https://dashboard.render.com/), choose **New → Blueprint**, connect the repository, select `main` and apply the root `render.yaml` on the **Free** plan. Once the service is live, open `/api/session` at its public URL and look for the JSON field `synthetic` set to `true`.
3. In the Vercel project's **Settings → Environment Variables**, add `RENDER_API_ORIGIN` for Production and, if desired, Preview. Use the actual HTTPS Render origin without a path. Redeploy the frontend with that variable to enable the simulator.
4. Open the Vercel URL. In **Overview**, switch between the three historical dates. In **Market records**, choose SPY and page through the quotes. In **Simulator**, select **Run backtest** to exercise the Render API. The historical pages, Plotly and all archived files load from Vercel. Only the simulator calls Render through the same-origin `/api/*` proxy. Both hosts work without a Databento key.

For a local check of the static files, run `npm ci --prefix ui --include=dev`, then `npm run build:vercel --prefix ui` and `python -m http.server 8080 --directory .vercel/output/static` from the repository root. Open `http://localhost:8080`. The Python static server serves the archive. Vercel applies the production proxy rules in `.vercel/output/config.json` at deployment.

### Single-service deployment

The repository includes `render.yaml` for one free Python web service. After the deployment files and current frontend and backend are on your GitHub branch, use **New → Blueprint** in Render, connect that branch, and verify the **Free** plan before applying. The build installs Python and npm dependencies and compiles React. Uvicorn serves both React and FastAPI at the resulting URL, using a seeded synthetic session. Visitors can change the strategy settings and run a fresh simulation without credentials.

The free instance sleeps after 15 minutes of inactivity. Open the demo in advance of an interview to allow time for the instance to wake and the model to fit. Render's included instance hours, bandwidth and build minutes apply. [Free service details](https://render.com/docs/free).

## FastAPI backend

The dashboard command starts both the API and the React client. After the session is ready, open [the dashboard](http://127.0.0.1:8765/) or [Swagger UI](http://127.0.0.1:8765/docs). The OpenAPI schema is available at `/openapi.json`. Swagger UI loads its documentation assets from a CDN. The dashboard serves its scripts locally.

| Request | Purpose |
| --- | --- |
| `GET /api/session` | Load the fitted model, benchmarks, replay bars and default backtest. |
| `POST /api/run` | Rerun the simulation with a JSON configuration. Omitted fields use the simulator defaults. |
| `GET /api/detail?t=1201` | Inspect quotes around a signal, in seconds from the beginning of the session. |

To launch the historical API directly, use `python -m uvicorn api:create_app --factory --host 127.0.0.1 --port 8765`. Both entry points load the session once per server process. In PowerShell, try changing the per-side fee while the server is running.

```powershell
$result = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8765/api/run -ContentType application/json -Body '{"fee":0.01}'
$result | Select-Object trades, net
```

## React dashboard and benchmarks

The browser UI uses React 19 and Plotly. FastAPI serves the compiled client and its JSON API on the same local port through Uvicorn. Use `npm run dev` from `ui/` while editing. Run `npm run build --prefix ui` to refresh the compiled client for the single-server demo. The committed production bundle lets a fresh Python installation start the dashboard without a Node build. On a fresh checkout, `python portable_demo.py` creates `results/Phase-demo.html` with embedded scripts and synthetic data.

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

To repeat the comparison for November 23, 2026, run the following from the project folder:

```powershell
.\.venv\Scripts\python.exe study.py repeat --date 2026-11-23 --contract ESZ6 --max-estimate 0.50
```

Enter your key at the hidden terminal prompt. The command targets 10:00–10:30 New York time. It waits for the window to close and for both MBP-1 feeds to cover it under your account, then requests a cost estimate. The optional estimate limit authorizes the missing downloads only if the combined estimate is within the limit. Omit the limit to confirm interactively. Use Ctrl+C to stop waiting. Completed files are reused on the next run. The command writes the new session to its own directory, calculates the full response curve and prints both directions at 5 ms alongside the February baseline.

### Baseline window

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
