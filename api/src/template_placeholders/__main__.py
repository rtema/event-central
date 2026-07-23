from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Any, TypeVar

import pytz
from babel import Locale
from babel.dates import format_date
from babel.numbers import format_currency
from jinja2 import Undefined
from jinja2.sandbox import SandboxedEnvironment
from markupsafe import escape
from src.events.models import Event
from src.invoices.models import INVOICE_TYPE_CANCELLATION, INVOICE_TYPE_INVOICE, Invoice
from src.orders.models import Order
from src.users.models import User


def now_utc(exact: bool = True):
    """Get the current date/time in UTC.

    :param exact: Set to ``False`` to set seconds/microseconds to 0.
    :return: A timezone-aware `datetime` object
    """
    now = datetime.now(pytz.UTC)
    if not exact:
        now = now.replace(second=0, microsecond=0)
    return now


class PreserveUndefined(Undefined):
    def __str__(self):
        return f'{{{{ {self._undefined_name} }}}}'

    def _child(self, suffix: str):
        return PreserveUndefined(name=f'{self._undefined_name}{suffix}')

    def __getattr__(self, name: str):
        if name.startswith('_'):
            raise AttributeError(name)
        return self._child(f'.{name}')

    def __getitem__(self, key: Any):
        return self._child(f'.{key}' if isinstance(key, str) else f'[{key}]')


T = TypeVar("T")
Filter = Callable[..., Any]


def _noop[T](value: T, *args: Any, **kwargs: Any) -> T:
    return value


class PermissiveFilters(dict[str, Filter]):
    def __missing__(self, key: str) -> Filter:
        return _noop

    def get(self, key: str, default: Any = None) -> Filter:
        return self[key]

    def __contains__(self, key: object) -> bool:
        return True


class StrictSandbox(SandboxedEnvironment):
    def is_safe_attribute(self, obj: Any, attr: Any, value: Any):
        # Disallow all attribute access
        return False

    def is_safe_callable(self, obj: Any):
        # Disallow calling any functions or objects
        return False


# Create a strict environment
template_renderer_sandbox = StrictSandbox(undefined=PreserveUndefined)

# Remove all filters to prevent even basic formatting
template_renderer_sandbox.filters.clear()  # type: ignore

# Use filter that does nothing to prevent errors when users specify filters
template_renderer_sandbox.filters = PermissiveFilters()


def generate_title(data: dict[str, str], locale: str) -> str:
    title = ''
    if 'title' in data:
        if data['title'] == 'dr':
            title = 'Dr.'
        elif data['title'] == 'dr-ing':
            title = 'Dr.-Ing.'
        elif data['title'] == 'prof':
            title = 'Prof.'
        elif data['title'] == 'prof-dr':
            title = 'Prof. Dr.'
        elif data['title'] == 'prof-dr-ing':
            title = 'Prof. Dr.-Ing.'
        elif data['title'] == 'phd':
            title = 'Ph.D.'

    return title


def generate_salutation(data: dict[str, str], locale: str) -> str:
    salutation = ''
    append_first_name = False
    if locale == 'de':
        if 'salutation' in data:
            if data['salutation'] == 'mr':
                salutation += 'Sehr geehrter Herr '
            elif data['salutation'] == 'ms':
                salutation += 'Sehr geehrte Frau '
            else:
                salutation += 'Hallo '
                append_first_name = True

        if 'title' in data and data['title'] != '':  # noqa: PLC1901
            salutation += generate_title(data, locale)
            salutation += ' '

    else:  # noqa: PLR5501
        if 'title' in data and data['title'] != '':  # noqa: PLC1901
            title = generate_title(data, locale)
            salutation += ' '

            if title:
                salutation += title
                salutation += ' '
            else:
                salutation += 'Dear '
                append_first_name = True
        elif 'salutation' in data:
            if data['salutation'] == 'mr':
                salutation += 'Dear Mr. '
            elif data['salutation'] == 'ms':
                salutation += 'Dear Ms. '
            else:
                salutation += 'Dear '
                append_first_name = True
        else:
            salutation += 'Dear '
            append_first_name = True

    if append_first_name and 'firstName' in data:
        salutation += f'{escape(data["firstName"])} '

    # add last name
    salutation += escape(data.get('lastName', ''))

    return salutation


def generate_user_placeholders(user: User | None, locale: str) -> dict[str, str]:
    placeholders = {
        'email': "",
        'firstName': "",
        'lastName': "",
        'salutation': "",
    }
    if user:
        placeholders['salutation'] = escape(user.email)
        placeholders['firstName'] = escape(user.first_name)
        placeholders['lastName'] = escape(user.first_name)
        placeholders['salutation'] = escape("") # TODO: use generate_salutation

    return placeholders

def generate_event_placeholders(event: Event | None, locale: str) -> dict[str, str]:
    placeholders = {
        'label': "",
    }
    if event:
        placeholders['label'] = escape(event.label.get(locale, ''))

    return placeholders


def generate_order_placeholders(order: Order | None, locale: str) -> dict[str, str]:
    placeholders = {
        'externalShortId': '',
        'link': '',
        'invoiceNumbers': '',
        'payments': '',
        'paymentText': '',
    }
    if order:
        if order.external_short_id:
            placeholders['externalShortId'] = escape(order.external_short_id)

        if order.link:
            placeholders['link'] = escape(order.link)

        # if order.recipient:
        #   placeholders['salutation'] = generate_salutation(order.recipient, locale)
        # placeholders['name'] += f'{order.billing.get('firstName', '')} {
        #     order.billing.get('lastName', '')}'

        # # invoice numbers
        # invoice_numbers = [
        #     invoice.invoice_number for invoice in order.invoices]
        # placeholders['invoiceNumbers'] = ', '.join(invoice_numbers)

        # # build address
        # placeholders['address'] += f'{order.billing.get('company', '')}<br>'
        # placeholders['address'] += f'{placeholders['name']}<br>'
        # if 'addressAddition' in order.billing and order.billing['addressAddition'] is not None:
        #     placeholders['address'] += f'{order.billing.get('addressAddition', '')}<br>'
        # placeholders['address'] += f'{order.billing.get('street', '')}<br>'
        # placeholders['address'] += f'{order.billing.get('zip', '')} {order.billing.get('city', '')} <br>'  # noqa: E501
        # resolved_locale = Locale(locale)
        # placeholders[
        #     'address'] += f'{resolved_locale.territories[order.billing.get('country', '')]}<br>'

        # # build payments table
        # for payment in order.payments:
        #     if payment.status == PAYMENT_STATUS_SUCCESS and payment.type == PAYMENT_TYPE_PAYMENT:
        #         method_name = ''
        #         if payment.method == 'bank-transfer':
        #             method_name = 'Überweisung' if locale == 'de' else 'Bank Transfer'
        #         elif payment.method == 'card':
        #             method_name = 'Kreditkarte' if locale == 'de' else 'Credit Card'
        #         elif payment.method == 'paypal':
        #             method_name = 'PayPal'
        #         else:
        #             method_name = 'Zahlung' if locale == 'de' else 'Payment'

        #         placeholders['payments'] += f'<tr>\
        #             <td>{format_date(payment.completed, 'medium', locale=locale)}</td>\
        #             <td>{method_name}</td>\
        #             <td>{format_currency(payment.amount,
        #                                  currency=payment.currency,
        #                                  locale='de_DE' if locale == 'de' else 'en_GB')}</td>\
        #             </tr>'

    return placeholders


def generate_invoice_placeholders(invoice: Invoice | None, locale: str) -> dict[str, str]:
    placeholders = {
        'label': '',
        'invoiceNumber': '',
        'orderNumber': '',
        'issueDate': '',
        'dueDate': '',
        'lines': '',
        'totals': '',
        'recipientName': '',
        'recipientPurchaseOrderReference': '',
        'recipientVatId': '',
        'recipientAddress': '',
        'supplierAddressLine': '',
        'supplierContact': '',
        'supplierIban': '',
        'supplierBankName': '',
        'supplierLegal': '',

    }

    resolved_locale = Locale(locale)

    if invoice:
        # build label
        if invoice.invoice_type == INVOICE_TYPE_CANCELLATION:
            placeholders['label'] = 'Storno-Rechnung' if locale == 'de' else 'Credit Note'
        elif invoice.invoice_type_code == INVOICE_TYPE_INVOICE:
            placeholders['label'] = 'Rechnung' if locale == 'de' else 'Invoice'

        # get basic data
        placeholders['invoiceNumber'] = escape(invoice.invoice_number) or ""
        placeholders['issueDate'] += format_date(
            invoice.issue_date, 'medium', locale=invoice.locale)
        placeholders['dueDate'] += format_date(
            invoice.due_date, 'medium', locale=invoice.locale)

        # supplier data
        if invoice.supplier:

            supplier_address: list[str | None] = [
                invoice.supplier.get('line1', None),
                invoice.supplier.get('line2', None),
                invoice.supplier.get('line3', None),
                f'{invoice.supplier.get('zip_code', '')} {invoice.supplier.get('city', '')}',
            ]
            placeholders['supplierAddressLine'] += ', '.join([escape(x) for x in supplier_address if x is not None])  # noqa: E501

            placeholders['supplierIban'] += escape(
                invoice.supplier.get('iban', ''))

            placeholders['supplierBankName'] += escape(
                invoice.supplier.get('bankName', ''))

            supplier_contact: list[str | None] = [
                'Kontakt:' if locale == 'de' else 'Contact:',
                invoice.supplier.get('contact_name', None),
                invoice.supplier.get('contact_phone', None),
                invoice.supplier.get('contact_email', None),
            ]
            placeholders['supplierContact'] += '<br> '.join([escape(x) for x in supplier_contact if x is not None])  # noqa: E501

        # recipient data
        if invoice.recipient:
            recipient_name = f'{invoice.recipient.get('contact_firstname', '')} \
                  {invoice.recipient.get('contact_lastname', '')}'

            placeholders['recipientName'] += escape(recipient_name)

            placeholders['recipientPurchaseOrderReference'] += escape(
                invoice.recipient.get('purchase_order_reference', '')
            )

            placeholders['recipientVatId'] += escape(
                invoice.recipient.get('vat_id', ''))

            recipient_address: list[str | None] = [
                invoice.recipient.get('line1', None),
                invoice.recipient.get('line2', None),
                invoice.recipient.get('line3', None),
                f'{invoice.recipient.get('zip', '')} {invoice.recipient.get('city', '')}',
                f'{resolved_locale.territories[invoice.recipient.get('country', '').upper()]}'
            ]

            placeholders['recipientAddress'] += '<br> '.join([escape(x) for x in recipient_address if x is not None])  # noqa: E501

        # build items table
        taxes: dict[str, Decimal] = {}
        for line_item in invoice.line_items:
            quantity = f"{line_item.quantity:.10f}".rstrip("0").rstrip(".")
            placeholders['lines'] += f'<tr>\
              <td>{escape(quantity)}</td>\
              <td>{escape(line_item.name).replace("\n", "<br>")}</td>\
              <td>{format_currency(line_item.total_net,
                                   currency=invoice.currency,
                                   locale='de_DE' if locale == 'de' else 'en_GB')}</td>\
                </tr>'

            # compute tax line
            tax_name = line_item.tax_exemption_reason
            if not tax_name:
                tax_name = line_item.tax.label.get(
                    locale, '')
            tax_name = f'{line_item.tax_rate:.1f}% {tax_name}'

            if tax_name in taxes:
                taxes[tax_name] += line_item.total_tax
            else:
                taxes[tax_name] = line_item.total_tax

        # build totals table
        placeholders['totals'] += f'<tr>\
              <td class="net" colspan="2">{'Netto' if locale == 'de' else 'Subtotal'}</td>\
              <td class="net">{format_currency(invoice.total_net,
                                               currency=invoice.currency,
                                               locale='de_DE' if locale == 'de' else 'en_GB')}</td>\
              </tr>'

        for tax_name in taxes:  # noqa: PLC0206
            placeholders['totals'] += f'<tr>\
              <td class="tax" colspan="2">{tax_name}</td>\
              <td class="tax">{format_currency(taxes[tax_name],
                                               currency=invoice.currency,
                                               locale='de_DE' if locale == 'de' else 'en_GB')}</td>\
              </tr>'

        placeholders['totals'] += f'<tr>\
              <td class="net" colspan="2">{'Brutto' if locale == 'de' else 'Total'}</td>\
              <td class="net">{format_currency(invoice.total_gross,
                                               currency=invoice.currency,
                                               locale='de_DE' if locale == 'de' else 'en_GB')}</td>\
              </tr>'
    return placeholders
