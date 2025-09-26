from typing import List
from typing import Optional

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str
    quantity: Optional[float] = 1
    unit_price: Optional[float] = None
    total: Optional[float] = None


class InvoiceExtraction(BaseModel):
    supplier_name: Optional[str]
    supplier_tax_id: Optional[str]
    invoice_number: Optional[str]
    invoice_date: Optional[str]
    due_date: Optional[str]
    currency: Optional[str] = "USD"
    subtotal: Optional[float]
    tax: Optional[float]
    total: Optional[float]
    buyer_name: Optional[str]
    buyer_tax_id: Optional[str]
    items: List[LineItem] = Field(default_factory=list)
    raw_text: str


class ClassificationResult(BaseModel):
    label: str
    proba: float


class PredictiveResult(BaseModel):
    predicted_payment_days: float
    predicted_payment_date: Optional[str]
    risk_score: float
    confidence: float
