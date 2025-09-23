#!/usr/bin/env python3
"""CLI entry-point for synthetic invoice data generation."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))

from ai_invoice.data.synthetic import SyntheticInvoiceGenerator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic invoice datasets for training.")
    parser.add_argument(
        "--records",
        type=int,
        default=200,
        help="Number of invoice records to fabricate (must be > 0).",
    )
    parser.add_argument(
        "--class-balance",
        type=float,
        default=0.5,
        help="Fraction of classifier documents that should be invoices (0.0-1.0).",
    )
    parser.add_argument(
        "--noise",
        type=float,
        default=0.1,
        help="Noise level to inject into text and numeric fields (0.0-1.0).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic random seed for reproducible batches.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/training"),
        help="Directory that will receive the generated CSV files.",
    )
    parser.add_argument(
        "--prefix",
        default="synthetic",
        help="Filename prefix for the generated CSV files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.records < 1:
        raise ValueError("--records must be a positive integer")
    if not 0.0 <= args.class_balance <= 1.0:
        raise ValueError("--class-balance must be between 0.0 and 1.0")
    if not 0.0 <= args.noise <= 1.0:
        raise ValueError("--noise must be between 0.0 and 1.0")

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = SyntheticInvoiceGenerator(seed=args.seed)

    invoice_documents = max(1, round(args.records * args.class_balance))
    invoice_count = max(args.records, invoice_documents)

    invoices = generator.generate_invoices(invoice_count, noise_level=args.noise)
    invoices_for_training = invoices[: args.records]

    classifier_df = generator.build_classifier_dataset(
        invoices=invoices,
        invoice_documents=invoice_documents,
        total_documents=args.records,
        noise_level=args.noise,
    )
    predictive_df = generator.predictive_to_dataframe(invoices_for_training)
    invoice_df = generator.invoices_to_dataframe(invoices_for_training)
    line_items_df = generator.line_items_to_dataframe(invoices_for_training)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    prefix = args.prefix.strip() or "synthetic"

    classifier_path = output_dir / f"{prefix}_classifier_{timestamp}.csv"
    predictive_path = output_dir / f"{prefix}_predictive_{timestamp}.csv"
    invoices_path = output_dir / f"{prefix}_invoices_{timestamp}.csv"
    line_items_path = output_dir / f"{prefix}_line_items_{timestamp}.csv"

    classifier_df.to_csv(classifier_path, index=False)
    predictive_df.to_csv(predictive_path, index=False)
    invoice_df.to_csv(invoices_path, index=False)
    line_items_df.to_csv(line_items_path, index=False)

    invoice_labels = int((classifier_df["label"] == "invoice").sum())
    receipt_labels = len(classifier_df) - invoice_labels

    print(f"Wrote {len(classifier_df)} classifier rows ({invoice_labels} invoices / {receipt_labels} receipts) -> {classifier_path}")
    print(f"Wrote {len(predictive_df)} predictive rows -> {predictive_path}")
    print(f"Wrote {len(invoice_df)} invoice summaries -> {invoices_path}")
    print(f"Wrote {len(line_items_df)} line items -> {line_items_path}")


if __name__ == "__main__":
    main()
