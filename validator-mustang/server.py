#!/usr/bin/env python3
"""Tiny stdlib HTTP wrapper around the Mustang-CLI e-invoice validator.

Mustang (https://www.mustangproject.org/) validates the *whole* ZUGFeRD /
Factur-X PDF -- PDF/A-3 conformance via an embedded veraPDF plus the embedded
XML against its XML-Schema and the EN16931 / profile Schematron -- as well as
stand-alone CII / XRechnung XML. This server exposes that as a small JSON API so
the (Python) fuzzer can call it over HTTP instead of shelling out to Java.

No third-party packages: only the Python standard library, so the container
stays small. Each request runs one `java -jar Mustang-CLI.jar --action validate`
subprocess; a semaphore caps how many JVMs run at once so a burst of invoices
can't OOM the container.

Endpoints
    GET  /health              -> 200 {"status":"UP", ...}
    POST /validate            -> 200 {"valid":bool, "returncode":int,
                                       "report_xml":str, "kind":str, ...}
        body : the raw invoice bytes (PDF or XML), application/octet-stream
        query: ?kind=pdf|xml    (optional; auto-sniffed from the bytes if absent)
               ?notices=1        (optional; include NOTICE-level findings)

Everything is configured via environment variables (see the constants below),
all of which have container-friendly defaults.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl

MUSTANG_JAR = os.environ.get("MUSTANG_JAR", "/opt/Mustang-CLI.jar")
MUSTANG_VERSION = os.environ.get("MUSTANG_VERSION", "unknown")
PORT = int(os.environ.get("PORT", "8080"))
JAVA_MEM = os.environ.get("JAVA_MEM", "1G")
# How many Mustang JVMs may run concurrently. Each one is memory-hungry
# (veraPDF holds the whole PDF model), so keep this small.
MAX_CONCURRENCY = int(os.environ.get("MAX_CONCURRENCY", "2"))
# Hard wall-clock limit for a single validation, in seconds.
VALIDATE_TIMEOUT = int(os.environ.get("VALIDATE_TIMEOUT", "120"))
# Cap the request body so a malformed client can't fill the disk.
MAX_BODY_BYTES = int(os.environ.get("MAX_BODY_BYTES", str(64 * 1024 * 1024)))

_slots = threading.Semaphore(MAX_CONCURRENCY)


def _sniff_kind(raw: bytes) -> str:
    """Guess whether the bytes are a PDF or an XML document."""
    head = raw[:1024].lstrip()
    if raw[:5] == b"%PDF-" or b"%PDF-" in raw[:1024]:
        return "pdf"
    if head[:1] == b"<" or b"<?xml" in head or b"CrossIndustryInvoice" in head or b"Invoice" in head:
        return "xml"
    # Default to XML: Mustang will reject it cleanly if it is neither.
    return "xml"


def _run_mustang(raw: bytes, kind: str, *, notices: bool) -> tuple[int, str, str]:
    """Write the bytes to a temp file and run one Mustang validation.

    Returns ``(returncode, stdout_report, stderr_log)``. Mustang prints its XML
    ``<validation>`` report on stdout and its own logging on stderr; the return
    code is 0 for a valid document and non-zero (usually 255) for an invalid one.
    """
    suffix = ".pdf" if kind == "pdf" else ".xml"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as fh:
        fh.write(raw)
        tmp_path = fh.name
    try:
        cmd = [
            "java",
            f"-Xmx{JAVA_MEM}",
            "-Djava.awt.headless=true",
            "-Dfile.encoding=UTF-8",
            "-jar", MUSTANG_JAR,
            "--action", "validate",
            "--source", tmp_path,
        ]
        if not notices:
            cmd.insert(-2, "--no-notices")  # place before --source
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=VALIDATE_TIMEOUT,
        )
        return proc.returncode, proc.stdout, proc.stderr
    finally:
        try:
            Path(tmp_path).unlink()
        except OSError:
            pass


def _run_extract(pdf: bytes) -> tuple[bool, bytes, str]:
    """Extract the embedded Factur-X / ZUGFeRD XML from a PDF.

    Runs ``Mustang --action extract --source <pdf> --out <xml>`` (non-interactive
    because both paths are supplied) and returns ``(found, xml_bytes, log)``.
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fin:
        fin.write(pdf)
        pdf_path = fin.name
    out_path = pdf_path + ".xml"
    try:
        proc = subprocess.run(
            [
                "java", f"-Xmx{JAVA_MEM}", "-Djava.awt.headless=true",
                "-Dfile.encoding=UTF-8", "-jar", MUSTANG_JAR,
                "--action", "extract", "--source", pdf_path, "--out", out_path,
            ],
            capture_output=True, text=True, timeout=VALIDATE_TIMEOUT,
        )
        if Path(out_path).exists():
            data = Path(out_path).read_bytes()
            if data.strip():
                return True, data, proc.stderr
        return False, b"", proc.stderr
    finally:
        for p in (pdf_path, out_path):
            try:
                Path(p).unlink()
            except OSError:
                pass


def _overall_valid(report_xml: str, returncode: int) -> bool:
    """Trust the report's top-level <summary status=.../> when present.

    The return code corroborates it (0 == valid), but parsing the status is more
    robust across Mustang versions and lets a caller that only has the report
    reach the same verdict.
    """
    # The last top-level "<summary status=..." wins; Mustang emits a per-section
    # summary and then the overall one. A simple rfind is enough and avoids a
    # full XML parse here (the client does the structured parse).
    marker = '<summary status="'
    idx = report_xml.rfind(marker)
    if idx != -1:
        start = idx + len(marker)
        end = report_xml.find('"', start)
        if end != -1:
            return report_xml[start:end].strip().lower() == "valid"
    return returncode == 0


class Handler(BaseHTTPRequestHandler):
    server_version = "MustangShim/1.0"

    # Silence the default noisy per-request logging; keep it terse.
    def log_message(self, format: str, *args: object) -> None:
        pass

    def _send_json(self, code: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] == "/health":
            self._send_json(200, {
                "status": "UP",
                "engine": "mustang",
                "version": MUSTANG_VERSION,
                "maxConcurrency": MAX_CONCURRENCY,
            })
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        path, _, query = self.path.partition("?")
        if path not in ("/validate", "/extract"):
            self._send_json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            self._send_json(400, {"error": "empty body"})
            return
        if length > MAX_BODY_BYTES:
            self._send_json(413, {"error": "body too large"})
            return

        raw = self.rfile.read(length)

        params: dict[str, str] = dict(parse_qsl(query, keep_blank_values=True))

        if path == "/extract":
            self._handle_extract(raw)
            return

        kind = (params.get("kind") or _sniff_kind(raw)).lower()
        if kind not in ("pdf", "xml"):
            kind = _sniff_kind(raw)
        notices = params.get("notices", "0") in ("1", "true", "yes")

        acquired = _slots.acquire(timeout=VALIDATE_TIMEOUT)
        if not acquired:
            self._send_json(503, {"error": "validator busy, try again"})
            return
        try:
            rc, report_xml, stderr = _run_mustang(raw, kind, notices=notices)
        except subprocess.TimeoutExpired:
            self._send_json(504, {"error": "validation timed out"})
            return
        except Exception as exc:  # pragma: no cover - defensive
            self._send_json(500, {"error": f"validator crashed: {exc}"})
            return
        finally:
            _slots.release()

        # No report at all means Mustang could not even start on the input; that
        # is an engine/transport problem, not an invoice verdict.
        if "<validation" not in report_xml:
            self._send_json(422, {
                "error": "no validation report produced",
                "returncode": rc,
                "kind": kind,
                "stderr": stderr[-2000:],
            })
            return

        self._send_json(200, {
            "valid": _overall_valid(report_xml, rc),
            "returncode": rc,
            "kind": kind,
            "engine": "mustang",
            "version": MUSTANG_VERSION,
            "report_xml": report_xml,
        })

    def _handle_extract(self, pdf: bytes) -> None:
        """Extract the embedded Factur-X/ZUGFeRD XML from a posted PDF."""
        if pdf[:5] != b"%PDF-" and b"%PDF-" not in pdf[:1024]:
            self._send_json(400, {"error": "body is not a PDF"})
            return
        acquired = _slots.acquire(timeout=VALIDATE_TIMEOUT)
        if not acquired:
            self._send_json(503, {"error": "validator busy, try again"})
            return
        try:
            found, xml, _stderr = _run_extract(pdf)
        except subprocess.TimeoutExpired:
            self._send_json(504, {"error": "extraction timed out"})
            return
        except Exception as exc:  # pragma: no cover - defensive
            self._send_json(500, {"error": f"extractor crashed: {exc}"})
            return
        finally:
            _slots.release()

        if not found:
            # Not an error: some PDFs simply carry no embedded invoice XML.
            self._send_json(200, {"found": False, "engine": "mustang"})
            return
        self._send_json(200, {
            "found": True,
            "engine": "mustang",
            "xml_b64": base64.b64encode(xml).decode("ascii"),
        })


def main() -> None:
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"mustang-validator listening on :{PORT} "
          f"(jar={MUSTANG_JAR}, version={MUSTANG_VERSION}, "
          f"concurrency={MAX_CONCURRENCY})", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
