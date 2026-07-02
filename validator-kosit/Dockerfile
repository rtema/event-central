# Strict German B2G validator: the OFFICIAL KoSIT validator + the OFFICIAL
# XRechnung rule configuration, in HTTP daemon mode.
#
# Why build our own instead of pulling a community image: KoSIT does not publish
# a Docker image -- only the validator JAR (github.com/itplr-kosit/validator) and
# the rule configuration (github.com/itplr-kosit/validator-configuration-xrechnung),
# both as GitHub releases. Every image on Docker Hub is therefore a third-party
# wrapper of varying provenance. Building from the two official release assets --
# pinned by version and SHA-256 -- means the only thing we trust is KoSIT itself,
# and upgrades are a one-line, reproducible change.
FROM eclipse-temurin:21-jre-noble

# --- pin both official artifacts ---------------------------------------------
# Validator JAR: https://github.com/itplr-kosit/validator/releases
ARG KOSIT_VALIDATOR_VERSION=1.6.2
ARG KOSIT_VALIDATOR_SHA256=244978514ad48f67c7573acfffc8f4fd73d81feda6f276710033f9913579857e
ARG KOSIT_VALIDATOR_URL=https://github.com/itplr-kosit/validator/releases/download/v${KOSIT_VALIDATOR_VERSION}/validator-${KOSIT_VALIDATOR_VERSION}-standalone.jar
# XRechnung config: https://github.com/itplr-kosit/validator-configuration-xrechnung/releases
ARG XR_CONFIG_DATE=2026-01-31
ARG XR_CONFIG_XR_VERSION=3.0.2
ARG XR_CONFIG_SHA256=6a5a5911a421b25fbc423f62f93f894df7b236f5d73ca4f84bb222a945082704
ARG XR_CONFIG_URL=https://github.com/itplr-kosit/validator-configuration-xrechnung/releases/download/v${XR_CONFIG_DATE}/xrechnung-${XR_CONFIG_XR_VERSION}-validator-configuration-${XR_CONFIG_DATE}.zip

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl unzip ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/kosit
RUN curl -fSL "${KOSIT_VALIDATOR_URL}" -o validator.jar \
 && echo "${KOSIT_VALIDATOR_SHA256}  validator.jar" | sha256sum -c - \
 && curl -fSL "${XR_CONFIG_URL}" -o config.zip \
 && echo "${XR_CONFIG_SHA256}  config.zip" | sha256sum -c - \
 && mkdir -p cfg && unzip -q config.zip -d cfg && rm config.zip \
 && test -f cfg/scenarios.xml

ENV PORT=8081 \
    JAVA_OPTS=-Xmx1g \
    KOSIT_VALIDATOR_VERSION=${KOSIT_VALIDATOR_VERSION} \
    XR_CONFIG_DATE=${XR_CONFIG_DATE}

RUN useradd --system --no-create-home --uid 10002 kosit
USER kosit

EXPOSE 8081

# The daemon exposes POST / (XML body -> VARL <rep:report>) and GET /server/health.
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=5 \
    CMD curl -fsS "http://localhost:${PORT}/server/health" || exit 1

CMD ["sh", "-c", "exec java $JAVA_OPTS -jar /opt/kosit/validator.jar -s /opt/kosit/cfg/scenarios.xml -r /opt/kosit/cfg -D -H 0.0.0.0 -P ${PORT}"]