# syntax=docker/dockerfile:1

##############################################################################
# Single image, multiple start-up modes (web / queue / migrate / backup /
# restore). The mode is the container's command, e.g. `docker run image queue`.
##############################################################################
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System libraries:
#  * WeasyPrint needs pango/cairo/gdk-pixbuf/harfbuzz + fonts.
#  * postgresql-client provides pg_dump / pg_restore for backup & restore modes.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        libharfbuzz0b \
        libjpeg62-turbo \
        shared-mime-info \
        fontconfig \
        fonts-dejavu-core \
        postgresql-client \
        libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Application code.
COPY pyproject.toml alembic.ini ./
COPY migrations ./migrations
COPY src ./src

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

# Default to the web handler; override with `queue`, `migrate`, etc.
ENTRYPOINT ["python", "-m", "src"]
CMD ["web"]
