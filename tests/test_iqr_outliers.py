"""
Check src.common.iqr_outliers against R's fbi::rm_outliers.fredmd.

R applies the 10 x IQR rule to the full transformed panel, including the first
2 rows that preprocess.R later drops, so we rebuild that panel from data/raw.
R's outliers = cells that are NaN in fredmd_transformed_* but observed in the
rebuilt panel.

Run: python tests/test_iqr_outliers.py   (or pytest)
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.common import REPO_ROOT, VINTAGE, iqr_outliers, load_transformed

RAW_PATH = REPO_ROOT / "data" / "raw" / f"{VINTAGE}-MD.csv"


def tcode_transform(x: pd.Series, code: int) -> pd.Series:
    """McCracken & Ng tcodes, as in fbi::fredmd."""
    return {
        1: lambda: x,
        2: lambda: x.diff(),
        3: lambda: x.diff().diff(),
        4: lambda: np.log(x),
        5: lambda: np.log(x).diff(),
        6: lambda: np.log(x).diff().diff(),
        7: lambda: (x / x.shift() - 1).diff(),
    }[code]()


def load_raw_transformed() -> pd.DataFrame:
    raw = pd.read_csv(RAW_PATH)
    tcodes = raw.iloc[0, 1:].astype(int)
    raw = raw.iloc[1:].dropna(how="all")
    raw.index = pd.to_datetime(raw.pop("sasdate"), format="%m/%d/%Y")
    raw = raw.astype(float)
    return pd.DataFrame({c: tcode_transform(raw[c], tcodes[c]) for c in raw.columns})


def test_iqr_outliers_matches_r():
    full = load_raw_transformed()
    r = load_transformed()
    py = iqr_outliers(full).loc[r.index]
    observed = full.loc[r.index].notna()

    r_out = r.isna() & observed
    py_out = py.isna() & observed
    print("Outliers  R:", int(r_out.sum().sum()), " Python:", int(py_out.sum().sum()))
    assert (r_out == py_out).all().all()


if __name__ == "__main__":
    test_iqr_outliers_matches_r()
    print("OK")
