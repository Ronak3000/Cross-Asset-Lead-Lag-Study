import React, {useMemo, useState} from "react";
import {Card, Plot, lilac, mint} from "./charts";
import {cash} from "./data";
import {replaySpread} from "./kalman-model.mjs";
import pairs from "./kalman-snapshot.json";

const source = "https://github.com/Ronak3000/alpha-research-kalman";
const dateAxis = {type:"date", tickformat:"%b %Y"};

function trace(name, dates, values, color) {
  return {type:"scatter", mode:"lines", name, x:dates, y:values, line:{color, width:1.6}};
}

export function KalmanStudy() {
  const [pair,setPair] = useState("PEP/KO");
  const {dates, spread, beta, target, reference, targetName, referenceName} = pairs[pair];
  const hedgeUnits = `${reference} shares per ${target} share`;
  const [days,setDays] = useState(30);
  const [entry,setEntry] = useState(2);
  const result = useMemo(() => replaySpread(spread, days, entry), [spread, days, entry]);
  const guides = [-entry, entry].map(y => ({
    type:"line", xref:"paper", x0:0, x1:1, y0:y, y1:y, line:{color:lilac, dash:"dot", width:1}
  }));
  return <main>
    <section className="heading"><div><h1>Kalman <span>pairs trading</span></h1>
      <p>How does the hedge ratio between {targetName} ({target}) and {referenceName} ({reference}) change over time?</p>
      <p>{dates.length.toLocaleString()} paired daily adjusted closes · {dates[0]} to {dates.at(-1)}</p>
    </div><label className="session-select">Stock pair
      <select value={pair} onChange={e=>setPair(e.target.value)}>{Object.keys(pairs).map(key=><option key={key} value={key}>{key.replace("/", " / ")}</option>)}</select>
    </label></section>
    <div className="work kalman-work"><div className="views">
      <Card title={`${target} hedge ratio`} foot={`The filter updates the intercept and slope after each close. The slope estimates the number of ${hedgeUnits} in the hedge.`}>
        <Plot id="kalman-hedge" traces={[trace("Hedge ratio", dates, beta, mint)]} xaxis={dateAxis} yaxis={{title:{text:hedgeUnits}}}/>
      </Card>
      <Card title="Spread z-score" foot={`Dotted lines mark the ±${entry.toFixed(1)} entry thresholds. A positive extreme shorts the spread, a negative extreme buys it, and |z| below 0.5 closes the position.`}>
        <Plot id="kalman-z" small traces={[trace("Spread z-score",dates,result.z,lilac)]} xaxis={dateAxis} yaxis={{title:{text:"Standard deviations"}}} extra={{shapes:guides}}/>
      </Card>
      <Card title="Cumulative spread P&L" foot="The original strategy applies yesterday’s position to the change in the fitted residual. A changing hedge ratio can move that residual even with fixed prices. This curve therefore measures a model-based proxy for trading returns.">
        <Plot id="kalman-net" small traces={[trace("Net spread P&L", dates, result.cumulative, mint)]} xaxis={dateAxis} yaxis={{title:{text:"Spread P&L ($)"}}}/>
      </Card>
    </div><aside>
      <Card title="Signal settings"><div className="kalman-settings">
        <label>Lookback <strong>{days} sessions</strong><input type="range" min="10" max="60" step="1" value={days} onChange={e=>setDays(Number(e.target.value))}/></label>
        <label>Entry threshold <strong>±{entry.toFixed(1)} σ</strong><input type="range" min="1" max="3" step="0.1" value={entry} onChange={e=>setEntry(Number(e.target.value))}/></label>
        <button onClick={()=>{setDays(30);setEntry(2);}}>Reset settings</button>
      </div><dl aria-live="polite"><div><dt>Net spread P&L</dt><dd>{cash(result.cumulative.at(-1))}</dd></div>
        <div><dt>Position units traded</dt><dd>{result.turnover}</dd></div></dl></Card>
      <Card title="Method &amp; source"><p className="note">Each daily spread is {target}'s adjusted close minus its fitted value using {reference}. Positions carry forward between signals. Each unit of position change costs $0.005.</p>
        <div className="downloads"><a href={source}>Original Python project</a></div></Card>
    </aside></div>
  </main>;
}
