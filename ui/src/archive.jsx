import React, {useEffect, useState} from "react";
import {Card, Plot, Segments, mint, lilac} from "./charts";
import {Benchmarks, Model} from "./research";
import {cash, exportCsv, number} from "./data";

const base = new URL("archive/", document.baseURI);
const pageSize = 50;
const views = ["Overview", "Arrivals", "Benchmarks", "Executions", "Market records"];

async function read(url, signal) {
  const response = await fetch(url, {signal});
  if (!response.ok) throw new Error("Could not load " + new URL(url).pathname);
  return response;
}

function useFile(url, load) {
  const [state, set] = useState({});
  useEffect(() => {
    const controller = new AbortController();
    load(url, controller.signal).then(data => {
      if (!controller.signal.aborted) set({url, data});
    }).catch(error => {
      if (!controller.signal.aborted) set({url, error: error.message});
    });
    return () => controller.abort();
  }, [url, load]);
  return state.url === url ? state : {};
}

const json = async (url, signal) => (await read(url, signal)).json();
async function reports(folder, signal) {
  const [model, benchmarks, result, candles] = await Promise.all(
    ["hawkes.json", "benchmarks.json", "backtest.json", "candles.json"].map(file => json(folder + file, signal))
  );
  return {model, benchmarks, result, candles};
}

function Pager({page, setPage, count}) {
  const pages = Math.ceil(count / pageSize);
  return <div className="pager">
    <span>{number(page * pageSize + 1)}–{number(Math.min(count, (page + 1) * pageSize))} of {number(count)}</span>
    <button disabled={!page} onClick={() => setPage(page - 1)}>Previous</button>
    <label>Page <input type="number" min="1" max={pages} value={page + 1}
      onChange={e => {const n = e.target.valueAsNumber; if (Number.isInteger(n) && n >= 1 && n <= pages) setPage(n - 1);}}/></label>
    <button disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}>Next</button>
  </div>;
}

function Grid({columns, rows}) {
  return <div className="tablewrap scrolling"><table><thead><tr>{columns.map(c => <th key={c}>{c}</th>)}</tr></thead>
    <tbody>{rows.map((row,i) => <tr key={i}>{row.map((v,j) => <td key={j}>{v}</td>)}</tr>)}</tbody></table></div>;
}

async function lines(url, signal) {
  const blob = await (await read(url, signal)).blob();
  const data = new Response(blob.stream().pipeThrough(new DecompressionStream("gzip")));
  return (await data.text()).trimEnd().split(/\r?\n/);
}

function splitCsv(line) {
  // Databento fields are single-line CSV; retain nanosecond integers as strings.
  return Array.from(line.matchAll(/(?:^|,)("(?:[^"]|"")*"|[^,]*)/g),
    m => m[1].startsWith('"') ? m[1].slice(1,-1).replaceAll('""','"') : m[1]);
}

function RawFeed({feed, folder}) {
  const [page, setPage] = useState(0), [progress, setProgress] = useState(""), [busy, setBusy] = useState(false);
  const first = page * pageSize, chunk = Math.floor(first / feed.chunk_rows);
  const {data, error} = useFile(folder + feed.chunks[chunk], lines);
  const offset = first % feed.chunk_rows + (chunk === 0 ? 1 : 0);
  async function download() {
    setBusy(true);
    try {
      const parts = [];
      for (const [i, name] of feed.chunks.entries()) {
        setProgress("Downloading part " + (i+1) + " of " + feed.chunks.length);
        parts.push(await (await read(folder + name)).blob());
      }
      const url = URL.createObjectURL(new Blob(parts, {type:"application/gzip"}));
      const link = document.createElement("a");
      link.href = url; link.download = feed.symbol + ".csv.gz"; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 10000); setProgress("");
    } catch(e) {setProgress(e.message);} finally {setBusy(false);}
  }
  return <Card title={feed.symbol + " · MBP-1 records"} action={<button disabled={busy} onClick={download}>Download full CSV.gz</button>}
    foot={"Original CSV SHA-256 · " + feed.sha256}>
    <Pager page={page} setPage={setPage} count={feed.rows}/>
    <div role="status">{progress}</div>
    {data ? <Grid columns={feed.columns} rows={data.slice(offset, offset + pageSize).map(splitCsv)}/> : <p className="note">{error || "Loading records…"}</p>}
  </Card>;
}

function Executions({result}) {
  const [page, setPage] = useState(0), [fee,setFee] = useState(result.settings.fee);
  const ledger = result.ledger, keys = Object.keys(ledger[0] || {});
  const repriced = result.net - 2 * (fee - result.settings.fee) * ledger.length;
  return <><Card title="Execution cost sensitivity" foot="One SPY share per round trip. Repricing holds recorded fills and impact fixed.">
    <div className="pager"><label>Fee per side ($) <input type="number" min="0" max="0.1" step="0.001" value={fee}
      onChange={e=>{const n=e.target.valueAsNumber;if(n>=0 && n<=0.1)setFee(n);}}/></label><strong>Repriced net {cash(repriced)}</strong></div></Card>
    <Card title="Simulated round trips" action={<button onClick={()=>exportCsv(ledger)}>Export all trades</button>}
      foot="Times are seconds from session start. Entry and exit are simulated fill prices in USD.">
      {ledger.length > 0 && <Pager page={page} setPage={setPage} count={ledger.length}/>}
      <Grid columns={keys} rows={ledger.slice(page*pageSize,(page+1)*pageSize).map(row=>keys.map(k=>typeof row[k]==="number"?Number(row[k].toFixed(9)):row[k]))}/>
    </Card></>;
}

function Overview({session, data, folder}) {
  const [symbol,setSymbol]=useState(session.contract);
  const bars=data.candles[symbol];
  return <><Card label="HISTORICAL REPLAY" title="Midpoint candles" action={<Segments label="Instrument" value={symbol} onChange={setSymbol} items={session.feeds.map(f=>[f.symbol,f.symbol])}/>}
    foot="One-second OHLC of observed midpoint updates. Drag to zoom. Double-click to reset.">
    <Plot id="archive-candles" traces={[{type:"candlestick",name:symbol,x:bars.map(b=>new Date(b[0]*1000).toISOString()),
      ...Object.fromEntries(["open","high","low","close"].map((k,i)=>[k,bars.map(b=>b[i+1])])),
      increasing:{line:{color:mint}},decreasing:{line:{color:"#fc929e"}}}]} xaxis={{type:"date",rangeslider:{visible:false},title:{text:"UTC"}}} yaxis={{title:{text:"Midpoint (USD)"}}}/></Card>
    <Card title="Which instrument moved first?" action={<a href={folder+"response.csv"} download>Response CSV</a>}
      foot="Mean signed target midpoint change after a source move, using feed receive times. Each curve includes ten horizons.">
      <Plot id="archive-response" traces={session.feeds.map((f,i)=>{
        const rows=session.responses.filter(r=>r.source===f.symbol);
        return {type:"scatter",mode:"lines+markers",name:f.symbol+" → "+rows[0].target,x:rows.map(r=>+r.horizon_ms),y:rows.map(r=>+r.post_bps),line:{color:i?lilac:mint}};
      })} extra={{showlegend:true,legend:{orientation:"h"}}} xaxis={{type:"log",title:{text:"Horizon (ms)"}}} yaxis={{title:{text:"Signed response (bp)"}}}/>
    </Card></>;
}

function Historical({session, sessions, select, view}) {
  const folder = new URL(session.id + "/", base).href;
  const {data,error}=useFile(folder,reports);
  const [symbol,setSymbol]=useState(session.contract);
  const feed=session.feeds.find(f=>f.symbol===symbol);
  return <main><section className="heading"><div><div className="eyebrow">HISTORICAL RESEARCH</div><h1>Cross-asset <span>lead–lag</span></h1>
    <p>{session.contract} futures and Nasdaq SPY · 10:00–10:30 New York</p></div>
    <label className="session-select">Research session<select value={session.id} onChange={e=>select(e.target.value)}>{sessions.map(s=><option key={s.id} value={s.id}>{s.date} · {s.contract}</option>)}</select></label></section>
    {!data ? <p role="status">{error||"Loading session…"}</p> : <>
      <div className="stats">{[["Market records",number(session.feeds.reduce((n,f)=>n+f.rows,0))],["Simulated trades",number(data.result.trades)],
        ["Gross P&L",cash(data.result.gross)],["Net P&L",cash(data.result.net)]].map(([k,v])=><div className="metric" key={k}><label>{k}</label><strong className={v.startsWith("-")?"negative":""}>{v}</strong></div>)}</div>
      {view==="Overview"&&<Overview session={session} data={data} folder={folder}/>}
      {view==="Arrivals"&&<Model session={data}/>}
      {view==="Benchmarks"&&<Benchmarks session={data}/>}
      {view==="Executions"&&<Executions result={data.result}/>}
      {view==="Market records"&&<><div className="pager"><Segments label="Feed" value={symbol} onChange={setSymbol} items={session.feeds.map(f=>[f.symbol,f.symbol])}/></div><RawFeed key={symbol} feed={feed} folder={folder}/></>}
      <div className="downloads"><strong>Session files</strong>{["response.csv","hawkes.json","benchmarks.json","backtest.json","candles.json"].map(f=><a key={f} href={folder+f} download>{f}</a>)}</div>
    </>}</main>;
}

export function Archive({onSimulator}) {
  const {data:sessions,error}=useFile(new URL("sessions.json", base).href,json);
  const [id,select]=useState(""),[view,setView]=useState("Overview");
  const session=sessions?.find(s=>s.id===id)||sessions?.[0];
  return <><header><div className="brand"><span className="brandmark" aria-hidden="true"><i/><i/><i/></span>Phase</div>
    <nav aria-label="Historical research">{views.map(v=><button key={v} aria-current={view===v?"page":undefined} onClick={()=>setView(v)}>{v}</button>)}</nav>
    {!window.PHASE_STATIC&&<button onClick={onSimulator}>Simulator</button>}</header>
    {session?<Historical key={session.id} session={session} sessions={sessions} select={select} view={view}/>:<main role="status">{error||"Loading historical sessions…"}</main>}</>;
}
