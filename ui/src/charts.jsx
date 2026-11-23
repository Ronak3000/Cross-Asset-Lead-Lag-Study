import React,{useEffect,useRef,useState} from "react";
import {iso} from "./data";
export const mint="#55e4c3", lilac="#b396ff", red="#fc929e";
const axis={gridcolor:"#202b39",zerolinecolor:"#445164",nticks:6,automargin:true,showspikes:true,spikethickness:1,spikecolor:"#9baabd"};
export function Plot({id,traces,xaxis={},yaxis={},extra={},small=false}) {
  const el=useRef(null);
  useEffect(()=>{
    const node=el.current;
    Plotly.react(node,traces,{paper_bgcolor:"transparent",plot_bgcolor:"transparent",font:{family:"Inter, Segoe UI, sans-serif",color:"#94a5b9",size:11},
      showlegend:false,margin:{l:51,r:20,t:15,b:41},hovermode:"x unified",hoverlabel:{bgcolor:"#253044",font:{color:"white"}},
      xaxis:{...axis,...xaxis},yaxis:{...axis,...yaxis},...extra},{displayModeBar:false,responsive:true,scrollZoom:true});
  },[traces,xaxis,yaxis,extra]);
  useEffect(()=>{const node=el.current;const obs=new ResizeObserver(()=>{if(node.data)Plotly.Plots.resize(node);});obs.observe(node);
    return ()=>{obs.disconnect();Plotly.purge(node);};},[]);
  return <div ref={el} id={id} className={"plot "+(small?"short":"")} />;
}
export function Segments({items,value,onChange,label}) {
  return <div className="segments" role="group" aria-label={label}>{items.map(([v,text])=>
    <button key={v} type="button" aria-pressed={v===value} onClick={()=>onChange(v)}>{text}</button>)}</div>;
}
export function Card({label,title,action,children,foot}) {
  return <section className="panel"><div className="panelhead"><div>{label&&<div className="eyebrow">{label}</div>}<h2>{title}</h2></div>{action}</div>
    {children}{foot&&<div className="foot">{foot}</div>}</section>;
}
export function Markets({session,result}) {
  const [mode,setMode]=useState("relative"),[minutes,setMinutes]=useState(10),[rate,setRate]=useState(false);
  const bars=session.bars.map(rows=>rows.filter(p=>p[0]>=session.end-minutes*60));
  const traces=mode==="relative"?bars.map((rows,i)=>({type:"scatter",mode:"lines",name:i?"SPY":"ESH5",x:rows.map(p=>iso(session.start,p[0]+1)),
    y:rows.map(p=>(p[4]/rows[0][4]-1)*10000),line:{width:1.7,color:i?lilac:mint},hovertemplate:"%{y:.2f} bp<extra></extra>"})):
    [{type:"candlestick",name:"SPY",x:bars[1].map(p=>iso(session.start,p[0]+1)),...Object.fromEntries(["open","high","low","close"].map((f,i)=>[f,bars[1].map(p=>p[i+1])])),
      increasing:{line:{color:mint}},decreasing:{line:{color:red}}}];
  const points=result.markout;
  const values=points.map((r,i)=>{const prev=points[i-1]||{ms:0,bp:0};return !rate||r.bp==null?r.bp:prev.bp==null?null:(r.bp-prev.bp)/(r.ms-prev.ms);});
  return <><Card label="PRICE DISCOVERY" title="Market replay" action={<Segments label="Chart style" value={mode} onChange={setMode} items={[["relative","Relative"],["candles","Candles"]]}/>}
    foot={mode==="relative"?"One-second closing midpoints, rebased at the selected window’s start. Drag to zoom.":"SPY midpoint OHLC at one-second intervals. Double-click to reset zoom."}>
    <div className="charttools"><div className="legend">{mode==="relative"?<><i/>ESH5 <i className="purple"/>SPY</>:"SPY · USD"}</div>
    <Segments value={minutes} onChange={setMinutes} label="Replay window" items={[[1,"1m"],[5,"5m"],[10,"10m"]]}/></div>
    <Plot id="price" traces={traces} xaxis={{type:"date",tickformat:"%H:%M:%S",rangeslider:{visible:false}}} yaxis={{title:{text:mode==="relative"?"Return (bp)":"Price ($)"}}}/></Card>
    <Card label="SIGNAL DECAY" title="SPY response curve" action={<Segments label="Response units" items={[[false,"Return"],[true,"Per ms"]]} value={rate} onChange={setRate}/>}
      foot="Signed SPY midpoint change following each eligible signal. Includes signals observed while a trade was open.">
      <Plot small id="decay" traces={[{type:"scatter",mode:"lines+markers",name:"SPY",x:points.map(r=>r.ms),y:values,line:{color:lilac},fill:"tozeroy",fillcolor:"rgba(179,150,255,.09)"}]}
        xaxis={{type:"log",tickvals:[1,5,20,100,250],title:{text:"Milliseconds after signal"}}} yaxis={{title:{text:rate?"Incremental bp / ms":"Return (bp)"}}}/></Card></>;
}
