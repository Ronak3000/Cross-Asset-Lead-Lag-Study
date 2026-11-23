"""Plot the saved event study. Requires matplotlib."""

import csv
from itertools import groupby

import matplotlib.pyplot as plt

from study import DATA


def main():
    folder = DATA.parents[1] / "results" / DATA.name
    with (folder / "response.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
    for (source, group), color in zip(groupby(rows, key=lambda r: r["source"]), ("#00736d", "#994a18")):
        series = list(group)
        for ax, field in zip(axes, ("pre_bps", "post_bps")):
            ax.plot([int(r["horizon_ms"]) for r in series], [float(r[field]) for r in series],
                    marker="o", ms=4, color=color, label=f"{source} → {series[0]['target']}")
    for ax, title in zip(axes, ("Before the trigger", "After the trigger")):
        ax.set_xscale("log")
        ax.set_xticks([1, 5, 20, 100, 500, 1000], ["1", "5", "20", "100", "500", "1,000"])
        ax.set_xlabel("Window length (ms, log scale)")
        ax.set_title(title, loc="left", fontsize=12)
        ax.grid(axis="y", alpha=0.22)
        ax.axhline(0, color="#67717a", lw=0.8)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Mean signed target return (basis points)")
    axes[1].legend(frameon=False, loc="upper left")
    fig.suptitle("ES futures and SPY around midpoint moves", x=0.09, ha="left", weight="bold")
    fig.subplots_adjust(bottom=0.23, top=0.81, left=0.09)
    fig.text(0.09, 0.035, "4 Feb 2025  ·  10:00–10:30 New York  ·  feed receive times  ·  Nasdaq SPY quotes")
    fig.savefig(folder / "response.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
