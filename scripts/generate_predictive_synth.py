import argparse
import numpy as np
import pandas as pd


def synth(n: int = 800, seed: int = 7) -> pd.DataFrame:
    """Generate synthetic predictive training samples."""

    rng = np.random.default_rng(seed)
    rows: list[list[float]] = []

    for _ in range(n):
        amount = float(np.round(50 + rng.exponential(500), 2))
        customer_age_days = int(rng.integers(10, 1500))
        prior_invoices = int(max(0, int(rng.normal(customer_age_days / 40, 5))))
        late_ratio = float(np.clip(rng.beta(2, 8), 0, 1))
        weekday = int(rng.integers(0, 7))
        month = int(rng.integers(1, 13))

        base = 18 + 0.008 * (amount ** 0.5) + 0.02 * prior_invoices + 20 * late_ratio
        season = 4 if month in [12, 1] else 0
        noise = rng.normal(0, 6)
        actual_payment_days = max(0, min(120, base + season + noise))

        rows.append(
            [
                amount,
                customer_age_days,
                prior_invoices,
                late_ratio,
                weekday,
                month,
                actual_payment_days,
            ]
        )

    return pd.DataFrame(
        rows,
        columns=[
            "amount",
            "customer_age_days",
            "prior_invoices",
            "late_ratio",
            "weekday",
            "month",
            "actual_payment_days",
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=800)
    parser.add_argument("--out", default="data/training/predictive_example.csv")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    frame = synth(args.n, args.seed)
    frame.to_csv(args.out, index=False)
    print(f"Wrote {args.out} with {len(frame)} rows")


if __name__ == "__main__":
    main()
