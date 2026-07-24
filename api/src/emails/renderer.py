"""Business logic for Emails and Email templates (tag: Emails & Email Templates Document Templates).

TODO: Add a good summary
"""

from __future__ import annotations

import uuid

from babel.dates import format_date
from jinja2 import exceptions
from sqlalchemy.orm import Session
from src.config import settings
from src.emails.models import EmailTemplate
from src.events.models import Event
from src.invoices.models import Invoice
from src.orders.models import Order
from src.template_placeholders.__main__ import (
    generate_event_placeholders,
    generate_invoice_placeholders,
    generate_order_placeholders,
    generate_user_placeholders,
    now_utc,
    template_renderer_sandbox,
)
from src.users.models import User


def generate_email_template_placeholders(
        email_template: EmailTemplate,
        locale: str
) -> dict[str, str]:
    placeholders = {
        'timeOfGeneration': format_date(now_utc(), 'medium', locale=locale),
    }

    return placeholders


def generate_image_placeholders(
        email_template: EmailTemplate,
        locale: str
) -> dict[str, str]:
    placeholders: dict[str, str] = {}
    # add placeholders for every image

    for email_template_file in email_template.email_template_files:
        if (email_template_file.type == "image"):

            file = email_template_file.file

            # build url
            url = (
                f"{settings.api_base_url}/api/v1/files/public/email-templates/"
                f"{email_template.id}/{email_template_file.id}.{file.extension}"
            )

            placeholders[email_template_file.key] = url
            placeholders[f'{email_template_file.key}Width'] = f'image://{file.width}'
            placeholders[f'{email_template_file.key}Height'] = f'image://{file.height}'

    return placeholders


def render_email(
        db: Session,
        email_template: EmailTemplate,
        *,
        user: User | None = None,
        event: Event | None = None,
        order: Order | None = None,
        invoice: Invoice | None = None,
        extra: dict[str, str] | None = None
) -> tuple[str, str, uuid.UUID]:

    # get locale
    locale = email_template.locale

    # get the current version id
    email_template_version: uuid.UUID = (email_template.email_template_versions[0].id
                                         if len(email_template.email_template_versions) > 0
                                         else None)  # type: ignore

    # generate placeholder data
    placeholders: dict[str, str | dict[str, str]] = {
        'locale': locale,
        'user': generate_user_placeholders(user, locale),
        'event': generate_event_placeholders(event, locale),
        'order': generate_order_placeholders(order, locale),
        'invoice': generate_invoice_placeholders(invoice, locale),
        'template': generate_email_template_placeholders(email_template, locale),
        'images': generate_image_placeholders(email_template, locale),
        'extra': {} if extra is None else extra,
        'previewText': email_template.preview_text
    }

    # personalize subject
    subject = email_template.subject
    try:
        subject_template = template_renderer_sandbox.from_string(
            email_template.subject)
        subject = subject_template.render(**placeholders)
    except exceptions.SecurityError as e:
        print(f'Security error: {e}')

    # personalize previewText
    try:
        preview_text_template = template_renderer_sandbox.from_string(
            email_template.preview_text)
        placeholders['previewText'] = preview_text_template.render(
            **placeholders)
    except exceptions.SecurityError as e:
        print(f'Security error: {e}')

    # personalize body
    body = email_template.html
    try:
        html_template = template_renderer_sandbox.from_string(
            email_template.html)
        body = html_template.render(**placeholders)
    except exceptions.SecurityError as e:
        print(f'Security error: {e}')

    return body, subject, email_template_version
