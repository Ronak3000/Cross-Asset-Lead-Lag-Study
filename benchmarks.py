"""Chronological model ablation and execution sensitivity on one session."""
from dataclasses import replace
from platform import machine, python_version, system
from statistics import median
from time import perf_counter

from hawkes import calibrate
from simulation import SEC, Settings


def measure(session):
    full = session.fit
    restricted = calibrate(session.events, session.split / SEC, session.duration / SEC, within_asset=True)
    counts = sum(full["test_events"])
    models = []
    poisson = full["test_poisson_log_likelihood"]
    for name, score, half in (("Constant Poisson", poisson, None),
                             ("Within-asset Hawkes", restricted["test_log_likelihood"], restricted["half_life_ms"]),
                             ("Cross-asset Hawkes", full["test_log_likelihood"], full["half_life_ms"])):
        models.append(dict(name=name, test_ll=score, gain=(score-poisson)/counts, half_ms=half))
    base = Settings()
    cases = [(f"{ms} ms feed", replace(base, feed_ms=ms)) for ms in (0, 2, 4, 8, 12)]
    cases += [("Filter disabled", replace(base, filter_flow=False)), ("Passive entry", replace(base, style="passive"))]
    scenarios = []
    for name, config in cases:
        r = session.run(config)
        scenarios.append(dict(name=name, signals=r["signals"], attempts=r["attempts"], trades=r["trades"],
                              gross=r["gross"], net=r["net"], net_per_trade=r["avg_net"]))
    # Data and model are in memory. The sweep above includes a default warm-up.
    timings = []
    for _ in range(5):
        start = perf_counter()
        session.run(base)
        timings.append(1000*(perf_counter()-start))
    return dict(models=models, incremental_gain=(full["test_log_likelihood"]-restricted["test_log_likelihood"])/counts,
                scenarios=scenarios, train_arrivals=sum(full["train_events"]), test_arrivals=counts,
                runtime=dict(samples_ms=timings, median_ms=median(timings), python=python_version(),
                             platform=system()+" "+machine()), synthetic=session.synthetic)
