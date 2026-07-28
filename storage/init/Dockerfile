# Pull a pinned mc (MinIO client) binary from the official client image so the
# build needs no network download and the version is reproducible.
FROM minio/mc:RELEASE.2025-08-13T08-35-41Z AS mc

FROM python:3.12-slim

# --- non-root user + shared secrets group --------------------------------
# GID 5000 must match the group owner of the mounted secret on the host:
#   chown root:5000 ./secrets/db_password && chmod 640 ./secrets/db_password
RUN groupadd -g 5000 secrets \
    && useradd -m -u 1000 -s /usr/sbin/nologin app \
    && usermod -aG secrets app
# -------------------------------------------------------------------------

# mc lives at /usr/bin/mc inside the minio/mc image.
COPY --from=mc /usr/bin/mc /usr/local/bin/mc

WORKDIR /app
COPY init.py .
RUN chown -R app:app /app

# mc writes its config under $HOME; give it a writable dir the app user owns.
ENV HOME=/home/app

# The script only uses the standard library plus the mc binary, so there are
# no pip dependencies to install.
USER app
ENTRYPOINT ["python", "-u", "init.py"]