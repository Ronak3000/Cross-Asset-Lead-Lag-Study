import React,{useEffect,useState} from "react";
import {Card,Plot,mint,lilac} from "./charts";
import {cash,number,iso,tickData,exportCsv} from "./data";

export function Model({session}) {
  const m=session.model;
  return <><Card label="TRADE ARRIVALS" title="Excitation matrix" foot="Each cell estimates the integrated response of a row’s trade stream to a single event in the column’s stream.">
    <Plot id="matrix" traces={[{type:"heatmap",x:m.streams,y:m.streams,z:m.kernel_mass,texttemplate:"%{z:.3f}",zmin:0,showscale:false,
      colorscale:[[0,"#192233"],[.45,"#356d70"],[1,"#51b8a9"]],textfont:{color:"white"},hovertemplate:"%{x} → %{y}<br>Kernel mass %{z:.4f}<extra></extra>"}]}
      extra={{hovermode:"closest"}} xaxis={{title:{text:"Triggering stream"}}} yaxis={{autorange:"reversed",title:{text:"Responding stream"}}}/></Card>
    <Card title="Fit diagnostics"><dl>{[["Training window","First 20 minutes"],["Evaluation window","Final 10 minutes"],["Selected half-life",m.half_life_ms+" ms"],
      ["Spectral radius",m.spectral_radius.toFixed(3)],["Training arrivals",number(session.benchmarks.train_arrivals)],["Evaluation arrivals",number(session.benchmarks.test_arrivals)]
    ].map(([k,v])=><div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl></Card></>;
}

export function Benchmarks({session}) {
  const b=session.benchmarks;
  return <><Card label="MODEL ABLATION" title="Does cross-asset history help?" foot="Each Hawkes model selects its own half-life on the first 20 minutes. All three scores use the same final ten minutes.">
    <p className="insight"><strong>{b.incremental_gain>=0?"+":""}{b.incremental_gain.toFixed(4)}</strong> nats per held-out arrival from including ES–SPY interactions.</p>
    <div className="tablewrap"><table><thead><tr><th>Arrival model</th><th>Half-life</th><th>Test log likelihood</th><th>Gain vs Poisson¹</th></tr></thead><tbody>{b.models.map(m=><tr key={m.name}><td>{m.name}</td><td>{m.half_ms?m.half_ms+" ms":"—"}</td><td>{number(Math.round(m.test_ll))}</td><td>{m.gain.toFixed(4)}</td></tr>)}</tbody></table></div>
    <div className="note">¹ Nats per event across {number(b.test_arrivals)} signed arrivals. Higher scores mean better arrival-time predictions.</div></Card>
    <Card label="EXECUTION SENSITIVITY" title="Latency, fees and fills" foot="One share per trade. Fixed scenarios use 0.5 ms order routing, a 50 ms hold and $0.003 per side. The active configuration can be tested separately.">
      <div className="tablewrap"><table><thead><tr><th>Experiment</th><th>Trades</th><th>Net P&amp;L</th><th>Net / trade</th></tr></thead><tbody>{b.scenarios.map(r=><tr key={r.name}><td>{r.name}</td><td>{number(r.trades)}</td><td className={r.net<0?"negative":""}>{cash(r.net)}</td><td>{r.net_per_trade==null?"—":r.net_per_trade.toFixed(4)}</td></tr>)}</tbody></table></div></Card>
    <Card title="Warm replay benchmark"><p className="insight"><strong>{b.runtime.median_ms.toFixed(1)} ms</strong> median simulation time across five measured runs.</p><p className="note">Python {b.runtime.python} · {b.runtime.platform}. Inputs and fitted parameters were in memory. File reads, fitting, network and rendering are excluded.</p></Card></>;
}

export function Fills({session,result}) {
  const [index,setIndex]=useState(0),[quotes,setQuotes]=useState(null),[error,setError]=useState("");
  const rows=result.ledger,trade=rows[index]||rows[0];
  useEffect(()=>{let active=true;setQuotes(null);setError("");
    if(trade)tickData(trade.signal_s).then(v=>{if(active)setQuotes(v);}).catch(e=>{if(active)setError(e.message);});
    return ()=>{active=false;};},[trade]);
  const traces=(quotes||[]).map((pts,i)=>{const base=pts.find(p=>p[1]!=null)?.[1];
    return {type:"scatter",mode:"lines",name:i?"SPY":"ESH5",line:{color:i?lilac:mint,shape:"hv"},x:pts.map(p=>(p[0]-trade.signal_s)*1000),
      y:pts.map(p=>p[1]&&base?(p[1]/base-1)*10000:null)};});
  const marks=trade?[[0,"Signal"],[(trade.entry_s-trade.signal_s)*1000,"Entry"],[(trade.exit_s-trade.signal_s)*1000,"Exit"]].filter(([x])=>x<=100):[];
  return <><Card label="ORDER REPLAY" title="Execution log" action={<button disabled={!rows.length} onClick={()=>exportCsv(rows)}>Export CSV ↓</button>}
    foot={rows.length?"Select a trade to inspect its quote path. Export includes all "+number(rows.length)+" round trips.":"No completed trades for these settings."}>
    <div className="tablewrap scrolling"><table><thead><tr><th>Entry UTC</th><th>Side</th><th>Entry $</th><th>Exit $</th><th>Net $</th></tr></thead><tbody id="fillsBody">{rows.slice(0,100).map((r,i)=>
      <tr className={"selectable "+(r===trade?"selected":"")} key={r.signal_s} tabIndex={0} onClick={()=>setIndex(i)} onKeyDown={e=>{if(e.key==="Enter")setIndex(i);}}>
        <td>{iso(session.start,r.entry_s).slice(11,23)}</td><td className={r.side==="LONG"?"positive":"negative"}>{r.side}</td>
        <td>{r.entry.toFixed(2)}</td><td>{r.exit.toFixed(2)}</td><td className={r.net<0?"negative":"positive"}>{r.net.toFixed(3)}</td></tr>)}</tbody></table></div></Card>
    <Card title="Tick inspector" foot={trade?"Capture-time quotes around the selected signal. ES is mint and SPY is violet.":"Run a scenario with completed trades to inspect ticks."}>
      {error?<p role="alert">{error}</p>:quotes?<Plot id="detail" small traces={traces} xaxis={{title:{text:"Milliseconds from signal"}}} yaxis={{title:{text:"Basis points"}}}
        extra={{shapes:marks.map(([x])=>({type:"line",x0:x,x1:x,yref:"paper",y0:0,y1:1,line:{color:"#76869b",dash:"dot",width:1}})),
        annotations:marks.map(([x,text],i)=>({x,text,yref:"paper",y:i===1?.82:1,showarrow:false}))}}/>:null}</Card></>;
}
