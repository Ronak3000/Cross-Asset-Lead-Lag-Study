"""Build a single-file synthetic demo for interview rooms without Python or internet."""
import json
from dataclasses import replace
from pathlib import Path

from plotly.offline import get_plotlyjs

from research import Session
from benchmarks import measure
from sample_session import sample_books
from simulation import SEC, Settings


def script(code):
    return "<script>" + code.replace("</script", "<\\/script") + "</script>"


def main():
    root = Path(__file__).resolve().parent
    start = 1738681200 * SEC
    end = start + 1800 * SEC
    session = Session(sample_books(start, end), start, end, synthetic=True)
    base = Settings()
    runs = []
    details = {}
    for label, config in (("Marketable · 4 ms feed", base),
                          ("Marketable · 8 ms feed", replace(base, feed_ms=8)),
                          ("Passive · 4 ms feed", replace(base, style="passive"))):
        result = session.run(config)
        for trade in result["ledger"][:100]:
            second = trade["signal_s"]
            details[round(second*1e9)] = session.detail(second)
        runs.append(dict(label=label, result=result))
    payload = dict(start=start//SEC, split=1200, end=1800, model=session.fit, synthetic=True,
                   bars=session.chart(1200, 1800, 1), runs=runs, details=details, benchmarks=measure(session))
    ui = root / "ui"
    app = (ui / "app.js").read_text(encoding="utf-8")
    html = (ui / "index.html").read_text(encoding="utf-8")
    html = html.replace('<link rel="stylesheet" href="/ui/style.css">',
                        "<style>"+(ui/"style.css").read_text(encoding="utf-8")+"</style>")
    html = html.replace('<script defer src="/plot.js"></script>', "").replace('<script defer src="/ui/app.js"></script>', "")
    scripts = (script(get_plotlyjs()) + script("window.PHASE_DEMO="+json.dumps(payload, separators=(",", ":"))+";")
               + script(app))
    output = root/"results"/"Phase-demo.html"
    output.parent.mkdir(exist_ok=True)
    output.write_text(html.replace("</body>",scripts+"</body>"),encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
