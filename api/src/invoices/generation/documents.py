"""Top-level orchestration: turn an :class:`InvoiceDocument` into artefacts.

A single call produces both deliverables the API returns and stores:

* the **XRechnung** CII XML (:func:`build_cii_xml`), and
* the hybrid **ZUGFeRD** PDF/A-3 that embeds that very XML
  (:func:`render_zugferd_pdf`).

The same CII byte string is embedded in the PDF *and* returned as the
standalone XRechnung document, so the two artefacts can never drift apart.
"""

from __future__ import annotations

from src.document_templates.models import DocumentTemplate
from src.events.models import Event
from src.invoices.generation.cii import build_cii_xml
from src.invoices.generation.model import XRECHNUNG_SPEC_ID, InvoiceDocument
from src.invoices.generation.render import render_zugferd_pdf
from src.invoices.models import Invoice
from src.orders.models import Order


def build_documents(
    doc: InvoiceDocument,
    document_template: DocumentTemplate,
    locale: str,
    event: Event,
    order: Order,
    invoice: Invoice,
    spec_id: str = XRECHNUNG_SPEC_ID,
) -> tuple[bytes, bytes]:
    """Render ``doc`` to ``(pdf_bytes, xml_bytes)``.

    ``xml_bytes`` is a standalone XRechnung CII document; ``pdf_bytes`` is a
    PDF/A-3 with that same XML embedded as ``factur-x.xml`` (ZUGFeRD hybrid).
    An optional custom ``template_html`` / ``template_css`` controls only the
    human-readable PDF layer; the machine-readable XML is unaffected.
    """
    xml_bytes = build_cii_xml(doc, spec_id=spec_id)
    pdf_bytes = render_zugferd_pdf(
        document_template,
        locale,
        event,
        order,
        invoice,
        xml_bytes,
    )
    return pdf_bytes, xml_bytes
