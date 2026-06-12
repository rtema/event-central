"""Import every ORM model so ``Base.metadata`` is complete.

Used by Alembic (autogenerate / migrations) and anywhere the full metadata is
required. Importing this module has the side effect of registering all tables.
"""

from src.auth.models import AuthChallenge, RefreshToken
from src.document_templates.models import DocumentTemplate, PublicDocumentTemplate
from src.events.models import Event
from src.invoices.models import Invoice, InvoiceLineItem, Tax
from src.jobs.models import Job
from src.orders.models import Order
from src.payments.models import Payment
from src.users.models import User, UserAuth, UserData, UserHistory, UserScope

__all__ = [
    "AuthChallenge",
    "RefreshToken",
    "User",
    "UserAuth",
    "UserScope",
    "UserHistory",
    "UserData",
    "Event",
    "Order",
    "Payment",
    "Invoice",
    "InvoiceLineItem",
    "Tax",
    "Job",
    "DocumentTemplate",
    "PublicDocumentTemplate",
]
