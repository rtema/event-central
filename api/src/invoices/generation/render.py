"""Human-readable PDF rendering and ZUGFeRD assembly.

Produces a hybrid **ZUGFeRD** invoice: a PDF/A-3 document (rendered with
WeasyPrint) that embeds the CII XML as ``factur-x.xml`` with the ``Alternative``
relationship, plus the Factur-X XMP metadata that declares the embedded
invoice. The resulting file is both a normal, printable PDF and a
machine-readable e-invoice.

A built-in default template is used unless the caller supplies a custom one
(html/css with optional embedded fonts/images); custom templates are filled
with a small, dependency-free ``{{ placeholder }}`` substitution.
"""

from __future__ import annotations

import pydyf  # pyright: ignore[reportMissingTypeStubs]
from weasyprint import Attachment  # pyright: ignore[reportMissingTypeStubs]

from src.document_templates.models import DocumentTemplate
from src.document_templates.renderer.main import render_document
from src.events.models import Event
from src.invoices.generation.model import InvoiceDocument
from src.invoices.models import Invoice
from src.orders.models import Order

_FACTURX_NS = "urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#"
_EMBEDDED_FILENAME = "factur-x.xml"
_CONFORMANCE_LEVEL = "XRECHNUNG"

# --------------------------------------------------------------------------- #
# Factur-X XMP metadata
# --------------------------------------------------------------------------- #


def _facturx_xmp() -> str:
    return (
        f'<rdf:Description rdf:about="" xmlns:fx="{_FACTURX_NS}">'
        "<fx:DocumentType>INVOICE</fx:DocumentType>"
        f"<fx:DocumentFileName>{_EMBEDDED_FILENAME}</fx:DocumentFileName>"
        "<fx:Version>1.0</fx:Version>"
        f"<fx:ConformanceLevel>{_CONFORMANCE_LEVEL}</fx:ConformanceLevel>"
        "</rdf:Description>"
        '<rdf:Description rdf:about="" '
        'xmlns:pdfaExtension="http://www.aiim.org/pdfa/ns/extension/" '
        'xmlns:pdfaSchema="http://www.aiim.org/pdfa/ns/schema#" '
        'xmlns:pdfaProperty="http://www.aiim.org/pdfa/ns/property#">'
        "<pdfaExtension:schemas><rdf:Bag><rdf:li rdf:parseType=\"Resource\">"
        "<pdfaSchema:schema>Factur-X PDFA Extension Schema</pdfaSchema:schema>"
        f"<pdfaSchema:namespaceURI>{_FACTURX_NS}</pdfaSchema:namespaceURI>"
        "<pdfaSchema:prefix>fx</pdfaSchema:prefix>"
        "<pdfaSchema:property><rdf:Seq>"
        + "".join(
            '<rdf:li rdf:parseType="Resource">'
            f"<pdfaProperty:name>{n}</pdfaProperty:name>"
            "<pdfaProperty:valueType>Text</pdfaProperty:valueType>"
            "<pdfaProperty:category>external</pdfaProperty:category>"
            f"<pdfaProperty:description>{d}</pdfaProperty:description></rdf:li>"
            for n, d in (
                ("DocumentFileName", "name of the embedded XML invoice file"),
                ("DocumentType", "INVOICE"),
                ("Version", "the actual version of the ZUGFeRD XML schema"),
                ("ConformanceLevel", "the conformance level of the embedded data"),
            )
        )
        + "</rdf:Seq></pdfaSchema:property></rdf:li></rdf:Bag></pdfaExtension:schemas>"
        "</rdf:Description>"
    )


def _make_finisher():
    insert = _facturx_xmp().encode("utf-8")

    # pyright: ignore[reportMissingParameterType, reportUnknownParameterType]
    def finisher(_document, pdf: pydyf.PDF) -> None:
        for obj in pdf.objects:
            if not isinstance(obj, pydyf.Stream):
                continue
            if getattr(obj, "extra", {}).get("Type") != "/Metadata":
                continue
            raw = b"".join(
                x if isinstance(x, bytes) else str(x).encode() for x in obj.stream
            )
            if b"</rdf:RDF>" in raw:
                obj.stream = [raw.replace(
                    b"</rdf:RDF>", insert + b"</rdf:RDF>", 1)]
            return

    return finisher


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def render_zugferd_pdf(
    document_template: DocumentTemplate,
    locale: str,
    event: Event,
    order: Order,
    invoice: Invoice,
    cii_xml: bytes,
) -> bytes:
    """Render the ZUGFeRD PDF/A-3 embedding ``cii_xml`` as ``factur-x.xml``."""
    attachment = Attachment(
        string=cii_xml,
        name=_EMBEDDED_FILENAME,
        description="Factur-X/XRechnung invoice (CII)",
        relationship="Alternative",
    )

    data = render_document(
        document_template,
        locale,
        event,
        order=order,
        invoice=invoice,
        attachments=[attachment],
        pdf_variant="pdf/a-3b",
        finisher=_make_finisher(),
    )
    return data.getvalue()
