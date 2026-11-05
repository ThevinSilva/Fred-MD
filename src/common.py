"""
Shared data loading for the FRED-MD project.

Only loading, period slicing and the outlier rule live here for now. Shared
methods get added once the group agrees on them, via a pull request.

Which file to use (all produced by R/preprocess.R, see README "Outputs"):
    load_tcode        tcode transform only, NAs kept   -> forecasting
    load_transformed  + full-sample 10 x IQR outliers  -> legacy
    load_clean        + full-sample imputation         -> exploration / plots only
"""

from pathlib import Path

import pandas as pd


# =============================================================================
# SETTINGS
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parent.parent

# PROPOSAL: to be agreed by the group
VINTAGE = "2026-09"

# PROPOSAL: to be agreed by the group
CLEAN_PATH = REPO_ROOT / "data" / "clean" / f"fredmd_clean_{VINTAGE}.csv"

# PROPOSAL: to be agreed by the group
TRANSFORMED_PATH = REPO_ROOT / "data" / "clean" / f"fredmd_transformed_{VINTAGE}.csv"

# PROPOSAL: to be agreed by the group
TCODE_PATH = REPO_ROOT / "data" / "clean" / f"fredmd_tcode_{VINTAGE}.csv"

# PROPOSAL: to be agreed by the group
# The other periods will be added here once agreed.
PERIODS = {
    "2005-2015": ("2005-01-01", "2015-12-31"),
    "1990-2004": ("1990-01-01", "2004-12-31"),
}


# =============================================================================
# FUNCTIONS
# =============================================================================

def load_tcode(path: Path = TCODE_PATH) -> pd.DataFrame:
    """Load the tcode-transformed panel with a monthly DatetimeIndex.

    Recommended input for forecasting. Only the McCracken & Ng tcode
    transformations are applied: no outlier removal, no imputation, NAs kept
    (including the ragged final month). Apply any outlier rule (see
    iqr_outliers) and imputation inside each estimation window, using only
    data available at the forecast origin.
    """
    return pd.read_csv(path, index_col="date", parse_dates=True)


def load_clean(path: Path = CLEAN_PATH) -> pd.DataFrame:
    """Load the imputed FRED-MD panel with a monthly DatetimeIndex.

    WARNING: exploration and plots only, NOT for out-of-sample forecasting.
    Outliers are removed with a 10 x IQR rule and gaps are filled with tw_apc,
    both estimated on the FULL sample, so every row uses future information.
    For forecasting use load_tcode.
    """
    df = pd.read_csv(path, index_col="date", parse_dates=True)
    if all(str(c).isdigit() for c in df.columns):
        raise ValueError(
            f"{path} has numeric column headers (1..N) instead of series names. "
            "It was written by an old version of R/preprocess.R; rerun the script "
            "to regenerate it."
        )
    return df


def load_transformed(path: Path = TRANSFORMED_PATH) -> pd.DataFrame:
    """Load the transformed (not imputed) panel with a monthly DatetimeIndex. NAs are kept.

    Includes FULL-SAMPLE outlier removal: values with |x - median| > 10 x IQR,
    median and IQR computed over 1959 to the final month, are set to NA. The
    outlier thresholds therefore use future data. For forecasting use
    load_tcode and, if wanted, iqr_outliers inside each window.
    """
    return pd.read_csv(path, index_col="date", parse_dates=True)


def iqr_outliers(df: pd.DataFrame, k: float = 10) -> pd.DataFrame:
    """Set outliers to NaN using the McCracken & Ng (2016) rule.

    A value is an outlier if |x - median| > k * IQR, with the median and IQR
    of each column computed from the rows of df only (NaNs ignored). Pass the
    estimation window to apply it without look-ahead. Mirrors
    fbi::rm_outliers.fredmd for k = 10 (IQR = 75th - 25th percentile, R's
    default type-7 quantiles, strict inequality).

    Our default is NO outlier removal (outliers are real events such as 2001,
    the GFC and COVID); use this as a sensitivity check.
    """
    median = df.median()
    iqr = df.quantile(0.75) - df.quantile(0.25)
    return df.mask((df - median).abs() > k * iqr)


def slice_period(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Return the rows of df that fall inside PERIODS[name] (inclusive)."""
    start, end = PERIODS[name]
    return df.loc[start:end]
