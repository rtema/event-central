import datetime as dt
from decimal import Decimal
from zoneinfo import ZoneInfo

import pydyf  # type: ignore
from alembic.environment import Any
from src.events.models import Event
from src.invoices.models import INVOICE_TYPE_INVOICE, Invoice, InvoiceLineItem, Tax
from src.orders.models import Order
from src.users.models import User

# generate test user
dummy_user = User(
    email="text@tema.de",
    title="dr",
    salutation="ms",
    first_name="Lena",
    last_name="Musterfrau"
)

# generate test event
dummy_event = Event(
    id="indutest-2026",
    label={
        "de": "INDUTEST 2026 – Industriemesse",
        "en": "INDUTEST 2026 – Industrial Fair"
    },
    start_dt=dt.datetime(2026, 10, 6, 9, 0, tzinfo=ZoneInfo("Europe/Berlin")),
    end_dt=dt.datetime(2026, 10, 9, 17, 0, tzinfo=ZoneInfo("Europe/Berlin")),
)

# --- clearly-marked test recipient (industrial customer) -------------------
DUMMY_RECIPIENT = {
    "name": "Muster Stahl- und Walzwerke GmbH (TESTDATEN)",
    "address_line1": "Hochofenstraße 7",
    "postal_code": "47051",
    "city": "Duisburg",
    "country": "DE",
    "vat_id": "DE000000001",                 # obviously fake
    "email": "rechnung@example.com",
    "note": "TEST DATA / TESTDATEN – DO NOT USE IN PRODUCTION",
}

DUMMY_SUPPLIER = {

}

# generate test order
dummy_order = Order(
    # relationship sets event_id on flush
    event=dummy_event,
    external_id="ORD-2026-IND-000123",
    external_short_id="IND777",
    payment_link="https://pay.example.com/ORD-2026-IND-000123",
    link="https://portal.example.com/orders/ORD-2026-IND-000123",
    status="open",
    recipient=DUMMY_RECIPIENT,
)

# --- three tax rows --------------------------------------------------------
tax_standard = Tax(
    external_id="tax-19",
    rate=Decimal("19.00"),
    label={"de": "Umsatzsteuer 19 %", "en": "VAT 19%"},
    type="standard",
)

tax_reduced = Tax(
    external_id="tax-07",
    rate=Decimal("7.00"),
    label={
        "de": "Umsatzsteuer 7 %",
        "en": "VAT 7%"
    },
    type="standard",
)

tax_exempt = Tax(
    external_id="tax-exempt",
    rate=Decimal("0.00"),
    label={
        "de": "Steuerbefreit (Verein)",
        "en": "Tax-exempt (association)"
    },
    type="exempt-verein",
    tax_exemption_reason=(
        "Steuerbefreit gem. § 4 Nr. 22 UStG"
        "Tax-exempt under sec. 4 no. 22 German VAT Act"
    ),
)

# --- seven line items ------------------------------------------------------
dummy_line_items = [
    # 19 % standard-rated (category S)
    InvoiceLineItem(
        tax=tax_standard,
        position=1,
        quantity=Decimal("36.000"),
        price_per_unit=Decimal("145.00"),
        name="Standfläche Reihe / Row exhibition space (m²)",
        ticket=None,
        tax_category="S",
        tax_rate=Decimal("19.00"),
        tax_scheme="VAT",
        total_net=Decimal("5220.00"),
        total_tax=Decimal("991.80"),
        total_gross=Decimal("6211.80"),
    ),
    InvoiceLineItem(
        tax=tax_standard,
        position=2,
        quantity=Decimal("1.000"),
        price_per_unit=Decimal("320.00"),
        name="Starkstromanschluss 32 A / 32 A power connection",
        ticket=None,
        tax_category="S",
        tax_rate=Decimal("19.00"),
        tax_scheme="VAT",
        total_net=Decimal("320.00"),
        total_tax=Decimal("60.80"),
        total_gross=Decimal("380.80"),
    ),
    InvoiceLineItem(
        tax=tax_standard,
        position=3,
        quantity=Decimal("8.000"),
        price_per_unit=Decimal("50.00"),
        name="Fachbesucher-Tagesticket / Trade-visitor day ticket",
        ticket={"de": "Tagesticket", "en": "Day ticket"},
        tax_category="S", tax_rate=Decimal("19.00"), tax_scheme="VAT",
        total_net=Decimal("400.00"), total_tax=Decimal("76.00"), total_gross=Decimal("476.00"),
    ),
    # 7 % reduced-rated (still category S, lower rate)
    InvoiceLineItem(
        tax=tax_reduced,
        position=4,
        quantity=Decimal("3.000"),
        price_per_unit=Decimal("25.00"),
        name="Messekatalog (Druck) / Fair catalogue (print)",
        ticket=None,
        tax_category="S",
        tax_rate=Decimal("7.00"),
        tax_scheme="VAT",
        total_net=Decimal("75.00"),
        total_tax=Decimal("5.25"),
        total_gross=Decimal("80.25"),
    ),
    InvoiceLineItem(
        tax=tax_reduced,
        position=5,
        quantity=Decimal("2.000"),
        price_per_unit=Decimal("18.00"),
        name="Tagungsband (Druck) / Conference proceedings (print)",
        ticket=None,
        tax_category="S",
        tax_rate=Decimal("7.00"),
        tax_scheme="VAT",
        total_net=Decimal("36.00"),
        total_tax=Decimal("2.52"),
        total_gross=Decimal("38.52"),
    ),
    # exempt-verein (category E, 0 %, exemption reason carried on the line)
    InvoiceLineItem(
        tax=tax_exempt,
        position=6,
        quantity=Decimal("1.000"),
        price_per_unit=Decimal("500.00"),
        name="Mitgliedsbeitrag Förderverein / Association membership fee",
        ticket=None,
        tax_category="E",
        tax_rate=Decimal("0.00"),
        tax_scheme="VAT",
        tax_exemption_reason="Steuerbefreit gem. § 4 Nr. 22 UStG / Tax-exempt under sec. 4 no. 22 UStG",  # noqa: E501
        tax_exemption_reason_code="VATEX-EU-132",
        total_net=Decimal("500.00"), total_tax=Decimal("0.00"), total_gross=Decimal("500.00"),
    ),
    InvoiceLineItem(
        tax=tax_exempt,
        position=7,
        quantity=Decimal("4.000"),
        price_per_unit=Decimal("40.00"),
        name="Weiterbildungsseminar (gemeinnützig) / Training seminar (non-profit)",
        ticket=None,
        tax_category="E",
        tax_rate=Decimal("0.00"),
        tax_scheme="VAT",
        tax_exemption_reason="Steuerbefreit gem. § 4 Nr. 22 UStG / Tax-exempt under sec. 4 no. 22 UStG",  # noqa: E501
        tax_exemption_reason_code="VATEX-EU-132",
        total_net=Decimal("160.00"),
        total_tax=Decimal("0.00"),
        total_gross=Decimal("160.00"),
    ),
]

# generate test invoice
dummy_invoice = Invoice(
    # relationship sets order_id on flush
    order=dummy_order,
    document_template_id=None,
    locale="de",
    accounting_entity="DE-01",
    accounting_number=815,
    invoice_number="RE-2026-0815",
    invoice_type=INVOICE_TYPE_INVOICE,
    invoice_type_code="380",
    issue_date=dt.datetime(2026, 10, 6, 10, 30,
                           tzinfo=ZoneInfo("Europe/Berlin")),
    due_date=dt.datetime(2026, 10, 20, 10, 30,
                         tzinfo=ZoneInfo("Europe/Berlin")),
    currency="EUR",
    supplier={
        "name": "Messe Beispiel GmbH (TESTDATEN)",
        "address_line1": "Ausstellungsallee 1",
        "postal_code": "10557",
        "city": "Berlin",
        "country": "DE",
        "vat_id": "DE999999999",             # obviously fake
        "email": "buchhaltung@example.com",
        "note": "TEST DATA / TESTDATEN – DO NOT USE IN PRODUCTION",
    },
    recipient=DUMMY_RECIPIENT,                # mirror the order's recipient
    total_net=Decimal("6711.00"),
    total_tax=Decimal("1136.37"),
    total_gross=Decimal("7847.37"),
    pdf_key=None,
    xml_key=None,
    line_items=dummy_line_items,
)


def make_dummy_finisher() -> Any:

    # pyright: ignore[reportMissingParameterType, reportUnknownParameterType]
    def finisher(_document: Any, _pdf: pydyf.PDF) -> None:
        return

    return finisher
