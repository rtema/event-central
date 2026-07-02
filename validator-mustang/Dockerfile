# Full ZUGFeRD / Factur-X + XRechnung validator.
#
# Engine: Mustangproject (https://www.mustangproject.org/) -- validates the
# WHOLE hybrid PDF: PDF/A-3 conformance (embedded veraPDF) + the embedded XML
# (XML-Schema + EN16931 / profile Schematron). Also validates stand-alone
# CII / XRechnung XML.
#
# Why this base + source:
#   * eclipse-temurin is an official, security-maintained JRE image on a fast
#     update cadence (Adoptium ships monthly + CVE releases).
#   * The Mustang CLI is pulled from Maven Central by exact version and pinned
#     by SHA-256, so the build is reproducible and the engine is trivial to bump
#     (Mustang itself releases roughly monthly -- 2.24.0 shipped 2026-06-12).
FROM eclipse-temurin:21-jre-noble

# --- pin the validator engine -------------------------------------------------
ARG MUSTANG_VERSION=2.24.0
ARG MUSTANG_SHA256=e4904ffa0afdce3f5836dceb927c440a05ed5d60386fdd37e17a4b2f7652edbf
ARG MUSTANG_URL=https://repo1.maven.org/maven2/org/mustangproject/Mustang-CLI/${MUSTANG_VERSION}/Mustang-CLI-${MUSTANG_VERSION}.jar

# python3 runs the tiny HTTP shim; curl is only for the healthcheck.
RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

RUN curl -fSL "${MUSTANG_URL}" -o /opt/Mustang-CLI.jar \
  && echo "${MUSTANG_SHA256}  /opt/Mustang-CLI.jar" | sha256sum -c - \
  && chmod 0644 /opt/Mustang-CLI.jar

COPY server.py /opt/server.py

ENV MUSTANG_JAR=/opt/Mustang-CLI.jar \
  MUSTANG_VERSION=${MUSTANG_VERSION} \
  PORT=8080 \
  JAVA_MEM=1G \
  MAX_CONCURRENCY=2 \
  VALIDATE_TIMEOUT=120

# Run as an unprivileged user.
RUN useradd --system --no-create-home --uid 10001 appuser
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://localhost:${PORT}/health" || exit 1

CMD ["python3", "/opt/server.py"]