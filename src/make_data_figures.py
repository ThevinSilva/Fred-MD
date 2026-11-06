"""
Figures for the Data Description and Preprocessing section.

Run from the repo root:
    python -m src.make_data_figures

Saves to figures/:
    data_transform_examples.png   raw levels vs tcode-transformed series
    data_series_available.png     number of series observed each month
    data_outliers_over_time.png   observations flagged by the 10 x IQR rule
    data_missing_outliers.png     heatmap separating genuine gaps from outliers

Uses the tcode-only panel (load_tcode) plus the raw vintage, so the
missing/outlier split is exact: genuine gaps are NA in the tcode panel,
outliers are values the full-sample 10 x IQR rule would remove.
"""

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from src.common import REPO_ROOT, VINTAGE, iqr_outliers, load_tcode

FIG_DIR = REPO_ROOT / "figures"
RAW_PATH = REPO_ROOT / "data" / "raw" / f"{VINTAGE}-MD.csv"

# ---- Style ------------------------------------------------------------------
sns.set_theme(context="paper", style="ticks", font_scale=1.15)
plt.rcParams.update({"savefig.dpi": 220, "savefig.bbox": "tight",
                     "axes.titleweight": "bold", "axes.titlesize": 11})

NAVY = "#1d3557"
CORAL = "#e63946"
TEAL = "#2a9d8f"
SAND = "#f1ece2"
RECESSION = "#d9d4c7"

# NBER recessions (peak month, trough month)
RECESSIONS = [
    ("1960-04", "1961-02"), ("1969-12", "1970-11"), ("1973-11", "1975-03"),
    ("1980-01", "1980-07"), ("1981-07", "1982-11"), ("1990-07", "1991-03"),
    ("2001-03", "2001-11"), ("2007-12", "2009-06"), ("2020-02", "2020-04"),
]

TCODE_LABELS = {
    1: "level", 2: r"$\Delta x$", 3: r"$\Delta^2 x$", 4: r"$\log x$",
    5: r"$\Delta \log x$", 6: r"$\Delta^2 \log x$", 7: r"$\Delta(x_t/x_{t-1} - 1)$",
}


def load_raw():
    """Raw vintage in levels, plus the tcode row."""
    raw = pd.read_csv(RAW_PATH)
    tcodes = raw.iloc[0, 1:].astype(float).astype(int)
    df = raw.iloc[1:].copy()
    df["sasdate"] = pd.to_datetime(df["sasdate"], format="%m/%d/%Y")
    df = df.dropna(subset=["sasdate"]).set_index("sasdate").astype(float)
    return df, tcodes


def shade_recessions(ax):
    for peak, trough in RECESSIONS:
        ax.axvspan(pd.Timestamp(peak), pd.Timestamp(trough),
                   color=RECESSION, alpha=0.7, lw=0, zorder=0)


def decade_axis(ax):
    ax.xaxis.set_major_locator(mdates.YearLocator(10))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


def recession_handle():
    return Patch(color=RECESSION, alpha=0.7, label="NBER recession")


# ---------------------------------------------------------------------------
# 1. Raw vs transformed
# ---------------------------------------------------------------------------
def fig_transform_examples(raw, tcodes, X):
    series = [("INDPRO", "Industrial production"),
              ("CPIAUCSL", "CPI, all items"),
              ("FEDFUNDS", "Federal funds rate")]
    fig, axes = plt.subplots(len(series), 2, figsize=(10, 7), sharex=True)
    for row, (code, name) in enumerate(series):
        ax_raw, ax_tr = axes[row]
        for ax in (ax_raw, ax_tr):
            shade_recessions(ax)
            ax.grid(axis="y", color="0.9", lw=0.6)
            decade_axis(ax)
        ax_raw.plot(raw.index, raw[code], color=NAVY, lw=1.1)
        ax_tr.plot(X.index, X[code], color=CORAL, lw=0.7)
        ax_tr.axhline(0, color="0.4", lw=0.6)
        ax_raw.set_title(f"{name} ({code})", loc="left")
        ax_tr.set_title(f"tcode {tcodes[code]}: {TCODE_LABELS[tcodes[code]]}",
                        loc="left", fontweight="normal")
    axes[0, 0].text(0, 1.28, "Raw level", transform=axes[0, 0].transAxes,
                    fontsize=12, color=NAVY, fontweight="bold")
    axes[0, 1].text(0, 1.28, "Transformed", transform=axes[0, 1].transAxes,
                    fontsize=12, color=CORAL, fontweight="bold")
    fig.legend(handles=[recession_handle()], loc="lower center",
               frameon=False, bbox_to_anchor=(0.5, -0.03))
    sns.despine(fig)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "data_transform_examples.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 2. Series available per month
# ---------------------------------------------------------------------------
def fig_series_available(X):
    n_obs = X.notna().sum(axis=1)
    N = X.shape[1]
    floor = n_obs.min() - 4
    fig, ax = plt.subplots(figsize=(10, 3.2))
    shade_recessions(ax)
    ax.fill_between(n_obs.index, floor, n_obs.values, step="mid",
                    color=TEAL, alpha=0.25, lw=0)
    ax.step(n_obs.index, n_obs.values, where="mid", color=TEAL, lw=1.3)
    ax.axhline(N, color="0.35", ls="--", lw=0.8)
    ax.text(n_obs.index[8], N + 0.6, f"all {N} series", fontsize=9, color="0.35")
    ax.set_ylim(floor, N + 4)
    ax.set_ylabel("Series observed")
    ax.set_title("Series observed each month", loc="left")
    decade_axis(ax)
    ax.grid(axis="y", color="0.9", lw=0.6)
    sns.despine(ax=ax)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "data_series_available.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 3. Outliers over time
# ---------------------------------------------------------------------------
def outlier_mask(X):
    """True where the full-sample 10 x IQR rule would remove an observed value."""
    return iqr_outliers(X).isna() & X.notna()


def fig_outliers_over_time(X):
    counts = outlier_mask(X).sum(axis=1).resample("QS").sum()
    fig, ax = plt.subplots(figsize=(10, 3.4))
    shade_recessions(ax)
    cap = 14   # COVID quarter dwarfs everything; clip it so the rest is visible
    ax.bar(counts.index, counts.clip(upper=cap).values, width=88,
           color=CORAL, edgecolor="none", zorder=2)
    peak_date, peak = counts.idxmax(), int(counts.max())
    ax.annotate(f"{peak} (axis cut)", (peak_date, cap), xytext=(-6, 2),
                textcoords="offset points", ha="right", fontsize=9, color=CORAL)
    events = [("1974-06", "Oil shock"), ("1981-01", "Volcker"),
              ("2008-10", "GFC"), ("2020-04", "COVID-19")]
    for date, label in events:
        d = pd.Timestamp(date)
        h = counts.clip(upper=cap).loc[d - pd.Timedelta(days=400): d + pd.Timedelta(days=400)].max()
        ax.annotate(label, (d, h), xytext=(0, 14 if label == "COVID-19" else 6),
                    textcoords="offset points", ha="center", fontsize=9,
                    color=NAVY, fontweight="bold")
    ax.set_ylim(0, cap * 1.3)
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.set_ylabel("Outliers per quarter")
    ax.set_title(f"Observations flagged by the 10 × IQR rule "
                 f"({int(counts.sum())} in total)", loc="left")
    decade_axis(ax)
    ax.grid(axis="y", color="0.9", lw=0.6)
    ax.legend(handles=[recession_handle()], frameon=False, loc="upper left")
    sns.despine(ax=ax)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "data_outliers_over_time.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 4. Heatmap: genuine gaps vs outliers
# ---------------------------------------------------------------------------
def fig_missing_outliers(X):
    state = X.isna().astype(int) + 2 * outlier_mask(X).astype(int)  # 0 obs, 1 missing, 2 outlier
    state = state.loc[:, (state > 0).any()]
    order = (state > 0).sum().sort_values().index      # most affected at the top
    state = state[order]

    fig, ax = plt.subplots(figsize=(10, 0.14 * len(order) + 1.4))
    ax.pcolormesh(X.index, np.arange(len(order)), state.T.values,
                  cmap=ListedColormap([SAND, TEAL, CORAL]), vmin=0, vmax=2,
                  shading="nearest", rasterized=True)
    ax.set_yticks(np.arange(len(order)))
    ax.set_yticklabels(order, fontsize=5.5)
    ax.set_ylim(-0.5, len(order) - 0.5)
    for year in range(1960, 2030, 10):
        ax.axvline(pd.Timestamp(f"{year}-01-01"), color="white", lw=0.8)
    decade_axis(ax)
    ax.tick_params(axis="y", length=0)
    ax.legend(handles=[Patch(color=TEAL, label="missing in source"),
                       Patch(color=CORAL, label="outlier (10 × IQR)")],
              loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=2,
              frameon=False)
    ax.set_title(f"Missing values and outliers by series ({VINTAGE} vintage)",
                 loc="left")
    sns.despine(ax=ax, left=True, bottom=True)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "data_missing_outliers.png")
    plt.close(fig)


def main():
    FIG_DIR.mkdir(exist_ok=True)
    raw, tcodes = load_raw()
    X = load_tcode()

    fig_transform_examples(raw, tcodes, X)
    fig_series_available(X)
    fig_outliers_over_time(X)
    fig_missing_outliers(X)

    out = outlier_mask(X)
    print(f"Panel: T = {X.shape[0]} months, N = {X.shape[1]} series, "
          f"{X.index[0]:%b %Y} to {X.index[-1]:%b %Y}")
    print(f"Genuinely missing cells: {int(X.isna().sum().sum())}")
    print(f"Outliers (full-sample 10 x IQR): {int(out.sum().sum())}")
    print("Months with most outliers:")
    print(out.sum(axis=1).nlargest(5).to_string())
    print("tcode counts:")
    print(tcodes.value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
