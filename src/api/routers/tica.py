from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, conlist

from ..license_validator import LicenseClaims, ensure_feature, require_feature_flag


router = APIRouter(prefix="/invoices", tags=["invoices"])
require_extract_feature = require_feature_flag("extract")


def _to_decimal(value: Decimal | float | int | str | None) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _format_currency(value: Decimal | float | int, currency: str) -> str:
    amount = _to_decimal(value).quantize(Decimal("0.01"))
    return f"{currency} {amount:,.2f}"


def _format_quantity(value: Decimal | float | int) -> str:
    quantity = _to_decimal(value).normalize()
    # fpdf/locale independent formatting: strip exponent when integer
    if quantity == quantity.to_integral():
        return f"{quantity:.0f}"
    return f"{quantity:.3f}".rstrip("0").rstrip(".")


class TicaInvoiceItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)

    description: str = Field(..., max_length=200)
    quantity: Decimal = Field(..., gt=0)
    unit_value: Decimal = Field(..., ge=0)
    total_value: Decimal | None = Field(None, ge=0)
    hs_code: str | None = Field(None, max_length=20, alias="hs_code")
    country_of_origin: str | None = Field(None, max_length=60, alias="country_of_origin")

    def resolved_total(self) -> Decimal:
        if self.total_value is not None:
            return _to_decimal(self.total_value)
        return _to_decimal(self.quantity) * _to_decimal(self.unit_value)


class TicaInvoicePayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)

    invoice_number: str = Field(..., max_length=64)
    issue_date: date
    exporter_name: str = Field(..., max_length=120)
    exporter_id: str = Field(..., max_length=50)
    exporter_address: str | None = Field(None, max_length=200)
    importer_name: str = Field(..., max_length=120)
    importer_id: str = Field(..., max_length=50)
    importer_address: str | None = Field(None, max_length=200)
    incoterm: str | None = Field(None, max_length=16)
    transport_mode: str | None = Field(None, max_length=60)
    destination_port: str | None = Field(None, max_length=80)
    customs_reference: str | None = Field(None, max_length=80)
    regime: str | None = Field(None, max_length=80)
    currency: str = Field(..., max_length=12)
    subtotal: Decimal = Field(..., ge=0)
    tax: Decimal = Field(..., ge=0)
    total: Decimal = Field(..., ge=0)
    notes: str | None = Field(None, max_length=800)
    items: conlist(TicaInvoiceItem, min_length=1)


class SimplePdfBuilder:
    """Minimal PDF builder that writes positioned Helvetica text."""

    PAGE_WIDTH = 595
    PAGE_HEIGHT = 842
    MARGIN_X = 56
    MARGIN_TOP = 780
    MARGIN_BOTTOM = 72
    LINE_HEIGHT = 16
    WRAP_LIMIT = 90

    def __init__(self) -> None:
        self.pages: list[list[tuple[str, int, int, int, str]]] = [[]]
        self.current_y = self.MARGIN_TOP

    def _wrap(self, text: str | None) -> list[str]:
        if text is None:
            return ["N/A"]
        stripped = str(text).strip()
        if not stripped:
            return ["N/A"]
        words = stripped.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) <= self.WRAP_LIMIT:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [stripped]

    def _ensure_space(self, required: int) -> None:
        if self.current_y - required < self.MARGIN_BOTTOM:
            self.pages.append([])
            self.current_y = self.MARGIN_TOP

    def add_line(self, text: str | None, *, font: str = "F1", size: int = 11, indent: int = 0) -> None:
        lines = self._wrap(text)
        for line in lines:
            self._ensure_space(self.LINE_HEIGHT)
            x = self.MARGIN_X + indent
            self.pages[-1].append((font, size, x, self.current_y, line))
            self.current_y -= self.LINE_HEIGHT

    def add_spacing(self, amount: int) -> None:
        self.current_y -= amount

    def add_title(self, text: str) -> None:
        self._ensure_space(32)
        self.pages[-1].append(("F2", 18, self.MARGIN_X, self.current_y, text))
        self.current_y -= 26

    def add_section_heading(self, text: str) -> None:
        self.add_spacing(4)
        self._ensure_space(20)
        heading = text.strip().upper()
        self.pages[-1].append(("F2", 12, self.MARGIN_X, self.current_y, heading))
        self.current_y -= 18

    def add_field(self, label: str, value: str | None) -> None:
        self.add_line(f"{label}: {value or 'N/A'}")

    def add_paragraph(self, text: str) -> None:
        for part in str(text).splitlines() or [""]:
            self.add_line(part, size=10)

    def add_bullet(self, text: str) -> None:
        self.add_line(f"- {text}", size=10, indent=12)

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def render(self) -> bytes:
        pages = [page for page in self.pages if page]
        if not pages:
            pages = [[("F1", 11, self.MARGIN_X, self.MARGIN_TOP, "")]]

        object_contents: list[bytes] = []
        # Font definitions
        object_contents.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        object_contents.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

        for page in pages:
            commands = []
            for font, size, x, y, text in page:
                escaped = self._escape(text)
                commands.append(
                    f"BT\n/{font} {size} Tf\n1 0 0 1 {x} {y} Tm\n({escaped}) Tj\nET\n"
                )
            stream = "".join(commands).encode("latin-1", errors="replace")
            object_contents.append(
                b"<< /Length "
                + str(len(stream)).encode("ascii")
                + b" >>\nstream\n"
                + stream
                + b"\nendstream"
            )

        num_pages = len(pages)
        page_start = len(object_contents) + 1
        pages_index = page_start + num_pages
        catalog_index = pages_index + 1

        for idx in range(num_pages):
            content_index = 3 + idx
            page_obj = (
                f"<< /Type /Page /Parent {pages_index} 0 R /MediaBox [0 0 {self.PAGE_WIDTH} {self.PAGE_HEIGHT}] "
                f"/Contents {content_index} 0 R /Resources << /Font << /F1 1 0 R /F2 2 0 R >> >> >>"
            ).encode("ascii")
            object_contents.append(page_obj)

        kids = " ".join(f"{page_start + i} 0 R" for i in range(num_pages))
        pages_obj = f"<< /Type /Pages /Kids [{kids}] /Count {num_pages} >>".encode("ascii")
        object_contents.append(pages_obj)

        catalog_obj = f"<< /Type /Catalog /Pages {pages_index} 0 R >>".encode("ascii")
        object_contents.append(catalog_obj)

        buffer = BytesIO()
        buffer.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]

        for index, content in enumerate(object_contents, start=1):
            offsets.append(buffer.tell())
            buffer.write(f"{index} 0 obj\n".encode("ascii"))
            buffer.write(content)
            buffer.write(b"\nendobj\n")

        xref_offset = buffer.tell()
        buffer.write(f"xref\n0 {len(offsets)}\n".encode("ascii"))
        buffer.write(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            buffer.write(f"{offset:010d} 00000 n \n".encode("ascii"))

        buffer.write(
            f"trailer\n<< /Size {len(offsets)} /Root {catalog_index} 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
        )
        return buffer.getvalue()


def _build_tica_pdf(payload: TicaInvoicePayload) -> bytes:
    builder = SimplePdfBuilder()
    builder.add_title("Factura Comercial - Formato TICA")

    builder.add_section_heading("Datos de la factura")
    builder.add_field("Número de factura", payload.invoice_number)
    builder.add_field("Fecha de emisión", payload.issue_date.strftime("%d/%m/%Y"))
    builder.add_field("Referencia aduanera", payload.customs_reference)
    builder.add_field("Régimen", payload.regime)
    builder.add_field("Incoterm", payload.incoterm)

    builder.add_section_heading("Exportador")
    builder.add_field("Nombre", payload.exporter_name)
    builder.add_field("Identificación", payload.exporter_id)
    builder.add_field("Dirección", payload.exporter_address)

    builder.add_section_heading("Importador")
    builder.add_field("Nombre", payload.importer_name)
    builder.add_field("Identificación", payload.importer_id)
    builder.add_field("Dirección", payload.importer_address)

    builder.add_section_heading("Logística")
    builder.add_field("Medio de transporte", payload.transport_mode)
    builder.add_field("Puerto / Aduana de ingreso", payload.destination_port)

    builder.add_section_heading("Mercancías")
    for item in payload.items:
        parts = [
            item.description,
            f"Cant.: {_format_quantity(item.quantity)}",
            f"Unit.: {_format_currency(item.unit_value, payload.currency)}",
            f"Total: {_format_currency(item.resolved_total(), payload.currency)}",
        ]
        classification = " / ".join(filter(None, [item.hs_code, item.country_of_origin]))
        if classification:
            parts.append(f"Clasificación: {classification}")
        builder.add_bullet(" | ".join(parts))

    if not payload.items:
        builder.add_bullet("No se reportaron mercancías.")

    builder.add_section_heading("Totales")
    builder.add_field("Subtotal", _format_currency(payload.subtotal, payload.currency))
    builder.add_field("Impuestos", _format_currency(payload.tax, payload.currency))
    builder.add_field("Total factura", _format_currency(payload.total, payload.currency))

    if payload.notes:
        builder.add_section_heading("Notas")
        builder.add_paragraph(payload.notes)

    return builder.render()


@router.post("/tica-pdf", response_class=StreamingResponse)
def generate_tica_invoice_pdf(
    payload: TicaInvoicePayload,
    claims: LicenseClaims = Depends(require_extract_feature),
) -> StreamingResponse:
    """Generate a PDF tailored to the TICA customs platform requirements."""

    ensure_feature(claims, "extract")

    pdf_bytes = _build_tica_pdf(payload)
    buffer = BytesIO(pdf_bytes)
    filename = f"tica_invoice_{payload.invoice_number}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )

