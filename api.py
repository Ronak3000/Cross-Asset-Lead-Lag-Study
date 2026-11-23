"""FastAPI interface for the Phase research engine and its compiled React client."""
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.routing import APIRoute
from plotly.offline import get_plotlyjs
from pydantic import BaseModel, ConfigDict

from simulation import SEC, Settings


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    feed_ms: float = Settings.feed_ms
    order_ms: float = Settings.order_ms
    hold_ms: float = Settings.hold_ms
    threshold_bp: float = Settings.threshold_bp
    fee: float = Settings.fee
    impact_bp: float = Settings.impact_bp
    style: Literal["market", "passive"] = Settings.style
    filter_flow: bool = Settings.filter_flow


class SmallRequestRoute(APIRoute):
    """Enforce the original 4 KiB configuration limit, including chunked uploads."""
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def bounded(request: Request):
            if request.method != "POST":
                return await handler(request)
            received = 0

            async def receive():
                nonlocal received
                message = await request.receive()
                received += len(message.get("body", b""))
                if received > 4096:
                    raise HTTPException(413, "Configuration exceeds 4096 bytes")
                return message

            return await handler(Request(request.scope, receive))

        return bounded


def dashboard_app(session, initial, comparisons):
    app = FastAPI(title="Phase Research API", version="1.0",
                  description="Inspect a fitted ES–SPY session and replay execution scenarios.")
    app.router.route_class = SmallRequestRoute
    ui = Path(__file__).resolve().parent / "ui"
    plotly_js = Response(get_plotlyjs(), media_type="application/javascript")
    snapshot = JSONResponse(dict(start=session.start // SEC, split=session.split // SEC,
                                 end=session.duration // SEC, synthetic=session.synthetic,
                                 model=session.fit, result=initial, benchmarks=comparisons,
                                 bars=session.chart(session.split // SEC, session.duration // SEC, 1)))

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request, exc):
        issue = exc.errors()[0]
        field = ".".join(map(str, issue["loc"]))
        return JSONResponse({"error": f"{field}: {issue['msg']}"}, status_code=400)

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(ui / "index.html")

    @app.get("/plot.js", include_in_schema=False)
    def plot_bundle():
        return plotly_js

    @app.get("/ui/{asset}", include_in_schema=False)
    def frontend_asset(asset: str):
        if asset not in {"app.js", "style.css", "index.html"}:
            raise HTTPException(404)
        return FileResponse(ui / asset)

    @app.get("/api/session", summary="Read session, benchmarks and one-second bars")
    def get_session():
        return snapshot

    @app.post("/api/run", summary="Replay the evaluation window with execution settings")
    def run_backtest(config: RunRequest):
        try:
            settings = Settings(**config.model_dump())
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        return JSONResponse(session.run(settings))

    @app.get("/api/detail", summary="Inspect tick quotes surrounding a signal")
    def get_detail(t: float = Query(description="Signal time in seconds from session start")):
        if not session.split / SEC <= t < session.duration / SEC:
            return JSONResponse({"error": "Choose a time in the evaluation window"}, status_code=400)
        return JSONResponse(session.detail(t))

    return app


def create_app():
    """Historical-session entry point for uvicorn api:create_app --factory."""
    from research import prepare
    from study import DATA, END, START, records

    return dashboard_app(*prepare(DATA, START, END, records, benchmark=True))


def create_demo_app():
    """Hosted demo using generated books and the same interactive backtest engine."""
    from research import prepare
    from study import DATA, END, START, records

    return dashboard_app(*prepare(DATA, START, END, records, synthetic=True, benchmark=True))
