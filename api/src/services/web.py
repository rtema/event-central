"""FastAPI application factory — entry point for the *web* start-up mode.

A reverse proxy / TLS terminator will sit in front of the web replicas; that is
configured separately (not part of this repository yet).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import src.models  # type: ignore # noqa: F401 (import needs to be done here for sqlalchemy to build the full class registry)
from src.auth.router import router as auth_router
from src.config import settings
from src.core.errors import register_exception_handlers
from src.document_templates.router import router as document_templates_router
from src.emails.router import email_router, email_senders_router, email_templates_router
from src.events.router import router as events_router
from src.files.router import router as files_router
from src.invoices.router import router as invoicing_router
from src.logger import configure_logger
from src.misc.router import router as misc_router
from src.orders.router import router as orders_router
from src.payments.router import router as payments_router
from src.users.router import router as users_router

origins = [
    settings.app_base_url,
]


def create_app() -> FastAPI:
    configure_logger(settings.log_level)

    app = FastAPI(
        title="Event Central",
        description="Centralized API to generate e-invoices (E-Rechnungen) for events",
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(misc_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(invoicing_router)
    app.include_router(events_router)
    app.include_router(orders_router)
    app.include_router(payments_router)
    app.include_router(document_templates_router)
    app.include_router(files_router)
    app.include_router(email_router)
    app.include_router(email_senders_router)
    app.include_router(email_templates_router)

    return app


app = create_app()
