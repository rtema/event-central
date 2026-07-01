"""Factory for building randomized ``InvoiceTemplate`` payloads.

# cspell:ignore PICSUM KHTML wght Rechnung Rechnungsnr Beschreibung Menge Einzelpreis Betrag Zwischensumme Gesamtbetrag

The returned dict is the ``html`` + ``css`` variant of the model (never the
``templateName`` variant, since they are mutually exclusive), with random
Google Fonts and random images attached.

Verified remote sources (all reachable without an API key):
  * Font catalogue : https://fonts.google.com/metadata/fonts
  * Font binaries  : https://fonts.googleapis.com/css   -> static .ttf (via legacy UA)
  * Images         : https://picsum.photos/seed/<seed>/<w>/<h>.jpg (seeded -> deterministic)

Field names follow the *pydantic* models (the actual validators), which differ
from the OpenAPI YAML in two places: the image field is ``key`` (YAML says
``name``) and fonts carry a required ``weight`` (absent from the YAML). The
'link' image option is intentionally unused for now.
"""

from __future__ import annotations

import base64
import json
import re
import string
import threading
import urllib.parse
import urllib.request
from typing import Any
import random

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

_FONTS_METADATA_URL = "https://fonts.google.com/metadata/fonts"
_FONTS_CSS_URL = "https://fonts.googleapis.com/css"  # v1 API
_PICSUM_URL = "https://picsum.photos"

# The v1 CSS API serves a different font format per User-Agent. A legacy Android
# UA yields a static .ttf (format('truetype')); a modern UA would yield woff2 and
# an ancient IE UA would yield EOT. We want TTF, so use the Android UA for the
# font lookup. A normal UA is used for the catalogue and images.
_TTF_UA = (
    "Mozilla/5.0 (Linux; U; Android 4.0.3; en-us) AppleWebKit/534.30 "
    "(KHTML, like Gecko) Version/4.0 Mobile Safari/534.30"
)
_MODERN_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_HTTP_TIMEOUT = 20

# Locale -> Google Fonts subset. 'latin' (U+0000-00FF) already covers Western
# European accents including German ä/ö/ü/ß, so it is a safe default.
_LOCALE_SUBSET = {
    "de": "latin", "en": "latin", "fr": "latin",
    "es": "latin", "it": "latin", "nl": "latin", "pt": "latin",
}
_DEFAULT_SUBSET = "latin"

# Static, localized labels baked into the template. Dynamic invoice values stay
# as jinja ``{{ }}`` expressions and are filled in by the renderer.
_LABELS = {
    "en": {
        "invoice": "Invoice", "invoice_no": "Invoice No.", "date": "Date",
        "bill_to": "Bill To", "description": "Description", "qty": "Qty",
        "unit_price": "Unit price", "amount": "Amount",
        "subtotal": "Subtotal", "tax": "Tax", "total": "Total",
    },
    "de": {
        "invoice": "Rechnung", "invoice_no": "Rechnungsnr.", "date": "Datum",
        "bill_to": "Rechnung an", "description": "Beschreibung", "qty": "Menge",
        "unit_price": "Einzelpreis", "amount": "Betrag",
        "subtotal": "Zwischensumme", "tax": "MwSt.", "total": "Gesamtbetrag",
    },
}

# --------------------------------------------------------------------------- #
# Templates ($-placeholders are localized labels / font names; jinja {{ }} is
# left untouched because string.Template only touches $tokens.)
# --------------------------------------------------------------------------- #

_HTML = string.Template(
    """<!doctype html>
<html lang="">
<head><meta charset="utf-8"></head>
<body>
  <header class="head">
    {# 'logo' is resolved by the backend from the images[] array by its key. #}
    <img class="logo" src="{{ images.logo }}" alt="logo">
    <div class="seller">
      <div class="seller-name">{{ seller.name }}</div>
      <div>{{ seller.address }}</div>
    </div>
  </header>

  <h1>$invoice</h1>

  <table class="meta">
    <tr><td class="k">$invoice_no</td><td>{{ invoice.number }}</td></tr>
    <tr><td class="k">$date</td><td>{{ invoice.date }}</td></tr>
  </table>

  <div class="bill-to">
    <div class="k">$bill_to</div>
    <div>{{ buyer.name }}</div>
    <div>{{ buyer.address }}</div>
  </div>

  <table class="items">
    <thead>
      <tr>
        <th>$description</th>
        <th class="num">$qty</th>
        <th class="num">$unit_price</th>
        <th class="num">$amount</th>
      </tr>
    </thead>
    <tbody>
      {% for item in items %}
      <tr>
        <td>{{ item.description }}</td>
        <td class="num">{{ item.quantity }}</td>
        <td class="num">{{ "%.2f"|format(item.unit_price) }} {{ currency }}</td>
        <td class="num">{{ "%.2f"|format(item.quantity * item.unit_price) }} {{ currency }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <table class="totals">
    <tr><td class="k">$subtotal</td><td class="num">{{ "%.2f"|format(subtotal) }} {{ currency }}</td></tr>
    <tr><td class="k">$tax ({{ tax_rate }}%)</td><td class="num">{{ "%.2f"|format(tax_amount) }} {{ currency }}</td></tr>
    <tr class="grand"><td class="k">$total</td><td class="num">{{ "%.2f"|format(total) }} {{ currency }}</td></tr>
  </table>
</body>
</html>"""
)

# NOTE: no @font-face here. Uploaded font bytes have no URL the template can
# reference, so the renderer is expected to register each fonts[] entry with
# WeasyPrint under its `name`; the CSS just uses the family by name. If your
# backend instead expects @font-face in the CSS, add it in _render_css.
_CSS = string.Template(
    """@page { size: A4; margin: 2cm; }
* { box-sizing: border-box; }
body { font-family: '$body_family', sans-serif; font-size: 11pt; color: #222; line-height: 1.4; }
.head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.logo { height: 60px; width: auto; }
.seller { text-align: right; }
.seller-name { font-family: '$heading_family', serif; font-weight: 700; font-size: 13pt; }
h1 { font-family: '$heading_family', serif; font-size: 26pt; margin: 8px 0 16px; }
table { width: 100%; border-collapse: collapse; }
.meta td { padding: 2px 0; }
.meta .k, .bill-to .k, .totals .k { color: #666; }
.bill-to { margin: 18px 0; }
.items { margin: 24px 0; }
.items th { text-align: left; border-bottom: 2px solid #222; padding: 6px 8px; font-size: 9pt; text-transform: uppercase; letter-spacing: .04em; }
.items td { padding: 6px 8px; border-bottom: 1px solid #ddd; }
.num { text-align: right; }
.totals { width: 45%; margin-left: auto; margin-top: 12px; }
.totals td { padding: 4px 8px; }
.totals .grand td { font-family: '$heading_family', serif; font-weight: 700; font-size: 13pt; border-top: 2px solid #222; }
"""
)

# --------------------------------------------------------------------------- #
# HTTP + Google Fonts catalogue (cached)
# --------------------------------------------------------------------------- #

# One entry of the Google Fonts catalogue. The JSON is loosely structured, so
# values stay ``Any``; the alias just gives the keys a concrete container type.
_FamilyMeta = dict[str, Any]

_meta_lock = threading.Lock()
_meta_cache: list[_FamilyMeta] | None = None


def _http_get(url: str, ua: str = _MODERN_UA) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:  # follows redirects
        return resp.read()


def _load_font_families() -> list[_FamilyMeta]:
    """Fetch (once) and cache the full Google Fonts family catalogue."""
    global _meta_cache
    with _meta_lock:
        cached = _meta_cache
        if cached is None:
            text = _http_get(_FONTS_METADATA_URL).decode("utf-8")
            text = text[text.index("{"):]  # strip any anti-hijack prefix if present
            parsed: list[_FamilyMeta] = json.loads(text)["familyMetadataList"]
            _meta_cache = parsed
            cached = parsed
        return cached


def _families_for_subset(subset: str) -> list[_FamilyMeta]:
    return [f for f in _load_font_families() if subset in f.get("subsets", [])]


def _numeric_weights(family: _FamilyMeta) -> list[int]:
    """Upright (non-italic) numeric weights a family provides, e.g. [400, 700]."""
    fonts: dict[str, Any] = family.get("fonts", {})
    weights = {int(k) for k in fonts if k.isdigit()}
    return sorted(weights)


def _extract_ttf_url(css: str, subset: str) -> str | None:
    """Pull a .ttf URL out of a v1 CSS response, preferring the given subset."""
    marker = f"/* {subset} */"
    if marker in css:
        m = re.search(r"url\((https://[^)]+\.ttf)\)", css[css.index(marker):])
        if m:
            return m.group(1)
    m = re.search(r"url\((https://[^)]+\.ttf)\)", css)  # any block
    return m.group(1) if m else None


def _fetch_font_file(family: str, weight: int, subset: str) -> str | None:
    """Return base64 of a static .ttf for one family/weight/subset, or None."""
    url = (
        f"{_FONTS_CSS_URL}?family={urllib.parse.quote(family)}:{weight}"
        f"&subset={subset}"
    )
    try:
        css = _http_get(url, _TTF_UA).decode("utf-8")  # legacy UA -> truetype
        ttf_url = _extract_ttf_url(css, subset)
        if not ttf_url:
            return None
        return base64.b64encode(_http_get(ttf_url)).decode("ascii")
    except Exception:
        return None


def _fetch_image_file(seed: str, width: int, height: int) -> str | None:
    """Return base64 of a seeded (deterministic) random JPEG, or None on failure."""
    seed_q = urllib.parse.quote(seed, safe="")
    url = f"{_PICSUM_URL}/seed/{seed_q}/{width}/{height}.jpg"
    try:
        return base64.b64encode(_http_get(url)).decode("ascii")
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Public factory
# --------------------------------------------------------------------------- #


def make_invoice_template(rng: random.Random, locale: str) -> dict[str, Any]:
    lang = (locale or "en").replace("_", "-").split("-")[0].lower()
    subset = _LOCALE_SUBSET.get(lang, _DEFAULT_SUBSET)
    labels = _LABELS.get(lang, _LABELS["en"])

    # --- fonts: pick two distinct families (heading + body); each gets a
    #     regular weight and, usually, a bold weight. -------------------------
    candidates = _families_for_subset(subset)
    rng.shuffle(candidates)

    fonts: list[dict[str, Any]] = []
    family_names: list[str] = []
    for fam in candidates:
        if len(family_names) >= 2:
            break
        name: str = fam["family"]
        weights = _numeric_weights(fam) or [400]
        wanted = {min(weights, key=lambda w: abs(w - 400))}  # a regular-ish weight
        bold = [w for w in weights if w >= 600]
        if bold and rng.random() < 0.8:
            wanted.add(rng.choice(bold))

        entries: list[dict[str, Any]] = []
        for w in sorted(wanted):
            b64 = _fetch_font_file(name, w, subset)
            if b64:
                entries.append({"name": name, "weight": w, "file": b64})
        if entries:  # only keep the family if at least one weight downloaded
            fonts.extend(entries)
            family_names.append(name)

    heading_family = family_names[0] if family_names else "serif"
    body_family = family_names[-1] if family_names else "sans-serif"

    # --- images: a logo, plus (sometimes) a second decorative image. Content
    #     is random but the seed is rng-derived, so runs are reproducible. ----
    images: list[dict[str, Any]] = []
    logo = _fetch_image_file(f"logo-{rng.randrange(1_000_000)}", 240, 120)
    if logo:
        images.append({"key": "logo", "file": logo})  # 'link' left unset on purpose

    # --- assemble --------------------------------------------------------------
    html = _HTML.safe_substitute(labels)
    html = html.replace('<html lang="">', f'<html lang="{lang}">')
    css = _CSS.safe_substitute(heading_family=heading_family, body_family=body_family)

    template: dict[str, Any] = {"html": html, "css": css}
    if fonts:
        template["fonts"] = fonts
    if images:
        template["images"] = images
    return template


if __name__ == "__main__":
    import sys

    rng = random.Random(42)
    out = make_invoice_template(rng, "de")
    fonts_out: list[dict[str, Any]] = out.get("fonts", [])
    images_out: list[dict[str, Any]] = out.get("images", [])
    summary: dict[str, Any] = {
        "keys": sorted(out),
        "fonts": [(f["name"], f["weight"], f"{len(f['file'])}b64chars") for f in fonts_out],
        "images": [(i["key"], f"{len(i['file'])}b64chars") for i in images_out],
        "html_chars": len(out["html"]),
        "css_chars": len(out["css"]),
    }
    json.dump(summary, sys.stdout, indent=2, ensure_ascii=False)
    print()