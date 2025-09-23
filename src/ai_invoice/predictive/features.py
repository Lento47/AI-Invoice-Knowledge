from __future__ import annotations

import numpy as np
import pandas as pd


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()
    if "amount" in output.columns:
        output["amount_log"] = np.log1p(output["amount"].clip(lower=0))
    if "month" in output.columns:
        output["is_month_end"] = output["month"].isin([3, 6, 9, 12]).astype(int)
    return output
