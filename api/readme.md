# Event Central

Centralized backend to generate e-invoices (E-Rechnungen / XRechnung) for
events, track payments, manage collections and produce reporting.

---

## Getting Started

**Setup development database**
Generate a secure password and save it as a file `../secrets/db_password`
```
cd ..

```

**Install python 3.12 using pyenv**

See: https://github.com/pyenv/pyenv#a-getting-pyenv

```
curl -fsSL https://pyenv.run | bash
pyenv init --install
...
pyenv install 3.12
pyenv global 3.12
```

**Setup virtual env and install dependencies**
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements.dev.txt
```

**Startup all development 

**Initialize the database**
```
alembic upgrade head  
```

**Seed the initial data**
```
python -m src seed --email test@example.com
```

**Startup the development server**
```
python -m src web
```

You can now access the api locally using  
http://localhost:7435/

Try the health endpoints




## Architecture at a glance

One Docker image, several **start-up modes** — exactly one process per
container, scaled horizontally by running more replicas:

| Mode      | Command                              | Purpose                                     |
| --------- | ------------------------------------ | ------------------------------------------- |
| `web`     | `python -m src web`                  | FastAPI HTTP handler                        |
| `queue`   | `python -m src queue`                | Durable job worker (Postgres-backed queue)  |
| `migrate` | `python -m src migrate`              | Apply DB migrations to head, then exit      |
| `backup`  | `python -m src backup`               | `pg_dump` → object storage, then exit       |
| `restore` | `python -m src restore --key <key>`  | Object storage → `pg_restore`               |

* **Proxy / TLS:** the `web` mode speaks plain HTTP and publishes its port
  directly for now. A reverse proxy / TLS terminator and load balancer will be
  added separately later.
* **Database:** PostgreSQL via SQLAlchemy 2.0 (synchronous — simple and robust;
  throughput comes from running more containers, not from async complexity).
  Refresh-token revocation and the job queue both live in Postgres.
* **Object storage:** S3-compatible. MinIO in development; in production a
  **dual-write** setup mirrors every object to a secondary store so a single
  store failure cannot lose data.
* **Auth:** OAuth-style JWTs (HS256, shared secret so every replica can verify)
  plus long-lived opaque API tokens. Argon2 for all secret hashing.
* **Logging:** structured JSON on stdout by default; optionally ships to
  OpenObserve via a non-blocking background handler when `OPENOBSERVE_URL` is
  set (otherwise a log collector ships the stdout JSON).
* **Secrets:** any setting can be supplied as a file under `/run/secrets`
  (Docker / Kubernetes secrets); the app reads them automatically.

### Layout

The tree mirrors the OpenAPI **tags** — each feature is a self-contained
package (`models` / `schemas` / `service` / `router`), with cross-cutting
infrastructure in `core/`.

```
src/
  main.py            # CLI dispatch across the start-up modes
  web.py             # FastAPI app factory (includes the feature routers)
  worker.py          # queue handler loop (FOR UPDATE SKIP LOCKED)
  config.py          # settings (pydantic-settings) + Docker-secrets support
  logging_config.py  # JSON logging + optional OpenObserve handler
  models.py          # aggregator importing every ORM model (for Alembic)
  core/              # cross-cutting infrastructure (not a tag)
    db.py            # engine, session, declarative base
    models.py        # shared column types + mixins (UUID, JSONB, timestamps)
    schemas.py       # CamelModel base + shared fragments (Pagination, supplier/recipient)
    security.py      # argon2 hashing, JWT encode/decode, signed links, OTP
    scopes.py        # scope catalogue (+labels) + matching (:all covers :own/{eventId})
    errors.py        # Error / AuthError payloads + exception handlers (+ 501 NotImplementedYet)
    deps.py          # get_db, page_params
  auth/              # tag: Auth
    models.py        # RefreshToken, AuthChallenge
    schemas.py service.py router.py
    deps.py          # AuthenticatedActor, require_all_scopes / require_any_scope /
                     #   require_event_path_scope
  users/             # tag: Users
    models.py        # User, UserAuth, UserScope, UserHistory, UserData
    schemas.py service.py router.py
  invoicing/         # tag: Invoicing (+ Files download routes)
    models.py        # Invoice, InvoiceLineItem, Tax
    schemas.py service.py router.py
    deps.py          # require_invoice_scope (all/own/{eventId})
  events/            # tag: Events (+ the /events/{id}/orders Orders route)
    models.py schemas.py service.py router.py
  orders/            # tag: Orders (+ order-scoped Payments/Invoicing routes)
    models.py schemas.py service.py router.py
    deps.py          # require_order_scope (resolves the order's event)
  payments/          # tag: Payments
    models.py schemas.py service.py router.py
  templates/         # tag: Document Templates
    models.py        # DocumentTemplate, PublicDocumentTemplate
    schemas.py service.py router.py
  files/router.py    # tag: Files — signed-link downloads (step 3)
  misc/              # tag: Misc — /health, /ready, /taxes, /scopes
    schemas.py router.py
  jobs/models.py     # Job (queue table; backs exports)
  storage/s3.py      # single/dual S3-compatible storage
  services/          # backup.py (pg_dump→storage), restore.py (storage→pg_restore)
migrations/          # Alembic environment + versioned migrations
scripts/             # smoke_auth.py, smoke_users.py — end-to-end smoke tests
secrets/             # dev-only secret placeholders (mounted at /run/secrets)
```

---

## Running locally

Everything is wired up in `docker-compose.yml` (Postgres, MinIO, migrations,
web, queue). Secrets are read from files in `./secrets` (dev placeholders are
included):

```bash
cp .env.example .env          # non-secret config; secrets live in ./secrets
docker compose up --build
# API:            http://localhost:7435/
# OpenAPI docs:   http://localhost:7435/docs
# MinIO console:  http://localhost:9001   (minioadmin / minioadmin)
```

Scale the web tier horizontally:

```bash
docker compose up --scale web=3
```

Ad-hoc backup / restore (the `tools` profile):

```bash
docker compose run --rm backup
docker compose run --rm cli restore --key backups/eventcentral-<timestamp>.dump
```

### Secrets

In development the files under `secrets/` are mounted into the containers at
`/run/secrets/<name>`; the app maps each file to the setting whose field name
matches (`jwt_secret` → `JWT_SECRET`, etc.), and Postgres reads `db_password`
via `POSTGRES_PASSWORD_FILE`. In production, supply real values through your
orchestrator's secret store — the mount path is the same, so no code changes
are needed. Don't set a value as both an env var and a secret (env wins).

### Without Docker (development)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/eventcentral
export JWT_SECRET=... SIGNED_URL_SECRET=...
python -m src migrate
python -m src web          # or: uvicorn src.web:app --port 7435
```

---

## Authentication

All auth lives under `/auth`. The token endpoint supports three OAuth grants.

| Endpoint                            | Notes                                                        |
| ----------------------------------- | ------------------------------------------------------------ |
| `POST /auth/token`                  | Grants: `password`, `refresh_token`, Auth0 passwordless OTP  |
| `POST /auth/revoke`                 | Revoke a refresh token (logout); always responds opaquely    |
| `GET  /auth/userinfo`               | Requires a bearer token (JWT **or** API token)               |
| `POST /auth/passwordless/start`     | Issues a one-time code; opaque response (no user enumeration)|
| `POST /auth/password-reset/start`   | Issues a reset code; opaque response                         |
| `POST /auth/password-reset/confirm` | Sets a new password, revokes all sessions                    |

Key behaviours:

* **Access tokens** are short-lived signed JWTs carrying the granted `scope`.
* **Refresh tokens** are JWTs *and* have a server-side row, so they can be
  revoked. Using a refresh token **rotates** it (the old one is invalidated).
* **API tokens** are long-lived opaque credentials accepted anywhere a bearer
  token is, resolved against hashed values in `user_auth`.
* **Scopes** follow `resource:action:qualifier`; a granted `:all` satisfies the
  matching `:own` or `:{eventId}` requirement. Requested scopes are always
  narrowed to what the authenticated_actor actually owns.
* Auth methods are **append-only**: changing a password soft-deletes the old
  method and creates a new one, preserving an audit trail.

---

## Users

All user management lives under `/api/v1/users` (tag: Users). Reads require
`users:read:all`; writes require `users:write:all`. Per the spec, updates use
**POST** (not PUT/PATCH).

| Endpoint                                  | Purpose                                           |
| ----------------------------------------- | ------------------------------------------------- |
| `GET/POST /api/v1/users`                  | List (newest first) / create                      |
| `GET/POST/DELETE /api/v1/users/{id}`      | Fetch / update / soft-delete                      |
| `GET  /api/v1/users/{id}/history`         | Change history of the basic fields                |
| `POST /api/v1/users/{id}/restore`         | Restore a soft-deleted user                       |
| `GET/POST /api/v1/users/{id}/auth`        | List / create an auth method                      |
| `GET/DELETE /api/v1/users/{id}/auth/{id}` | Fetch / disable (soft-delete) an auth method      |
| `GET/POST /api/v1/users/{id}/scopes`      | List / reconcile (replace) scope grants           |
| `GET/POST /api/v1/users/{id}/data`        | Current arbitrary data / set new data             |
| `GET  /api/v1/users/{id}/data/history`    | Full history of arbitrary-data changes            |

Notes:

* **Soft-delete + history.** Users, auth methods and scopes are never hard
  deleted; every change to the basic fields appends a `user_history` row.
* **Append-only data.** `user_data` is append-only — the latest row is the
  current value and the full set is its history, so `/data` and `/data/history`
  read from the same table.
* **Secret visibility.** On creating an auth method the generated secret is
  shown **once** (api-token / backup-code / otp); passwordless returns its bound
  identifier; passwords are never returned. Listings and reads never expose
  stored secrets.
* **Scope reconciliation.** `POST /scopes` diffs the requested set against the
  active grants — newly requested scopes are granted, dropped ones soft-deleted
  — and returns the full list including history.

---

## Invoicing, Events, Orders, Payments, Templates (step 2)

Step 2 wires up the rest of the API: every endpoint exists, validates its
request, enforces scopes and has a persisted schema. The behaviours that
produce or move bytes — generating the ZUGFeRD PDF / XRechnung XML, issuing
signed download links, building exports and the cancellation invoice — are
scaffolded and return **`501 not_implemented`**; they land in step 3.

| Endpoint                                         | Status  | Scopes                                   |
| ------------------------------------------------ | ------- | ---------------------------------------- |
| `GET  /api/v1/invoices`                          | done    | `invoices:read:all`                      |
| `POST /api/v1/invoices`                          | 501     | `invoices:write:all`/`:own`              |
| `GET  /api/v1/invoices/{id}`                     | done    | `invoices:read:all`/`:own`/`:{eventId}`  |
| `GET  /api/v1/invoices/{id}/line-items`          | done    | as above                                 |
| `GET  /api/v1/invoices/{id}/taxes`               | done    | as above                                 |
| `POST /api/v1/invoices/{id}/link`                | 501     | as above                                 |
| `POST /api/v1/invoices/export`                   | 501     | `invoices:read:all`                      |
| `GET  /api/v1/events` / `…/{id}`                 | done    | `events:read:all` / `:{eventId}`         |
| `GET  /api/v1/events/{id}/orders`                | done    | `orders:read:all` / `:{eventId}`         |
| `GET  /api/v1/orders` / `…/{id}`                 | done    | `orders:read:all` / `:{eventId}`         |
| `DELETE /api/v1/orders/{id}`                     | 501     | `orders:write:all` / `:{eventId}`        |
| `GET/POST /api/v1/orders/{id}/payments`          | done    | `payments:read|write:all`/`:{eventId}`   |
| `GET  /api/v1/orders/{id}/invoices`              | done    | `invoices:read:all` / `:{eventId}`       |
| `GET  /api/v1/payments`                          | done    | `payments:read:all`                      |
| `GET  /api/v1/files/invoices/{id}/{name}`        | 501     | signed token (no bearer)                 |
| `GET  /api/v1/files/exports/{jobId}/{name}`      | 501     | signed token (no bearer)                 |
| `GET  /api/v1/document-templates` / `…/{id}`     | done    | `backend:read`                           |
| `GET/POST /api/v1/document-templates/public`     | done    | `backend:read` / `backend:write`         |
| `GET/POST /api/v1/document-templates/public/{id}`| done    | `backend:read` / `backend:write`         |
| `GET  /api/v1/taxes`                             | done    | `backend:read`                           |
| `GET  /api/v1/scopes`                            | done    | `backend:read`                           |

Notes:

* **Scoping.** A granted `:all` covers `:own` and any `:{eventId}`. Routes that
  carry an `eventId` in the path check it directly; order/invoice routes resolve
  the resource's event (and `:own` against `createdBy`) via dedicated guards.
* **External ids.** Order and payment `externalId`s are unique on a per-event
  basis; public template ids are slugs (`[a-z0-9_-]+`).
* **Versioned templates.** Updating a public template provisions a *new*
  concrete `document_templates` row and repoints the slug, so issued invoices
  keep referencing the exact template they were rendered with.

---

## Quality

* **Lint/format:** `ruff` (config in `pyproject.toml`), wired into
  `.pre-commit-config.yaml`. `ruff check .` is clean.
* **Smoke tests** drive the real app against a real Postgres:
  ```bash
  PYTHONPATH=. python scripts/smoke_auth.py     # 23 checks: full auth lifecycle
  PYTHONPATH=. python scripts/smoke_users.py    # 26 checks: every Users endpoint
  PYTHONPATH=. python scripts/smoke_step2.py    # 34 checks: invoicing/events/orders/
                                                #   payments/templates/taxes/scopes
  ```

---

## Roadmap

1. **Scaffolding + auth endpoints** — *done.*
2. Endpoint scaffolding, request validation & database schemas for the full API
   — *done.* (Users, invoices, events, orders, payments, document templates,
   files, misc/taxes/scopes.) The generation/storage routes return `501` until
   step 3.
3. E-invoice generation (PDF via WeasyPrint + XRechnung XML).
4. Validation of the generated e-invoices.
