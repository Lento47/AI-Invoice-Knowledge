"""Synthetic invoice data generation utilities."""

from __future__ import annotations

import random
import string
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, List, Sequence

import pandas as pd
from faker import Faker


@dataclass
class SyntheticLineItem:
    """A single line item inside a fabricated invoice."""

    invoice_id: str
    description: str
    quantity: int
    unit_price: float

    @property
    def line_total(self) -> float:
        """Return the rounded total for the line item."""

        return round(self.quantity * self.unit_price, 2)

    def to_dict(self) -> dict[str, object]:
        """Serialize the line item to a flat dictionary."""

        return {
            "invoice_id": self.invoice_id,
            "description": self.description,
            "quantity": self.quantity,
            "unit_price": round(self.unit_price, 2),
            "line_total": self.line_total,
        }


@dataclass
class SyntheticInvoice:
    """A fabricated invoice record with derived payment behavior."""

    invoice_id: str
    vendor: str
    customer: str
    issue_date: date
    due_date: date
    currency: str
    subtotal: float
    tax: float
    total: float
    payment_terms: int
    payment_days: int
    paid_on_time: bool
    customer_age_days: int
    prior_invoices: int
    historic_late_ratio: float
    weekday: int
    month: int
    line_items: List[SyntheticLineItem]

    def to_summary_dict(self) -> dict[str, object]:
        """Serialize headline invoice information."""

        return {
            "invoice_id": self.invoice_id,
            "vendor": self.vendor,
            "customer": self.customer,
            "issue_date": self.issue_date.isoformat(),
            "due_date": self.due_date.isoformat(),
            "currency": self.currency,
            "subtotal": round(self.subtotal, 2),
            "tax": round(self.tax, 2),
            "total": round(self.total, 2),
            "payment_terms": self.payment_terms,
            "actual_payment_days": self.payment_days,
            "paid_on_time": self.paid_on_time,
            "historic_late_ratio": round(self.historic_late_ratio, 2),
        }

    def to_predictive_features(self) -> dict[str, object]:
        """Return the engineered features used for payment prediction."""

        return {
            "amount": round(self.total, 2),
            "customer_age_days": self.customer_age_days,
            "prior_invoices": self.prior_invoices,
            "late_ratio": round(self.historic_late_ratio, 2),
            "weekday": self.weekday,
            "month": self.month,
            "actual_payment_days": self.payment_days,
        }

    def to_classifier_text(self) -> str:
        """Return a natural language description of the invoice."""

        items = "; ".join(
            f"{item.description} {item.quantity} x {item.unit_price:.2f} = {item.line_total:.2f}"
            for item in self.line_items
        )
        return (
            f"{self.vendor.upper()} INVOICE #{self.invoice_id} Issued {self.issue_date.isoformat()} "
            f"Due {self.due_date.isoformat()} Total {self.total:,.2f} {self.currency} Items: {items}"
        )


class SyntheticInvoiceGenerator:
    """Generator that fabricates invoices, line items, and payment outcomes."""

    RECEIPT_PREFIXES = ("RECEIPT", "TICKET", "POS RECEIPT", "SALES RECEIPT")
    INVOICE_PREFIXES = ("INV", "BILL", "FACT", "INVOICE")
    CURRENCIES = ("USD", "EUR", "GBP", "CAD", "AUD", "JPY")

    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed
        self._rng = random.Random(seed)
        self._faker = Faker()
        self._faker.seed_instance(seed)

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def generate_invoices(self, count: int, noise_level: float = 0.0) -> List[SyntheticInvoice]:
        """Generate a list of synthetic invoices.

        Args:
            count: Number of invoices to fabricate.
            noise_level: Value between 0 and 1 controlling numeric variability.
        """

        noise = self._clamp(noise_level)
        return [self._build_invoice(noise) for _ in range(count)]

    def build_classifier_dataset(
        self,
        invoices: Sequence[SyntheticInvoice],
        invoice_documents: int,
        total_documents: int,
        noise_level: float = 0.0,
    ) -> pd.DataFrame:
        """Create a dataframe of document texts and labels for the classifier."""

        noise = self._clamp(noise_level)
        invoice_count = min(invoice_documents, len(invoices))
        data = [
            {"text": self._apply_text_noise(inv.to_classifier_text(), noise), "label": "invoice"}
            for inv in invoices[:invoice_count]
        ]

        receipt_count = max(0, total_documents - invoice_count)
        for _ in range(receipt_count):
            receipt_text = self._generate_receipt_text(noise)
            data.append({"text": receipt_text, "label": "receipt"})

        self._rng.shuffle(data)
        return pd.DataFrame(data)

    @staticmethod
    def invoices_to_dataframe(invoices: Sequence[SyntheticInvoice]) -> pd.DataFrame:
        """Flatten invoices into a dataframe for export."""

        return pd.DataFrame(inv.to_summary_dict() for inv in invoices)

    @staticmethod
    def line_items_to_dataframe(invoices: Sequence[SyntheticInvoice]) -> pd.DataFrame:
        """Flatten invoice line items into a dataframe."""

        rows: list[dict[str, object]] = []
        for invoice in invoices:
            rows.extend(item.to_dict() for item in invoice.line_items)
        return pd.DataFrame(rows)

    @staticmethod
    def predictive_to_dataframe(invoices: Sequence[SyntheticInvoice]) -> pd.DataFrame:
        """Derive predictive model features from invoices."""

        return pd.DataFrame(inv.to_predictive_features() for inv in invoices)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_invoice(self, noise_level: float) -> SyntheticInvoice:
        invoice_id = f"{self._rng.choice(self.INVOICE_PREFIXES)}-{self._rng.randint(1000, 9999)}"
        vendor = self._faker.company()
        customer = self._faker.company() if self._rng.random() < 0.6 else self._faker.name()

        issue_date = self._faker.date_between(start_date="-18M", end_date="today")
        if isinstance(issue_date, str):  # pragma: no cover - faker returns date by default
            issue_date = date.fromisoformat(issue_date)
        payment_terms = self._rng.choice([15, 30, 45, 60])
        due_date = issue_date + timedelta(days=payment_terms)
        currency = self._rng.choice(self.CURRENCIES)

        line_items = [self._create_line_item(invoice_id, noise_level) for _ in range(self._rng.randint(1, 6))]
        subtotal = round(sum(item.line_total for item in line_items), 2)
        tax_rate = max(0.0, min(0.25, self._rng.choice([0.0, 0.05, 0.07, 0.13, 0.2]) + self._rng.uniform(-0.02, 0.02) * noise_level))
        tax = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax, 2)

        customer_age_days = self._rng.randint(60, 2400)
        prior_invoices = self._rng.randint(1, 60)
        base_late_ratio = min(0.95, max(0.02, self._rng.betavariate(2.5, 5.0)))
        historic_late_ratio = max(0.0, min(1.0, base_late_ratio + self._rng.uniform(-0.1, 0.1) * noise_level))

        risk_multiplier = 1 + (total / 20000.0) + (prior_invoices / 300.0) - (customer_age_days / 5000.0)
        late_probability = base_late_ratio * risk_multiplier
        late_probability += self._rng.uniform(-0.15, 0.15) * noise_level
        late_probability = max(0.05, min(0.95, late_probability))

        if self._rng.random() < late_probability:
            paid_on_time = False
            payment_days = payment_terms + self._rng.randint(2, int(30 + 40 * late_probability))
        else:
            paid_on_time = True
            payment_days = max(1, payment_terms - self._rng.randint(0, min(payment_terms, 7)))

        return SyntheticInvoice(
            invoice_id=invoice_id,
            vendor=vendor,
            customer=customer,
            issue_date=issue_date,
            due_date=due_date,
            currency=currency,
            subtotal=subtotal,
            tax=tax,
            total=total,
            payment_terms=payment_terms,
            payment_days=payment_days,
            paid_on_time=paid_on_time,
            customer_age_days=customer_age_days,
            prior_invoices=prior_invoices,
            historic_late_ratio=historic_late_ratio,
            weekday=issue_date.weekday(),
            month=issue_date.month,
            line_items=line_items,
        )

    def _create_line_item(self, invoice_id: str, noise_level: float) -> SyntheticLineItem:
        description = self._faker.catch_phrase()
        quantity = self._rng.randint(1, 12)
        base_price = self._rng.uniform(15.0, 850.0)
        price = base_price * (1 + self._rng.uniform(-0.35, 0.35) * noise_level)
        unit_price = round(max(5.0, price), 2)
        return SyntheticLineItem(invoice_id=invoice_id, description=description, quantity=quantity, unit_price=unit_price)

    def _generate_receipt_text(self, noise_level: float) -> str:
        store = f"{self._faker.company()} Store"
        receipt_id = f"{self._rng.choice(self.RECEIPT_PREFIXES)}-{self._rng.randint(1000, 99999)}"
        lines: list[str] = []
        subtotal = 0.0
        for _ in range(self._rng.randint(2, 6)):
            product = self._faker.word().title()
            quantity = self._rng.randint(1, 4)
            price = round(self._rng.uniform(0.5, 45.0) * (1 + self._rng.uniform(-0.5, 0.5) * noise_level), 2)
            line_total = round(quantity * price, 2)
            subtotal += line_total
            lines.append(f"{product} {quantity} x {price:.2f} = {line_total:.2f}")
        tax = round(subtotal * 0.07, 2)
        total = round(subtotal + tax, 2)
        base = f"{store} RECEIPT #{receipt_id} Subtotal {subtotal:.2f} Tax {tax:.2f} Total {total:.2f} Items: {'; '.join(lines)}"
        return self._apply_text_noise(base, noise_level)

    def _apply_text_noise(self, text: str, noise_level: float) -> str:
        noise = self._clamp(noise_level)
        if noise == 0:
            return text

        chars = list(text)
        for idx, char in enumerate(chars):
            if char.isalpha() and self._rng.random() < noise * 0.3:
                chars[idx] = char.swapcase()
            elif self._rng.random() < noise * 0.05:
                chars[idx] = self._rng.choice(string.ascii_letters + string.digits)

        drop_count = int(len(chars) * noise * 0.03)
        for _ in range(drop_count):
            if not chars:
                break
            del chars[self._rng.randrange(len(chars))]

        insert_count = int(len(chars) * noise * 0.04)
        for _ in range(insert_count):
            insert_char = self._rng.choice(string.ascii_letters + string.digits + " ")
            position = self._rng.randrange(len(chars) + 1)
            chars.insert(position, insert_char)

        return "".join(chars)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))


def shuffle_invoices(invoices: Iterable[SyntheticInvoice], seed: int | None = None) -> List[SyntheticInvoice]:
    """Return a shuffled copy of invoices for convenience."""

    rng = random.Random(seed)
    result = list(invoices)
    rng.shuffle(result)
    return result

