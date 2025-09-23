from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

REQUIRED_COLUMNS: tuple[str, ...] = (
    "amount",
    "customer_age_days",
    "prior_invoices",
    "late_ratio",
    "weekday",
    "month",
)
DERIVED_COLUMNS: tuple[str, ...] = (
    "amount_log",
    "is_q_end",
    "volume_per_tenure",
    "late_x_volume",
)
WEEKDAY_COLUMNS: tuple[str, ...] = tuple(f"weekday_{idx}" for idx in range(7))
MONTH_COLUMNS: tuple[str, ...] = tuple(f"month_{idx}" for idx in range(1, 13))
ALL_FEATURE_COLUMNS: tuple[str, ...] = (
    "amount",
    "customer_age_days",
    "prior_invoices",
    "late_ratio",
    *DERIVED_COLUMNS,
    *WEEKDAY_COLUMNS,
    *MONTH_COLUMNS,
)


def _ensure_columns(frame: pd.DataFrame, required: Iterable[str]) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required feature columns: {', '.join(sorted(missing))}")


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create the engineered feature frame used by the predictive model."""

    _ensure_columns(df, REQUIRED_COLUMNS)
    values = df.copy()

    for column in REQUIRED_COLUMNS:
        values[column] = pd.to_numeric(values[column], errors="coerce")

    if values[REQUIRED_COLUMNS].isnull().any().any():
        raise ValueError("Received null or non-numeric predictive feature values.")

    features = pd.DataFrame(index=values.index)

    amount = values["amount"].clip(lower=0).astype(float)
    customer_age = values["customer_age_days"].clip(lower=0).astype(float)
    prior_invoices = values["prior_invoices"].clip(lower=0).astype(float)
    late_ratio = values["late_ratio"].clip(lower=0, upper=1).astype(float)
    month = values["month"].round().astype(int)
    weekday = values["weekday"].round().astype(int)

    features["amount"] = amount
    features["customer_age_days"] = customer_age
    features["prior_invoices"] = prior_invoices
    features["late_ratio"] = late_ratio

    features["amount_log"] = np.log1p(amount)
    features["is_q_end"] = month.isin([3, 6, 9, 12]).astype(int)

    tenure = customer_age.replace(0, np.nan)
    features["volume_per_tenure"] = (
        (amount / tenure).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    )
    features["late_x_volume"] = late_ratio * features["amount_log"]

    weekday_dummies = pd.get_dummies(weekday, prefix="weekday")
    for column in WEEKDAY_COLUMNS:
        features[column] = weekday_dummies.get(column, 0)

    month_dummies = pd.get_dummies(month, prefix="month")
    for column in MONTH_COLUMNS:
        features[column] = month_dummies.get(column, 0)

    return features.reindex(columns=ALL_FEATURE_COLUMNS, fill_value=0.0)
