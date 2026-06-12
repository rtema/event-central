# Pull a pinned mc (MinIO client) binary from the official client image so the
# build needs no network download and the version is reproducible.
FROM minio/mc:RELEASE.2025-08-13T08-35-41Z AS mc

FROM python:3.12-slim

# mc lives at /usr/bin/mc inside the minio/mc image.
COPY --from=mc /usr/bin/mc /usr/local/bin/mc

WORKDIR /app
COPY init.py .

# The script only uses the standard library plus the mc binary, so there are
# no pip dependencies to install.
ENTRYPOINT ["python", "-u", "init.py"]