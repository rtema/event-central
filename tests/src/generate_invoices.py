#!/usr/bin/env python3
"""
Event Central -- invoice API fuzzer.

Authenticates against the Event Central API (OAuth2 password / refresh-token, or
a long-lived API key), caches the token on disk, then generates randomized
invoice-creation requests on the fly and checks every response against a set of
invariants. The goal is to surface bugs in the API implementation: broken money
math, malformed invoice numbers, undecodable documents, 500s, and error
responses that don't follow the documented Error schema.

Every run uses a base seed (printed at startup) and each invoice gets its own
derived seed, so any failing case can be reproduced exactly with
    --seed <base> --only <index>

USAGE
    python event_central_invoices.py --init                 # write a .env template
    python event_central_invoices.py                        # fuzz with the default settings
    python event_central_invoices.py --count 200            # send 200 invoices
    python event_central_invoices.py --seed 12345           # reproducible run
    python event_central_invoices.py --seed 12345 --only 7  # re-run ONLY the case that failed
    python event_central_invoices.py --no-edge              # benign random data only, no edge cases
    python event_central_invoices.py --dry-run              # print generated bodies, send nothing
    python event_central_invoices.py --login | --whoami     # auth helpers

    # Override the server (default: $API_BASE_URL or http://localhost:7435):
    python event_central_invoices.py --base-url https://eu-01.event-central.tema-dev.de

REQUIRES
    pip install requests faker python-dotenv
"""

from __future__ import annotations

import argparse
import base64
import datetime
import json
import os
import random
import string
import time
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, cast
from xml.etree import ElementTree

import requests
from dotenv import dotenv_values
from faker import Faker

from src.generate_template import make_invoice_template

# ======================================================================
#  CONFIGURATION  -- edit these to match your environment.
# ======================================================================

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:7435")

HERE = Path(__file__).resolve().parent
# USER / PASSWORD (and optional API_KEY / CLIENT_ID)
ENV_FILE = HERE / ".." / ".env"
# cached access / refresh token (chmod 600)
TOKEN_FILE = HERE / ".." / ".token.json"
# every sent request: {invoiceNumber|request-NNNN}.json (+ .pdf/.xml on success)
OUTPUT_DIR = HERE / ".." / "invoices"
# request + response of every failing case
FAILURES_DIR = HERE / ".." / "failures"

REQUESTED_SCOPES = "invoices:write:all invoices:read:all"
EXPIRY_BUFFER_SECONDS = 60
REQUEST_TIMEOUT = 120

# ---- Fuzzing knobs ----
RUN_COUNT = 25                  # how many invoices to generate per run
INCLUDE_EDGE_CASES = True       # inject weird/boundary values to probe robustness
# save the request JSON for every sent invoice (PDF/XML too on success)
SAVE_OUTPUTS = True
SAVE_FAILURES = True            # dump request+response to FAILURES_DIR on any failure
STOP_ON_FIRST_FAILURE = False   # halt as soon as one invoice fails its checks

# Money comparison tolerances, in currency units.
# accounting identities must hold (net+tax==gross, sums)
TIGHT_TOLERANCE = 0.005
ROUNDING_TOLERANCE = 0.02  # derived net/tax may differ by the server's rounding model

# Pseudo-random data generation.
FAKER_LOCALE = "de_DE"   # used only if Faker is installed
# shared pool of events invoices are spread across (>= 20)
EVENT_POOL_SIZE = 25


# ======================================================================
#  Credentials  -- read entirely from the .env file (see Credentials docstring).
# ======================================================================

@dataclass
class Credentials:
    """
    Authentication, read entirely from the .env file:
        USER=you@example.com
        PASSWORD=secret
        # optional:
        # API_KEY=...        long-lived key, used instead of USER/PASSWORD
        # CLIENT_ID=invoice-fuzzer

    Provide EITHER an API_KEY OR USER + PASSWORD.
    """

    client_id: str = "invoice-fuzzer"
    api_key: str | None = None
    username: str | None = None
    password: str | None = None

    @classmethod
    def load(cls) -> "Credentials":
        # dotenv_values reads the FILE only and does NOT touch os.environ. That
        # matters: 'USER' is also a standard shell variable, so reading it from
        # the process environment would pick up your OS login name instead.
        env = dotenv_values(ENV_FILE)
        return cls(
            client_id=env.get("CLIENT_ID") or "invoice-fuzzer",
            api_key=env.get("API_KEY"),
            username=env.get("USER"),
            password=env.get("PASSWORD"),
        )

    def can_password_login(self) -> bool:
        return bool(self.username and self.password)


# ======================================================================
#  Token cache  -- persisted so we don't log in every run.
# ======================================================================

@dataclass
class Token:
    access_token: str
    refresh_token: str | None = None
    scope: str | None = None
    token_type: str = "Bearer"
    expires_at: float = 0.0   # epoch seconds; 0.0 == no known expiry

    def is_valid(self) -> bool:
        if not self.access_token:
            return False
        if self.expires_at == 0.0:
            return True
        return time.time() < (self.expires_at - EXPIRY_BUFFER_SECONDS)

    @classmethod
    def load(cls) -> "Token | None":
        if not TOKEN_FILE.exists():
            return None
        try:
            return cls(**json.loads(TOKEN_FILE.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, TypeError):
            return None

    def save(self) -> None:
        TOKEN_FILE.write_text(json.dumps(
            self.__dict__, indent=2), encoding="utf-8")
        try:
            os.chmod(TOKEN_FILE, 0o600)
        except OSError:
            pass


# ======================================================================
#  Errors
# ======================================================================

class AuthError(RuntimeError):
    """Authentication failed or is impossible."""


def _describe_auth_error(resp: requests.Response) -> str:
    try:
        d = resp.json()
        return f"Auth failed (HTTP {resp.status_code}): " + (
            d.get("error_description") or d.get("error") or resp.text
        )
    except ValueError:
        return f"Auth failed (HTTP {resp.status_code}): {resp.text[:300]}"


# ======================================================================
#  API client
# ======================================================================

class EventCentralClient:
    _token: Token | None = None

    def __init__(self, base_url: str = API_BASE_URL, credentials: Credentials | None = None):
        self.base_url = base_url.rstrip("/")
        self.credentials = credentials or Credentials.load()
        self.session = requests.Session()
        self._token: Token | None = None

    # ---- token lifecycle -------------------------------------------------

    def _access_token(self) -> str:
        if self.credentials.api_key:
            return self.credentials.api_key

        if self._token is None:
            self._token = Token.load()
        if self._token and self._token.is_valid():
            return self._token.access_token

        if self._token and self._token.refresh_token:
            try:
                self._token = self._grant_refresh(self._token.refresh_token)
                self._token.save()
                return self._token.access_token
            except AuthError:
                pass

        if self.credentials.can_password_login():
            self._token = self._grant_password()
            self._token.save()
            return self._token.access_token

        raise AuthError(
            "No valid token and no way to get one. Set USER and PASSWORD in .env "
            "(or an API_KEY). Run with --init to create the template."
        )

    def _token_request(self, payload: dict[str, Any]) -> Token:
        resp = self.session.post(
            f"{self.base_url}/auth/token", json=payload, timeout=REQUEST_TIMEOUT
        )
        if resp.status_code != 200:
            raise AuthError(_describe_auth_error(resp))
        d = resp.json()
        expires_in = d.get("expires_in") or 0
        return Token(
            access_token=d["access_token"],
            refresh_token=d.get("refresh_token"),
            scope=d.get("scope"),
            token_type=d.get("token_type", "Bearer"),
            expires_at=(time.time() + expires_in) if expires_in else 0.0,
        )

    def _grant_password(self) -> Token:
        return self._token_request({
            "grant_type": "password",
            "username": self.credentials.username,
            "password": self.credentials.password,
            "client_id": self.credentials.client_id,
            "scope": REQUESTED_SCOPES,
        })

    def _grant_refresh(self, refresh_token: str) -> Token:
        tok = self._token_request({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.credentials.client_id,
        })
        if not tok.refresh_token:
            tok.refresh_token = refresh_token
        return tok

    def login(self) -> None:
        if self.credentials.api_key:
            print("Using a long-lived API key -- nothing to fetch.")
            return
        self._token = None
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
        self._access_token()
        print(
            f"Logged in. Granted scopes: {self._token.scope if self._token is not None else '(none reported)'}")

    # ---- requests --------------------------------------------------------

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._access_token()}"
        return self.session.request(
            method, f"{self.base_url}{path}",
            headers=headers, timeout=REQUEST_TIMEOUT, **kwargs,
        )

    def whoami(self) -> dict[str, Any]:
        resp = self.request("GET", "/auth/userinfo")
        resp.raise_for_status()
        return resp.json()

    def post_invoice(self, body: dict[str, Any]) -> requests.Response:
        # Returns the raw response so the validator can inspect any status.
        return self.request("POST", "/api/v1/invoices", json=body)


# ======================================================================
#  Money helpers
# ======================================================================

def round2(x: float) -> float:
    """Round to 2 decimals, half-up (the usual accounting convention)."""
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def close(a: float, b: float, tol: float) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


# ======================================================================
#  Random invoice generation
#  Each invoice is built from its own seeded RNG so it is reproducible.
#  Realistic data comes from Faker; WEIRD_NAMES feeds the edge cases.
# ======================================================================

WEIRD_NAMES = ["Ticket \U0001f3ab", "Voll-Paket (inkl. MwSt.)", "  leading/trailing  ", "Ünïcödé Posten",
               "X" * 240, "Line\nbreak", "Quote\"inside", "Sonder & Zeichen <tag>"]
TAX_EXEMPTION_REASONS = [
    "Gemeinnütziger Verein nach §52 AO",
    "Kleinunternehmer nach §19 UStG"
]


def _rand_string(rng: random.Random, n: int = 6) -> str:
    return "".join(rng.choice(string.ascii_uppercase + string.digits) for _ in range(n))


def _rand_date(rng: random.Random, min: int, max: int) -> str:
    offset = rng.randint(min, max)
    date = datetime.date.today() + datetime.timedelta(days=offset)
    return date.isoformat()


def make_tax_pool(rng: random.Random) -> list[dict[str, Any]]:
    """Build the set of tax rates this invoice's line items may reference."""
    pool: list[dict[str, Any]] = [
        {
            "externalId": "vat19",
            "rate": 19,
            "label": "USt 19%",
            "type": "standard"
        },
        {
            "externalId": "vat7",
            "rate": 7,
            "label": "USt 7%",
            "type": "standard"
        },
    ]
    if rng.random() < 0.3:
        pool.append({
            "externalId": "exempt",
            "rate": 0,
            "label": "Steuerbefreit",
            "type": "exempt-verein",
            "taxExemptionReason": rng.choice(TAX_EXEMPTION_REASONS),
        })
    return pool


def _slugify(text: str, rng: random.Random) -> str:
    """Make an event id of allowed chars: lowercase letters, numbers, '-' and '_'."""
    slug = "".join(c if (c.isalnum() and c.isascii())
                   else "-" for c in text.lower())
    slug = "-".join(part for part in slug.split("-")
                    if part)  # collapse repeats
    return slug or f"event-{rng.randint(1000, 9999)}"


def seed_faker(fake: Faker, rng: random.Random) -> Faker:
    """Reseed the shared Faker instance from `rng` so its output stays reproducible."""
    fake.seed_instance(rng.getrandbits(64))
    return fake


def build_event_pool(base_seed: int, size: int, fake: Faker) -> list[dict[str, str]]:
    """
    Build a shared pool of events (at least `size`, default >= 20) that invoices
    are spread across. Deterministic for a given base seed, so runs reproduce.
    """
    rng = random.Random(f"{base_seed}:eventpool")
    seed_faker(fake, rng)
    kinds = ["Summit", "Expo", "Forum", "Kongress",
             "Festival", "Conference", "Messe"]
    pool: list[dict[str, str]] = []
    seen: set[str] = set()
    for _i in range(size):
        label = f"{fake.city()} {rng.choice(kinds)} 20{rng.randint(24, 29):02d}"
        slug = f"{_slugify(label, rng)}"
        while slug in seen:
            slug = f"{slug}-{rng.randint(0, 999)}"
        seen.add(slug)
        pool.append({"id": slug, "label": label})
    return pool


def _make_supplier(rng: random.Random, fake: Faker) -> dict[str, Any]:
    """A pseudo-random supplier (the party issuing the invoice)."""
    company = fake.company()
    city = fake.city()
    return {
        "legalName": company,
        "legalRegistration": f"Handelsregister {city}, HRB {rng.randint(1000, 99999)}",
        "vatId": "DE" + "".join(rng.choice(string.digits) for _ in range(9)),
        "iban": fake.iban(),
        "line1": company,
        "line2": fake.street_address(),
        "city": city,
        "zipCode": fake.postcode(),
        "country": "de",
        "contactName": fake.name(),
        "contactPhone": fake.phone_number(),
        "contactEmail": fake.company_email(),
    }


def _make_accounting_entity(rng: random.Random, supplier_name: str) -> dict[str, Any]:
    """
    A pseudo-random accounting entity (Rechnungskreis). The prefix is built from
    the supplier's initials plus a 2-digit year, so it correlates with the
    supplier the way a real numbering circle would. firstInvoiceNumber and
    padNumber are randomized too, to exercise the server's number formatting.
    """
    letters = "".join(c for c in supplier_name.upper()
                      if c.isalpha() and c.isascii())[:4]
    while len(letters) < 3:
        letters += rng.choice(string.ascii_uppercase)
    return {
        "prefix": f"{letters}{rng.randint(22, 29):02d}-",
        "firstInvoiceNumber": rng.randint(1, 500),
        "padNumber": rng.choice([4, 5, 6]),
    }


def _make_order_links(rng: random.Random, order_id: str, event_id: str) -> dict[str, str]:
    return {
        "paymentLink": f"{API_BASE_URL}/tests/event/{event_id}/orders/{order_id}",
        "orderLink": f"{API_BASE_URL}/tests/event/{event_id}/orders/{order_id}/pay"
    }


def _make_invoice_template(rng: random.Random, locale: str) -> dict[str, Any]:
    if rng.random() < 0.5:
        return {
            "templateName": "invoice-de-v01"
        }
    else:
        return make_invoice_template(rng, locale)


def _make_recipient(rng: random.Random, fake: Faker, edge: bool) -> dict[str, Any]:
    company = fake.company()
    first_name = fake.first_name()
    last_name = fake.last_name()
    recipient: dict[str, Any] = {
        "city": fake.city(),
        "zipCode": fake.postcode(),
        "country": rng.choice(["de", "fr", "be"]),
        "contactSalutation": rng.choice(["mr", "ms", "mx"]),
        "contactTitle": rng.choice(["dr", "prof", "prof-dr"]),
        "contactFirstname": first_name,
        "contactLastname": last_name,
        "contactPhone": fake.phone_number(),
        "contactEmail": f"{_slugify(first_name, rng)}.{_slugify(last_name, rng)}@{_slugify(company, rng)}.{fake.tld()}",
    }

    if rng.random() < 0.6:
        recipient["line1"] = company
        recipient["line2"] = fake.street_address()
    else:
        recipient["line1"] = f"{first_name} {last_name}"
        recipient["line2"] = company
        recipient["line3"] = fake.street_address()

    if rng.random() < 0.6:
        recipient["vatId"] = "DE" + \
            "".join(rng.choice(string.digits) for _ in range(9))

    if rng.random() < 0.3:
        recipient["purchaseOrderReference"] = "PO-" + _rand_string(rng)

    # Edge: randomly drop optional fields to test how the server copes.
    if edge and rng.random() < 0.25:
        for k in list(recipient):
            if k not in ("line2", "line3", "contactSalutation", "contactTitle", "contactPhone") and rng.random() < 0.3:
                recipient.pop(k)

    return recipient


def _make_line_item(
        rng: random.Random,
        tax_pool: list[dict[str, Any]],
        fake: Faker,
        edge: bool
) -> tuple[dict[str, Any], list[str]]:
    """Return (lineItem, anomalies) where anomalies note any boundary values used."""
    anomalies: list[str] = []
    tax = rng.choice(tax_pool)

    quantity: float = rng.randint(1, 10)
    price: float = round2(rng.uniform(5, 2000))

    if edge:
        roll = rng.random()
        if roll < 0.08:
            quantity = 0
            anomalies.append("quantity=0")
        elif roll < 0.13:
            quantity = round(rng.uniform(0.1, 3.5), 3)
            anomalies.append("fractional-quantity")
        elif roll < 0.16:
            quantity = 100000
            anomalies.append("huge-quantity")

        roll = rng.random()
        if roll < 0.08:
            price = 0.0
            anomalies.append("price=0")
        elif roll < 0.13:
            price = -round2(rng.uniform(5, 500))
            anomalies.append("negative-price")
        elif roll < 0.18:
            # extra decimals -> rounding probe
            price = round(rng.uniform(0, 1), 4)
            anomalies.append("sub-cent-price")
        elif roll < 0.22:
            price = round2(rng.uniform(50000, 1_000_000))
            anomalies.append("huge-price")

    if edge and rng.random() < 0.25:
        name = rng.choice(WEIRD_NAMES)
    else:
        name = f"{fake.word().title()} {rng.choice(['Ticket', 'Paket', 'Stand', 'Workshop'])}"
    if len(name) >= 200:
        anomalies.append("very-long-name")

    item: dict[str, Any] = {
        "quantity": quantity,
        "pricePerUnit": price,
        "externalTaxId": tax["externalId"],
        "name": name,
    }
    return item, anomalies


def generate_invoice(seed_material: str, edge_cases: bool,
                     event_pool: list[dict[str, str]], fake: Faker
                     ) -> tuple[dict[str, Any], list[str]]:
    """
    Build one randomized invoice body plus a list of anomalies (for repro/context).
    `seed_material` makes the result deterministic given the same base seed + index.
    `event_pool` is the shared list of events to draw from; `fake` is an optional
    Faker instance for realistic data.
    """
    rng = random.Random(seed_material)
    seed_faker(fake, rng)  # tie Faker's output to this invoice's seed
    anomalies: list[str] = []
    edge = edge_cases and rng.random() < 0.5  # ~half the invoices stay "clean"

    tax_pool = make_tax_pool(rng)
    n_lines = rng.randint(1, 4)
    if edge:
        roll = rng.random()
        if roll < 0.1:
            n_lines = 0
            anomalies.append("zero-line-items")
        elif roll < 0.2:
            n_lines = 60
            anomalies.append("many-line-items")

    line_items: list[dict[str, Any]] = []
    for _ in range(n_lines):
        item, item_anoms = _make_line_item(rng, tax_pool, fake, edge)
        line_items.append(item)
        anomalies.extend(item_anoms)

    supplier = _make_supplier(rng, fake)
    event = rng.choice(event_pool) if event_pool else {
        "id": "fallback-event", "label": "Fallback"
    }
    order_id = _rand_string(rng, 10)
    locale = rng.choice(["de", "en"])

    body: dict[str, Any] = {
        "externalOrderId": f"ORD-{order_id}",
        "externalOrderShortId": f"#{order_id}",
        "locale": locale,
        "currency": "EUR",
        "dueDate": _rand_date(rng, 0, 365),
        "accountingEntity": _make_accounting_entity(rng, event["label"]),
        "event": {"id": event["id"], "label": event["label"]},
        "links": _make_order_links(rng, order_id, event["id"]),
        "supplier": supplier,
        "recipient": _make_recipient(rng, fake, edge),
        "taxRates": tax_pool,
        "lineItems": line_items,
        "invoiceTemplate": _make_invoice_template(rng, locale)
    }

    # Edge: drop a required-ish field entirely to test validation/error envelopes.
    if edge and rng.random() < 0.1:
        victim = rng.choice(
            ["recipient", "lineItems", "event", "externalOrderShortId"])
        body.pop(victim, None)
        anomalies.append(f"missing:{victim}")

    # Edge: drop a due date that is before now
    if edge and rng.random() < 0.1:
        body["dueDate"] = _rand_date(rng, -14, -1)
        anomalies.append("due-date-before-now")

    return body, sorted(set(anomalies))


# ======================================================================
#  Response validation  -- the part that actually catches API bugs.
#  We assert invariants that must hold regardless of the server's exact
#  rounding rules, so we don't get false positives on legitimate choices.
# ======================================================================

@dataclass
class Report:
    index: int
    seed_material: str
    anomalies: list[str]
    status: int

    # definite bugs
    errors: list[str] = field(default_factory=list[str])

    # suspicious, needs a human
    warnings: list[str] = field(default_factory=list[str])

    @property
    def ok(self) -> bool:
        return not self.errors


def _expected_line_money(quantity: float, price: float, rate: float) -> tuple[float, float, float]:
    gross = round2(quantity * price)
    net = gross if rate == 0 else round2(gross / (1 + rate / 100))
    return gross, net, round2(gross - net)


def validate(body: dict[str, Any], resp: requests.Response, report: Report) -> None:
    status = resp.status_code

    # A server error is always a bug, whatever we sent.
    if status >= 500:
        report.errors.append(f"server error {status} (input should never 500)")
        return

    if status == 201:
        _validate_success(body, resp, report)
    elif 400 <= status < 500:
        _validate_error_envelope(resp, report)
        # The fuzzer only sends deliberately-invalid data on "edge" invoices,
        # and every such deviation is recorded in report.anomalies. A clean
        # invoice (no anomalies) is valid input the server MUST accept, so a
        # 4xx rejection of one -- e.g. a 422 Unprocessable Entity -- is a bug,
        # not a pass. Without this check those rejections slipped through as OK
        # because the envelope checks below only ever raise warnings.
        if not report.anomalies:
            report.errors.append(
                f"client error {status} on a clean invoice "
                f"(valid input should be accepted, not rejected)")
    else:
        report.warnings.append(
            f"unexpected status {status} (expected 201 or 4xx)")


def _validate_error_envelope(resp: requests.Response, report: Report) -> None:
    # The spec's Error schema requires at least `error`; code/correlationId help debugging.
    try:
        d = resp.json()
    except ValueError:
        report.warnings.append(
            "4xx response body is not JSON (Error schema expected)")
        return
    if not isinstance(d, dict) or "error" not in d:
        report.warnings.append("4xx body missing required 'error' field")
    if "correlationId" not in d:
        report.warnings.append(
            "4xx body has no correlationId (harder to trace in logs)")


def _validate_success(body: dict[str, Any], resp: requests.Response, report: Report) -> None:
    try:
        data = resp.json()
    except ValueError:
        report.errors.append("201 response is not valid JSON")
        return

    raw_invoice = data.get("invoice")
    if not isinstance(raw_invoice, dict):
        report.errors.append("201 response has no 'invoice' object")
        return
    invoice: dict[str, Any] = data.get("invoice")
    invoices_lines: list[dict[str, Any]] = data.get("invoiceLines") or []

    # --- echoed scalar fields ---
    if "currency" in body and invoice.get("currency") not in (None, body["currency"]):
        report.errors.append(
            f"currency not echoed: sent {body['currency']!r}, got {invoice.get('currency')!r}")
    if "locale" in body and invoice.get("locale") not in (None, body["locale"]):
        report.warnings.append(
            f"locale not echoed: sent {body['locale']!r}, got {invoice.get('locale')!r}")

    # --- invoice number format: prefix + numeric == accountingNumber ---
    prefix = invoice.get("accountingEntity")
    number = invoice.get("invoiceNumber")
    acc_no = invoice.get("accountingNumber")
    if isinstance(number, str) and isinstance(prefix, str):
        if not number.startswith(prefix):
            report.errors.append(
                f"invoiceNumber {number!r} does not start with prefix {prefix!r}")
        else:
            numeric = number[len(prefix):]
            if not numeric.isdigit():
                report.errors.append(
                    f"invoiceNumber tail {numeric!r} is not all digits")
            elif acc_no is not None and int(numeric) != int(acc_no):
                report.errors.append(
                    f"invoiceNumber tail ({numeric}) != accountingNumber ({acc_no})")
    else:
        report.warnings.append(
            "invoiceNumber / accountingEntity missing or not strings")

    # --- per-line money self-consistency (independent of rounding model) ---
    sum_net = sum_tax = sum_gross = 0.0
    for i, line in enumerate(invoices_lines):
        q = line.get("quantity")
        p = line.get("pricePerUnit")
        rate = line.get("taxRate")

        net: float | None = line.get("totalNet", None)
        tax: float | None = line.get("totalTax", None)
        gross: float | None = line.get("totalGross", None)

        if net is None:
            report.errors.append(
                f"line {i}: missing totalNet")
            continue
        if tax is None:
            report.errors.append(
                f"line {i}: missing totalTax")
            continue
        if gross is None:
            report.errors.append(
                f"line {i}: missing totalGross")
            continue

        # Hard identity: gross must equal net + tax exactly (to the cent).
        if not close(gross, (net or 0) + (tax or 0), TIGHT_TOLERANCE):
            report.errors.append(
                f"line {i}: totalNet+totalTax ({round2((net or 0)+(tax or 0))}) != totalGross ({gross})")

        # gross should match quantity * unit price (price is tax-inclusive per spec).
        if q is not None and p is not None and not close(gross, q * p, TIGHT_TOLERANCE):
            report.errors.append(
                f"line {i}: totalGross ({gross}) != quantity*pricePerUnit ({round2(q * p)})")

        # net derived from gross and the rate -- looser, rounding may differ.
        if rate is not None and q is not None and p is not None:
            _, exp_net, _ = _expected_line_money(q, p, rate)
            if not close(net, exp_net, ROUNDING_TOLERANCE):
                report.warnings.append(
                    f"line {i}: totalNet ({net}) differs from expected {exp_net} (rate {rate}%)")

        sum_net += net or 0
        sum_tax += tax or 0
        sum_gross += gross or 0

    # --- invoice totals must equal the sum of the line totals ---
    inv_net: float | None = invoice.get("totalNet")
    inv_tax: float | None = invoice.get("totalTax")
    inv_gross: float | None = invoice.get("totalGross")
    if invoices_lines:
        if inv_net is not None and not close(inv_net, sum_net, TIGHT_TOLERANCE):
            report.errors.append(
                f"invoice totalNet ({inv_net}) != sum of lines ({round2(sum_net)})")
        if inv_tax is not None and not close(inv_tax, sum_tax, TIGHT_TOLERANCE):
            report.errors.append(
                f"invoice totalTax ({inv_tax}) != sum of lines ({round2(sum_tax)})")
        if inv_gross is not None and not close(inv_gross, sum_gross, TIGHT_TOLERANCE):
            report.errors.append(
                f"invoice totalGross ({inv_gross}) != sum of lines ({round2(sum_gross)})")
    if (inv_net is not None and
                inv_tax is not None and
                inv_gross is not None and
            not close(inv_gross, inv_net + inv_tax, TIGHT_TOLERANCE)
            ):
        report.errors.append(
            f"invoice totalNet+totalTax ({round2(inv_net + inv_tax)}) != totalGross ({inv_gross})")

    # --- the generated documents must actually be valid PDF / XML ---
    _validate_pdf(data.get("invoicePdf"), report)
    _validate_xml(data.get("invoiceXml"), report)


def _validate_pdf(b64: Any, report: Report) -> None:
    if not b64:
        report.warnings.append("response has no invoicePdf")
        return
    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception:
        report.errors.append("invoicePdf is not valid base64")
        return
    if not raw.startswith(b"%PDF"):
        report.errors.append("invoicePdf does not start with %PDF")


def _validate_xml(b64: Any, report: Report) -> None:
    if not b64:
        report.warnings.append("response has no invoiceXml")
        return
    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception:
        report.errors.append("invoiceXml is not valid base64")
        return
    try:
        ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        report.errors.append(f"invoiceXml is not well-formed XML: {exc}")


# ======================================================================
#  Output capture  -- persist every request (and documents on success)
# ======================================================================

def _safe_filename(name: str) -> str:
    """Keep only filename-safe characters; fall back to a timestamp."""
    safe = "".join(c for c in str(name) if c.isalnum() or c in "-_.")
    return safe or f"invoice-{int(time.time())}"


def save_request_body(body: dict[str, Any], output_dir: Path, stem: str) -> Path:
    """Write a single request body to `output_dir`/`stem`.json and return the path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    req_path = output_dir / f"{stem}.json"
    req_path.write_text(json.dumps(
        body, indent=2, ensure_ascii=False), encoding="utf-8")
    return req_path


def save_invoice_files(body: dict[str, Any], resp: requests.Response,
                       output_dir: Path, index: int) -> list[Path]:
    """
    Persist EVERY sent request into `output_dir`, regardless of the response
    status:
        {stem}.json   the request body we sent

    For a successful (201) response, the decoded documents are written too:
        {stem}.pdf    decoded ZUGFeRD PDF
        {stem}.xml    decoded XRechnung XML

    `stem` is the server-assigned invoiceNumber when one is available (the usual
    case for 201s) and otherwise `request-{index:04d}`, so failed/rejected
    requests still land on disk under a stable, reproducible name.
    Returns the list of files written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Parse the response if we can; a non-201 (or non-JSON) response simply has
    # no invoice object / documents, and we fall back to an index-based name.
    # resp.json() is typed Any, so cast the parsed payload to a concrete dict
    # type -- otherwise isinstance-narrowing leaves it as dict[Unknown, Unknown]
    # and every downstream .get() reads as "partially unknown".
    try:
        parsed: Any = resp.json()
    except ValueError:
        parsed = None
    data: dict[str, Any] = cast(
        "dict[str, Any]", parsed) if isinstance(parsed, dict) else {}

    raw_invoice = data.get("invoice")
    invoice: dict[str, Any] = cast(
        "dict[str, Any]", raw_invoice) if isinstance(raw_invoice, dict) else {}

    number = invoice.get("invoiceNumber")
    stem = _safe_filename(number) if number else f"request-{index:04d}"

    written: list[Path] = [save_request_body(body, output_dir, stem)]

    # Decoded documents (only present on success; skip silently if absent or
    # undecodable -- the validator has already flagged those cases).
    for field_name, suffix in (("invoicePdf", "pdf"), ("invoiceXml", "xml")):
        encoded = data.get(field_name)
        if not encoded:
            continue
        try:
            raw = base64.b64decode(encoded)
        except Exception:
            continue
        doc_path = output_dir / f"{stem}.{suffix}"
        doc_path.write_bytes(raw)
        written.append(doc_path)

    return written


# ======================================================================
#  Failure capture
# ======================================================================

def save_failure(report: Report, body: dict[str, Any], resp: requests.Response) -> Path:
    FAILURES_DIR.mkdir(parents=True, exist_ok=True)
    try:
        response_body: Any = resp.json()
    except ValueError:
        response_body = resp.text[:2000]
    payload: dict[str, Any] = {
        "index": report.index,
        "seed_material": report.seed_material,
        "reproduce_with": f"--seed <base> --only {report.index}",
        "anomalies": report.anomalies,
        "status": report.status,
        "errors": report.errors,
        "warnings": report.warnings,
        "request": body,
        "response": response_body,
    }
    path = FAILURES_DIR / f"fail-{int(time.time())}-{report.index:04d}.json"
    path.write_text(json.dumps(payload, indent=2,
                    ensure_ascii=False), encoding="utf-8")
    return path


# ======================================================================
#  Init helper
# ======================================================================

ENV_TEMPLATE = (
    "USER=\n"
    "PASSWORD=\n"
    "\n"
    "# Optional: use a long-lived API key instead of USER/PASSWORD\n"
    "# API_KEY=\n"
    "# CLIENT_ID=invoice-fuzzer\n"
)


def cmd_init() -> None:
    if ENV_FILE.exists():
        print(f"skip   {ENV_FILE.name} (already exists)")
    else:
        ENV_FILE.write_text(ENV_TEMPLATE, encoding="utf-8")
        try:
            os.chmod(ENV_FILE, 0o600)  # contains a password
        except OSError:
            pass
        print(f"create {ENV_FILE.name}")

    print("\nFill in USER and PASSWORD in .env, then run the script to start fuzzing.")


# ======================================================================
#  Main
# ======================================================================

def run_fuzz(client: EventCentralClient, *, count: int, base_seed: int,
             edge_cases: bool, only: int | None, dry_run: bool,
             stop_on_fail: bool, save_outputs: bool) -> int:
    indices = [only] if only is not None else range(count)
    reports: list[Report] = []

    # Build the shared Faker instance and event pool once, both seeded from the
    # base seed so the whole run is reproducible.
    fake = Faker(FAKER_LOCALE)
    event_pool = build_event_pool(base_seed, EVENT_POOL_SIZE, fake)

    for i in indices:
        seed_material = f"{base_seed}:{i}"
        body, anomalies = generate_invoice(
            seed_material, edge_cases, event_pool, fake)

        if dry_run:
            print(f"\n--- invoice #{i}  anomalies={anomalies or ['none']} ---")
            print(json.dumps(body, indent=2, ensure_ascii=False))
            continue

        report = Report(index=i, seed_material=seed_material,
                        anomalies=anomalies, status=0)
        try:
            resp = client.post_invoice(body)
        except requests.RequestException as exc:
            report.status = -1
            report.errors.append(f"request raised: {exc}")
            reports.append(report)
            print(f"[#{i}] NETWORK ERROR: {exc}")
            # No response came back, but the request itself was generated and
            # sent -- persist it so the run still captures every request.
            if save_outputs:
                path = save_request_body(body, OUTPUT_DIR, f"request-{i:04d}")
                print(f"        saved  {OUTPUT_DIR.name}/{path.name}")
            if stop_on_fail:
                break
            continue

        report.status = resp.status_code
        validate(body, resp, report)
        reports.append(report)

        tag = "OK  " if report.ok else "FAIL"
        extra = f" anomalies={','.join(report.anomalies)}" if report.anomalies else ""
        print(f"[#{i}] {tag} status={resp.status_code} "
              f"errors={len(report.errors)} warnings={len(report.warnings)}{extra}")
        for e in report.errors:
            print(f"        ERROR  {e}")
        for w in report.warnings:
            print(f"        warn   {w}")

        # Persist the request for EVERY invoice (plus documents on success).
        if save_outputs:
            saved = save_invoice_files(body, resp, OUTPUT_DIR, i)
            if saved:
                suffixes = ",".join(sorted(p.suffix.lstrip(".")
                                    for p in saved))
                print(
                    f"        saved  {OUTPUT_DIR.name}/{saved[0].stem}.{{{suffixes}}}")

        if not report.ok and SAVE_FAILURES:
            path = save_failure(report, body, resp)
            print(f"        saved  {path}")
        if not report.ok and stop_on_fail:
            break

    if dry_run:
        return 0

    failed = [r for r in reports if not r.ok]
    warned = [r for r in reports if r.ok and r.warnings]
    print("\n" + "=" * 60)
    print(f"Ran {len(reports)} invoice(s) against {client.base_url}")
    print(
        f"  base seed : {base_seed}   (reproduce a case with --seed {base_seed} --only <index>)")
    print(f"  passed    : {len(reports) - len(failed)}")
    print(f"  failed    : {len(failed)}")
    print(
        f"  warnings  : {len(warned)} passing case(s) had non-fatal warnings")
    if not dry_run:
        print(
            f"  outputs   : every request saved under {OUTPUT_DIR.name}/")
    if failed:
        print("  failing indices: " + ", ".join(str(r.index) for r in failed))
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fuzz the Event Central invoice API.")
    parser.add_argument("--init", action="store_true",
                        help="write a .env template, then exit")
    parser.add_argument("--login", action="store_true",
                        help="force a fresh login and exit")
    parser.add_argument("--whoami", action="store_true",
                        help="print the authenticated user and exit")
    parser.add_argument("--count", type=int, default=RUN_COUNT,
                        help=f"invoices to generate (default {RUN_COUNT})")
    parser.add_argument("--seed", type=int, default=None,
                        help="base RNG seed (default: random, printed at start)")
    parser.add_argument("--only", type=int, default=None,
                        help="run only this invoice index (needs --seed to repro)")
    parser.add_argument("--no-edge", action="store_true",
                        help="disable edge-case injection")
    parser.add_argument("--dry-run", action="store_true",
                        help="print generated bodies, send nothing")
    parser.add_argument("--stop-on-fail", action="store_true",
                        help="halt at the first failing invoice")
    parser.add_argument("--no-save", action="store_true",
                        help="do not save request JSON (or PDF/XML) for any invoice")
    parser.add_argument("--base-url", default=API_BASE_URL,
                        help="override the API base URL")
    args = parser.parse_args()

    if args.init:
        cmd_init()
        return 0

    client = EventCentralClient(base_url=args.base_url)

    if args.login:
        client.login()
        return 0
    if args.whoami:
        print(json.dumps(client.whoami(), indent=2))
        return 0

    base_seed = args.seed if args.seed is not None else random.randrange(
        1, 2**31)
    print(f"Fuzzing {client.base_url}  seed={base_seed}  "
          f"edge_cases={'off' if args.no_edge else 'on'}  "
          f"events={EVENT_POOL_SIZE}  faker={FAKER_LOCALE}")

    return run_fuzz(
        client,
        count=args.count,
        base_seed=base_seed,
        edge_cases=not args.no_edge,
        only=args.only,
        dry_run=args.dry_run,
        stop_on_fail=args.stop_on_fail or STOP_ON_FIRST_FAILURE,
        save_outputs=SAVE_OUTPUTS and not args.no_save,
    )


if __name__ == "__main__":
    raise SystemExit(main())
