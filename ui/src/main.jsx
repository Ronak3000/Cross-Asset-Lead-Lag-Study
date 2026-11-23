import React,{useEffect,useRef,useState} from "react";
import {createRoot} from "react-dom/client";
import {Markets} from "./charts";
import {Benchmarks,Fills,Model} from "./research";
import {cash,demo,loadSession,number,simulate} from "./data";

const tabs={market:"Market replay",model:"Hawkes model",fills:"Executions",bench:"Benchmarks"};
const fields=[["feed_ms","ES feed","ms",0,100,.1],["order_ms","Order route","ms",0,100,.1],["hold_ms","Hold time","ms",1,1000,1],
  ["threshold_bp","Gap threshold","bp",.01,10,.01],["fee","Fee per side","USD",0,.1,.001],["impact_bp","Impact per side","bp",0,10,.01]];
function Spark({values,purple=false}){
  const width=114,height=29,min=Math.min(...values),range=Math.max(...values)-min||1;
  const d=values.map((v,i)=>(i?"L":"M")+(i*width/(values.length-1||1)).toFixed(1)+","+(height-2-(height-4)*(v-min)/range).toFixed(1)).join(" ");
  return <svg aria-hidden="true" viewBox={"0 0 "+width+" "+height} className={"spark "+(purple?"violet":"")}><path d={d}/></svg>;
}
function Stats({session,result}){
  return <div className="stats">{session.bars.map((bars,i)=>{const close=bars.at(-1)[4],bp=10000*(close/bars[0][4]-1);
    return <div className="metric instrument" key={i}><label><i className={i?"dot violet":"dot"}/>{i?"SPY":"ESH5"} <small>{i?"NASDAQ":"CME"}</small></label><strong>{number(Number(close.toFixed(3)))}</strong>
      <div className="metricbottom"><small>{bp.toFixed(2)} bp · window</small><Spark purple={!!i} values={bars.filter((_,j)=>j%5===0||j===bars.length-1).map(p=>p[4])}/></div></div>;})}
    <div className="metric"><label>Net P&amp;L</label><strong id="net" className={result.net<0?"negative":"positive"}>{cash(result.net)}</strong><small>{cash(result.gross)} before fees &amp; impact</small></div>
    <div className="metric"><label>Closed round trips</label><strong id="count">{number(result.trades)}</strong><small>{number(result.attempts)} attempted entries</small></div></div>;
}
function Controls({session,onRun,busy}){
  const defaults=session.result.settings;
  const [form,setForm]=useState(defaults),[scenario,setScenario]=useState(0);
  const set=(key,value)=>setForm(old=>({...old,[key]:value}));
  function submit(e){e.preventDefault();const config={...form};for(const [name] of fields)config[name]=Number(config[name]);onRun(config,scenario);}
  function reset(){setForm(defaults);setScenario(0);onRun(defaults,0);}
  return <form onSubmit={submit} className="panel controls"><div className="confighead"><span className="eyebrow"><i className="dot"/> SIMULATOR</span><h2>Execution settings</h2></div>
    <fieldset disabled={busy}>{demo&&<label>Recorded scenario<select value={scenario} onChange={e=>{const i=Number(e.target.value);setScenario(i);setForm({...demo.runs[i].result.settings});}}>{demo.runs.map((r,i)=><option value={i} key={i}>{r.label}</option>)}</select></label>}
    <label>Entry style<select disabled={!!demo} name="style" value={form.style} onChange={e=>set("style",e.target.value)}><option value="market">Marketable order</option><option value="passive">Passive · join best quote</option></select></label>
    <div className="fieldgrid">{fields.map(([k,title,unit,min,max,step])=><label key={k}>{title}<span className="inputbox"><input name={k} type="number" required min={min} max={max} step={step} disabled={!!demo&&!["fee","impact_bp"].includes(k)}
      value={form[k]} onChange={e=>set(k,e.target.value)}/><b>{unit}</b></span></label>)}</div>
    <label className="toggle"><span>Hawkes direction filter</span><input type="checkbox" name="filter_flow" disabled={!!demo} checked={form.filter_flow} onChange={e=>set("filter_flow",e.target.checked)}/></label>
    <button className="run" id="run" type="submit">{busy?"Replaying…":demo?"Reprice scenario":"Run backtest"} <span>↗</span></button>
    <button className="reset" type="button" onClick={reset}>Restore defaults</button></fieldset>
    <div className="foot">{demo?"Three recorded synthetic runs. Fees and impact are recalculated in your browser.":"One SPY share per position. ES supplies the signal. Evaluation uses the final ten minutes."}</div></form>;
}
function App(){
  const [session,setSession]=useState(null),[result,setResult]=useState(null),[tab,setTab]=useState("market"),
    [status,setStatus]=useState(""),[busy,setBusy]=useState(false);
  const running=useRef(false);
  useEffect(()=>{loadSession().then(s=>{setSession(s);setResult(s.result);}).catch(e=>setStatus(e.message));},[]);
  async function run(config,scenario){if(running.current)return;running.current=true;setBusy(true);setStatus("");
    try{const r=await simulate(config,scenario);setResult(r);setStatus("Replay complete · "+number(r.signals)+" signals · "+number(r.missed)+" missed entries · "+r.unclosed+" open at end");}
    catch(e){setStatus(e.message);}finally{running.current=false;setBusy(false);}}
  return <><header><div className="brand"><span className="brandmark" aria-hidden="true"><i/><i/><i/></span>Phase<span className="wordmark">/ terminal</span></div>
    <nav aria-label="Research views">{Object.entries(tabs).map(([id,name])=><button key={id} data-tab={id} aria-current={tab===id?"page":undefined} onClick={()=>setTab(id)}>{name}</button>)}</nav>
    <span className="connection"><i className="dot"/>{session?.synthetic?"Synthetic demo":"Historical replay"}</span></header>
    {session?<main><section className="heading"><div><div className="eyebrow"><b className="shortline"/> MICROSTRUCTURE RESEARCH</div>
      <h1>Cross-asset <span>lead–lag</span></h1><p>E-mini S&amp;P 500 futures <b>×</b> SPDR S&amp;P 500 ETF</p></div><div className="date"><label>REPLAY WINDOW</label>
        <strong>{session.synthetic?"Generated session":"04 FEB 2025"}</strong><small>15:20 — 15:30 UTC</small></div></section>
    <Stats session={session} result={result}/><div className="work"><div className="views">{tab==="market"?<Markets session={session} result={result}/>:tab==="model"?<Model session={session}/>:tab==="bench"?<Benchmarks session={session}/>:<Fills session={session} result={result}/>}</div>
    <aside><Controls session={session} onRun={run} busy={busy}/><div role="status" id="status">{status}</div></aside></div></main>:<main role="status">{status||"Loading session…"}</main>}</>;
}
createRoot(document.getElementById("root")).render(<App/>);
