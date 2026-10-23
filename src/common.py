"""
Shared data loading for the FRED-MD project.

Only loading and period slicing live here for now. Shared methods get added
once the group agrees on them, via a pull request.
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
# The other periods will be added here once agreed.
PERIODS = {
    "2005-2015": ("2005-01-01", "2015-12-31"),
}


# =============================================================================
# FUNCTIONS
# =============================================================================

def load_clean(path: Path = CLEAN_PATH) -> pd.DataFrame:
    """Load the imputed FRED-MD panel with a monthly DatetimeIndex.

    The R imputation step drops the series names (columns come out as 1..N),
    so if that happens they are restored from the matching transformed file,
    which has the same columns in the same order.
    """
    df = pd.read_csv(path, index_col="date", parse_dates=True)
    if df.columns[0] == "1":
        names_path = Path(path).with_name(Path(path).name.replace("_clean_", "_transformed_"))
        df.columns = pd.read_csv(names_path, index_col="date", nrows=0).columns
    return df


def load_transformed(path: Path = TRANSFORMED_PATH) -> pd.DataFrame:
    """Load the transformed (not imputed) panel with a monthly DatetimeIndex. NAs are kept."""
    return pd.read_csv(path, index_col="date", parse_dates=True)


def slice_period(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Return the rows of df that fall inside PERIODS[name] (inclusive)."""
    start, end = PERIODS[name]
    return df.loc[start:end]
