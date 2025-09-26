from __future__ import annotations

from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..middleware import require_api_key, require_license_claims_if_configured


router = APIRouter(
    prefix="/workspace",
    tags=["workspace"],
    dependencies=[Depends(require_api_key), Depends(require_license_claims_if_configured)],
)


class KpiCard(BaseModel):
    label: str
    value: str = Field(..., description="Formatted metric value")
    delta: str
    trend: Literal["up", "down", "neutral"]


class CashFlowPoint(BaseModel):
    day: str
    value: float


class DashboardPayload(BaseModel):
    cards: List[KpiCard]
    cash_flow: List[CashFlowPoint]


class InvoiceSummary(BaseModel):
    id: str
    vendor: str
    issued_on: str
    due_on: str
    amount: str
    status: str
    reference: str
    notes: str | None = None


class InvoiceLineItem(BaseModel):
    id: str
    description: str
    quantity: float
    unit_cost: str
    amount: str


class InvoicePayload(BaseModel):
    summary: InvoiceSummary
    line_items: List[InvoiceLineItem]


class VendorEntry(BaseModel):
    id: str
    name: str
    category: str
    contact: str
    status: str


class ReportEntry(BaseModel):
    id: str
    title: str
    description: str
    updated: str


class ApprovalStatus(str):
    Pending = "Pending"
    Approved = "Approved"
    Rejected = "Rejected"


class ApprovalEntry(BaseModel):
    id: str
    title: str
    vendor: str
    amount: str
    submitted: str
    status: Literal["Pending", "Approved", "Rejected"]


class ApprovalDecision(BaseModel):
    status: Literal["Approved", "Rejected"]


_DASHBOARD = DashboardPayload(
    cards=[
        KpiCard(label="Pending Approvals", value="8", delta="+2 vs last week", trend="up"),
        KpiCard(label="Invoices Processed", value="142", delta="+12% efficiency", trend="up"),
        KpiCard(label="Average Cycle Time", value="2.4d", delta="-0.6d this month", trend="down"),
        KpiCard(label="Exceptions", value="3", delta="2 high priority", trend="neutral"),
    ],
    cash_flow=[
        CashFlowPoint(day="Mon", value=12.0),
        CashFlowPoint(day="Tue", value=18.0),
        CashFlowPoint(day="Wed", value=15.0),
        CashFlowPoint(day="Thu", value=22.0),
        CashFlowPoint(day="Fri", value=26.0),
        CashFlowPoint(day="Sat", value=21.0),
        CashFlowPoint(day="Sun", value=24.0),
    ],
)


_INVOICE = InvoicePayload(
    summary=InvoiceSummary(
        id="INV-2098",
        vendor="Pura Vida Supplies",
        issued_on="2025-05-02",
        due_on="2025-05-16",
        amount="₡4 860 000",
        status="Awaiting Approval",
        reference="PO-6635",
        notes="Expedited shipping requested",
    ),
    line_items=[
        InvoiceLineItem(
            id="1",
            description="Thermal paper rolls",
            quantity=120,
            unit_cost="₡7 500",
            amount="₡900 000",
        ),
        InvoiceLineItem(
            id="2",
            description="Receipt printers",
            quantity=15,
            unit_cost="₡72 000",
            amount="₡1 080 000",
        ),
        InvoiceLineItem(
            id="3",
            description="POS tablets (Wi-Fi)",
            quantity=6,
            unit_cost="₡132 000",
            amount="₡792 000",
        ),
        InvoiceLineItem(
            id="4",
            description="Custom cabling kit",
            quantity=6,
            unit_cost="₡24 000",
            amount="₡144 000",
        ),
    ],
)


_VENDORS: list[VendorEntry] = [
    VendorEntry(
        id="v-01",
        name="Pura Vida Supplies",
        category="Hardware",
        contact="andrea@puravida.cr",
        status="Active",
    ),
    VendorEntry(
        id="v-02",
        name="San José Stationers",
        category="Office Supplies",
        contact="ventas@sanjose.co.cr",
        status="Active",
    ),
    VendorEntry(
        id="v-03",
        name="CloudCafe Roasters",
        category="Hospitality",
        contact="orders@cloudcafe.cr",
        status="On Hold",
    ),
    VendorEntry(
        id="v-04",
        name="Montezuma Analytics",
        category="Consulting",
        contact="sofia@montezuma.io",
        status="Active",
    ),
    VendorEntry(
        id="v-05",
        name="Tamarindo Creative",
        category="Design",
        contact="hola@tamarindocreative.cr",
        status="Prospect",
    ),
]


_REPORTS: list[ReportEntry] = [
    ReportEntry(
        id="r-01",
        title="Monthly Spend Overview",
        description="Summary of paid vs outstanding invoices by department.",
        updated="Updated 2 days ago",
    ),
    ReportEntry(
        id="r-02",
        title="Aging Report",
        description="Breakdown of invoices by 0-30, 31-60, 61-90, and 90+ days.",
        updated="Updated yesterday",
    ),
    ReportEntry(
        id="r-03",
        title="Vendor Performance",
        description="Delivery, accuracy, and SLA insights by supplier.",
        updated="Updated 4 days ago",
    ),
]


_APPROVALS: list[ApprovalEntry] = [
    ApprovalEntry(
        id="a-01",
        title="Invoice INV-2098",
        vendor="Pura Vida Supplies",
        amount="₡4 860 000",
        submitted="2h ago",
        status="Pending",
    ),
    ApprovalEntry(
        id="a-02",
        title="Purchase Request PR-447",
        vendor="CloudCafe Roasters",
        amount="₡602 000",
        submitted="5h ago",
        status="Pending",
    ),
    ApprovalEntry(
        id="a-03",
        title="Contract Renewal CT-032",
        vendor="Montezuma Analytics",
        amount="₡7 440 000",
        submitted="Yesterday",
        status="Pending",
    ),
]


@router.get("/dashboard", response_model=DashboardPayload)
def workspace_dashboard() -> DashboardPayload:
    return _DASHBOARD


@router.get("/invoice", response_model=InvoicePayload)
def workspace_invoice() -> InvoicePayload:
    return _INVOICE


@router.get("/vendors", response_model=list[VendorEntry])
def workspace_vendors() -> list[VendorEntry]:
    return _VENDORS


@router.get("/reports", response_model=list[ReportEntry])
def workspace_reports() -> list[ReportEntry]:
    return _REPORTS


@router.get("/approvals", response_model=list[ApprovalEntry])
def workspace_approvals() -> list[ApprovalEntry]:
    return _APPROVALS


@router.post("/approvals/{approval_id}", response_model=ApprovalEntry)
def decide_approval(approval_id: str, decision: ApprovalDecision) -> ApprovalEntry:
    for index, item in enumerate(_APPROVALS):
        if item.id == approval_id:
            updated = item.copy(update={"status": decision.status})
            _APPROVALS[index] = updated
            return updated
    raise HTTPException(status_code=404, detail="Approval not found")
