export const demo = window.PHASE_DEMO;
export async function request(url, options) {
  const r = await fetch(url, options);
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.error || r.statusText);
  }
  return r.json();
}
export function loadSession() {
  return demo ? Promise.resolve({...demo, result:demo.runs[0].result}) : request("/api/session");
}
export async function simulate(settings, scenario) {
  if (!demo) return request("/api/run",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(settings)});
  const recorded = demo.runs[scenario].result;
  const ledger = recorded.ledger.map(r => {
    const cost = 2*settings.fee + (r.entry+r.exit)*settings.impact_bp/10000;
    return {...r, cost, net:r.gross-cost};
  });
  const net = ledger.reduce((sum,r)=>sum+r.net,0);
  return {...recorded,settings,ledger,net,avg_net:ledger.length ? net/ledger.length : null};
}
export function tickData(t) {
  return demo ? Promise.resolve(demo.details[Math.round(t*1e9)]) : request("/api/detail?t="+t);
}
export const cash = n => (n<0?"−":"")+"$"+Math.abs(n).toFixed(2);
export const number = n => n.toLocaleString("en-US");
export const iso = (start,t) => new Date((start+t)*1000).toISOString();
export function exportCsv(rows) {
  if (!rows.length) return;
  const keys=Object.keys(rows[0]);
  const url=URL.createObjectURL(new Blob([[keys.join(","),...rows.map(r=>keys.map(k=>r[k]).join(","))].join("\n")],{type:"text/csv"}));
  const a=document.createElement("a"); a.href=url; a.download="phase-executions.csv"; a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
