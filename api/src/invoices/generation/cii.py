"""UN/CEFACT Cross Industry Invoice (CII) generation.

Builds an EN16931-compliant CII document following the XRechnung 3.0 CIUS. The
very same XML is returned as the standalone *XRechnung* document and embedded in
the *ZUGFeRD* PDF (the ZUGFeRD ``XRECHNUNG`` profile is exactly an
XRechnung-conformant CII), so a single generator covers both deliverables.

Element ordering follows the CII (D16B) schema sequences, which validators are
strict about. Only stdlib :mod:`xml.etree.ElementTree` is used — no extra
dependency.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from xml.etree import ElementTree as ET

from src.invoices.generation.model import (
    XRECHNUNG_SPEC_ID,
    DocumentLine,
    InvoiceDocument,
    Party,
)

# CII namespaces.
NS = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}
for _prefix, _uri in NS.items():
    ET.register_namespace(_prefix, _uri)


def _q(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def _sub(parent: ET.Element, qname: str, text: str | None = None, **attrs: str) -> ET.Element:
    el = ET.SubElement(parent, qname, {k: v for k, v in attrs.items() if v is not None}) # type: ignore
    if text is not None:
        el.text = text
    return el


def _amount(value: Decimal) -> str:
    return f"{value:.2f}"


def _date_str(parent: ET.Element, qname: str, value: dt.date) -> None:
    el = _sub(parent, qname)
    _sub(el, _q("udt", "DateTimeString"), value.strftime("%Y%m%d"), format="102")


def _electronic_address(party: Party) -> tuple[str, str] | None:
    """Resolve BT-34/BT-49 electronic address as ``(schemeID, value)``.

    Prefers an explicit ``electronic_address`` on the party (with optional
    ``electronic_address_scheme``, e.g. ``"0204"`` for a German Leitweg-ID);
    otherwise falls back to the contact email under the EAS ``EM`` scheme.
    PEPPOL rules R010/R020 require this on the buyer and seller respectively.
    """
    addr = getattr(party, "electronic_address", None)
    if addr:
        scheme = getattr(party, "electronic_address_scheme", None) or "EM"
        return scheme, addr
    email = getattr(party, "contact_email", None)
    if email:
        return "EM", email
    return None


def _party(parent: ET.Element, qname: str, party: Party, *, is_seller: bool) -> None:
    node = _sub(parent, qname)
    _sub(node, _q("ram", "Name"), party.name or "")

    if is_seller and party.legal_registration:
        org = _sub(node, _q("ram", "SpecifiedLegalOrganization"))
        _sub(org, _q("ram", "ID"), party.legal_registration)

    # Seller contact (BG-6). XRechnung requires seller contact details.
    if is_seller and (party.contact_name or party.contact_phone or party.contact_email):
        contact = _sub(node, _q("ram", "DefinedTradeContact"))
        if party.contact_name:
            _sub(contact, _q("ram", "PersonName"), party.contact_name)
        if party.contact_phone:
            phone = _sub(contact, _q("ram", "TelephoneUniversalCommunication"))
            _sub(phone, _q("ram", "CompleteNumber"), party.contact_phone)
        if party.contact_email:
            email = _sub(contact, _q("ram", "EmailURIUniversalCommunication"))
            _sub(email, _q("ram", "URIID"), party.contact_email)

    addr = _sub(node, _q("ram", "PostalTradeAddress"))
    if party.zip_code:
        _sub(addr, _q("ram", "PostcodeCode"), party.zip_code)
    if party.line1:
        _sub(addr, _q("ram", "LineOne"), party.line1)
    if party.line2:
        _sub(addr, _q("ram", "LineTwo"), party.line2)
    if party.line3:
        _sub(addr, _q("ram", "LineThree"), party.line3)
    if party.city:
        _sub(addr, _q("ram", "CityName"), party.city)
    _sub(addr, _q("ram", "CountryID"), (party.country or "DE").upper())

    # BT-34 (seller) / BT-49 (buyer) electronic address. Must sit between the
    # postal address and the tax registration per the CII schema sequence.
    endpoint = _electronic_address(party)
    if endpoint is not None:
        scheme, value = endpoint
        uri = _sub(node, _q("ram", "URIUniversalCommunication"))
        _sub(uri, _q("ram", "URIID"), value, schemeID=scheme)

    if party.vat_id:
        reg = _sub(node, _q("ram", "SpecifiedTaxRegistration"))
        _sub(reg, _q("ram", "ID"), party.vat_id, schemeID="VA")


def _line_item(parent: ET.Element, line: DocumentLine) -> None:
    item = _sub(parent, _q("ram", "IncludedSupplyChainTradeLineItem"))

    doc = _sub(item, _q("ram", "AssociatedDocumentLineDocument"))
    _sub(doc, _q("ram", "LineID"), str(line.position))

    product = _sub(item, _q("ram", "SpecifiedTradeProduct"))
    name = line.name if not line.ticket_label else f"{line.name} ({line.ticket_label})"
    _sub(product, _q("ram", "Name"), name)

    agreement = _sub(item, _q("ram", "SpecifiedLineTradeAgreement"))
    net_price = _sub(agreement, _q("ram", "NetPriceProductTradePrice"))
    _sub(net_price, _q("ram", "ChargeAmount"), _amount(line.net_unit_price))

    delivery = _sub(item, _q("ram", "SpecifiedLineTradeDelivery"))
    _sub(delivery, _q("ram", "BilledQuantity"), f"{line.quantity:g}", unitCode="C62")

    settlement = _sub(item, _q("ram", "SpecifiedLineTradeSettlement"))
    tax = _sub(settlement, _q("ram", "ApplicableTradeTax"))
    _sub(tax, _q("ram", "TypeCode"), line.tax_scheme)
    if line.tax_category == "E" and line.exemption_reason:
        _sub(tax, _q("ram", "ExemptionReason"), line.exemption_reason)
    _sub(tax, _q("ram", "CategoryCode"), line.tax_category)
    if line.tax_category == "E" and line.exemption_reason_code:
        _sub(tax, _q("ram", "ExemptionReasonCode"), line.exemption_reason_code)
    _sub(tax, _q("ram", "RateApplicablePercent"), _amount(line.tax_rate))

    summation = _sub(settlement, _q("ram", "SpecifiedTradeSettlementLineMonetarySummation"))
    _sub(summation, _q("ram", "LineTotalAmount"), _amount(line.net))


# BT-23 Business process type. PEPPOL/EN16931 (rule PEPPOL-EN16931-R001) requires
# this. The standard PEPPOL BIS Billing 3.0 value, also used by XRechnung.
DEFAULT_BUSINESS_PROCESS = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"


def build_cii_xml(
    doc: InvoiceDocument,
    *,
    spec_id: str = XRECHNUNG_SPEC_ID,
    business_process: str = DEFAULT_BUSINESS_PROCESS,
) -> bytes:
    """Render ``doc`` as an EN16931 CII XML document (UTF-8 bytes)."""
    root = ET.Element(_q("rsm", "CrossIndustryInvoice"))

    # 1) Document context — the business process (BT-23) and guideline / CIUS
    #    (BT-24) this document conforms to. BusinessProcess MUST come first per
    #    the CII (D16B) schema sequence.
    ctx = _sub(root, _q("rsm", "ExchangedDocumentContext"))
    process = _sub(ctx, _q("ram", "BusinessProcessSpecifiedDocumentContextParameter"))
    _sub(process, _q("ram", "ID"), business_process)
    guideline = _sub(ctx, _q("ram", "GuidelineSpecifiedDocumentContextParameter"))
    _sub(guideline, _q("ram", "ID"), spec_id)

    # 2) Document header (BT-1/BT-3/BT-2 + notes).
    header = _sub(root, _q("rsm", "ExchangedDocument"))
    _sub(header, _q("ram", "ID"), doc.invoice_number)
    _sub(header, _q("ram", "TypeCode"), doc.invoice_type_code)
    _date_str(header, _q("ram", "IssueDateTime"), doc.issue_date)
    for note in doc.notes:
        note_el = _sub(header, _q("ram", "IncludedNote"))
        _sub(note_el, _q("ram", "Content"), note)

    # 3) The trade transaction.
    txn = _sub(root, _q("rsm", "SupplyChainTradeTransaction"))
    for line in doc.lines:
        _line_item(txn, line)

    # 3a) Agreement: buyer reference + the two parties.
    agreement = _sub(txn, _q("ram", "ApplicableHeaderTradeAgreement"))
    _sub(agreement, _q("ram", "BuyerReference"), doc.buyer_reference or "N/A")
    _party(agreement, _q("ram", "SellerTradeParty"), doc.supplier, is_seller=True)
    _party(agreement, _q("ram", "BuyerTradeParty"), doc.recipient, is_seller=False)
    if doc.order_external_id:
        order_ref = _sub(agreement, _q("ram", "BuyerOrderReferencedDocument"))
        _sub(order_ref, _q("ram", "IssuerAssignedID"), doc.order_external_id)

    # 3b) Delivery (mandatory element; left empty — no delivery details).
    _sub(txn, _q("ram", "ApplicableHeaderTradeDelivery"))

    # 3c) Settlement: currency, payment means, VAT breakdown, terms, totals.
    settlement = _sub(txn, _q("ram", "ApplicableHeaderTradeSettlement"))
    _sub(settlement, _q("ram", "PaymentReference"), doc.invoice_number)
    _sub(settlement, _q("ram", "InvoiceCurrencyCode"), doc.currency)

    if doc.supplier.iban:
        means = _sub(settlement, _q("ram", "SpecifiedTradeSettlementPaymentMeans"))
        _sub(means, _q("ram", "TypeCode"), "58")  # SEPA credit transfer
        account = _sub(means, _q("ram", "PayeePartyCreditorFinancialAccount"))
        _sub(account, _q("ram", "IBANID"), doc.supplier.iban)

    for entry in doc.tax_breakdown:
        tax = _sub(settlement, _q("ram", "ApplicableTradeTax"))
        _sub(tax, _q("ram", "CalculatedAmount"), _amount(entry.amount))
        _sub(tax, _q("ram", "TypeCode"), "VAT")
        if entry.category == "E" and entry.exemption_reason:
            _sub(tax, _q("ram", "ExemptionReason"), entry.exemption_reason)
        _sub(tax, _q("ram", "BasisAmount"), _amount(entry.basis))
        _sub(tax, _q("ram", "CategoryCode"), entry.category)
        if entry.category == "E" and entry.exemption_reason_code:
            _sub(tax, _q("ram", "ExemptionReasonCode"), entry.exemption_reason_code)
        _sub(tax, _q("ram", "RateApplicablePercent"), _amount(entry.rate))

    if doc.due_date:
        terms = _sub(settlement, _q("ram", "SpecifiedTradePaymentTerms"))
        _date_str(terms, _q("ram", "DueDateDateTime"), doc.due_date)

    money_sum = _sub(settlement, _q("ram", "SpecifiedTradeSettlementHeaderMonetarySummation"))
    _sub(money_sum, _q("ram", "LineTotalAmount"), _amount(doc.total_net))
    _sub(money_sum, _q("ram", "TaxBasisTotalAmount"), _amount(doc.total_net))
    _sub(
        money_sum,
        _q("ram", "TaxTotalAmount"),
        _amount(doc.total_tax),
        currencyID=doc.currency,
    )
    _sub(money_sum, _q("ram", "GrandTotalAmount"), _amount(doc.total_gross))
    _sub(money_sum, _q("ram", "DuePayableAmount"), _amount(doc.total_gross))

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)