"""Continuous-time likelihood for signed ES and SPY trade arrivals."""
from itertools import groupby

import numpy as np
from scipy.optimize import minimize


LABELS = ("ES buy", "ES sell", "SPY buy", "SPY sell")


def history(events, beta):
    """Strictly prior exponential kernel values. Tied streams share pre-event state."""
    features = np.zeros((len(events), 4))
    state = np.zeros(4)
    previous = 0.0
    for time, group in groupby(enumerate(events), key=lambda item: item[1][0]):
        state *= np.exp(-beta * (time - previous))
        batch = list(group)
        for index, _ in batch:
            features[index] = state
        for _, (_, stream) in batch:
            state[stream] += beta
        previous = time
    return features


def exposure(times, streams, beta, start, end):
    """Integral of each unit-mass kernel over the requested observation interval."""
    keep = times < end
    age = np.maximum(start - times[keep], 0)
    width = end - np.maximum(start, times[keep])
    mass = np.exp(-beta * age) * -np.expm1(-beta * width)
    return np.bincount(streams[keep], weights=mass, minlength=4)


def likelihood_rows(features, streams, mass, duration, params):
    intensity = params[streams, 0] + np.einsum("ij,ij->i", features, params[streams, 1:])
    return float(np.log(intensity).sum() - duration * params[:, 0].sum() - (params[:, 1:] @ mass).sum())


def fit_rows(features, streams, mass, duration, within_asset=False):
    rows = []
    for stream in range(4):
        x = features[streams == stream]
        if not len(x):
            raise ValueError(f"No training arrivals for {LABELS[stream]}")
        design = np.column_stack((np.ones(len(x)), x))
        integral = np.r_[duration, mass]

        def objective(theta):
            rates = np.einsum("ij,j->i", design, theta)
            loss = integral @ theta - np.log(rates).sum()
            gradient = integral - np.einsum("ij,i->j", design, 1 / rates)
            return loss / len(x), gradient / len(x)

        limits = [.99 if not within_asset or j // 2 == stream // 2 else 0 for j in range(4)]
        initial = [len(x) / duration] + [min(.05, cap) for cap in limits]
        solution = minimize(objective, initial,
                            jac=True, method="SLSQP", bounds=[(1e-8, None)] + [(0, cap) for cap in limits],
                            constraints=[dict(type="ineq", fun=lambda p: .99 - p[1:].sum())],
                            options=dict(ftol=1e-10, maxiter=350))
        if not solution.success:
            raise ValueError(f"Hawkes fit failed for {LABELS[stream]}: {solution.message}")
        rows.append(solution.x)
    return np.array(rows)


def calibrate(events, split, end, within_asset=False):
    times = np.array([time for time, _ in events])
    streams = np.array([stream for _, stream in events], dtype=int)
    train = times < split
    if not np.any(~train):
        raise ValueError("No evaluation trades in the session.")
    best = None
    for half_ms in (1, 5, 20, 100, 500):
        beta = np.log(2) * 1000 / half_ms
        x = history(events, beta)
        mass = exposure(times, streams, beta, 0, split)
        fit = fit_rows(x[train], streams[train], mass, split, within_asset)
        score = likelihood_rows(x[train], streams[train], mass, split, fit)
        if best is None or score > best[0]:
            best = score, half_ms, beta, fit, x
    train_ll, half_ms, beta, fit, x = best
    mass = exposure(times, streams, beta, split, end)
    test_ll = likelihood_rows(x[~train], streams[~train], mass, end - split, fit)
    counts = np.bincount(streams[train], minlength=4)
    poisson = np.column_stack((counts / split, np.zeros((4, 4))))
    baseline = likelihood_rows(x[~train], streams[~train], mass, end - split, poisson)
    return dict(streams=LABELS, half_life_ms=half_ms, beta_per_s=beta,
                baseline_per_s=fit[:, 0].tolist(), kernel_mass=fit[:, 1:].tolist(),
                spectral_radius=float(max(abs(np.linalg.eigvals(fit[:, 1:])))),
                train_events=counts.tolist(), test_events=np.bincount(streams[~train], minlength=4).tolist(),
                train_log_likelihood=train_ll, test_log_likelihood=test_ll,
                test_poisson_log_likelihood=baseline,
                test_gain_nats_per_event=(test_ll - baseline) / int(sum(~train)))
