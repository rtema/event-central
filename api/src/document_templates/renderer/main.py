import logging
import mimetypes
import os
from io import BytesIO
from pathlib import Path
from typing import Any

import pydyf  # pyright: ignore[reportMissingTypeStubs]
from jinja2 import exceptions
from qrcode import QRCode, constants
from weasyprint import CSS, HTML, Attachment  # type: ignore
from weasyprint.text.fonts import FontConfiguration  # type: ignore

from src.document_templates.models import DocumentTemplate, DocumentTemplateFile
from src.document_templates.renderer.placeholders import (
    generate_document_template_placeholders,
    generate_event_placeholders,
    generate_image_placeholders,
    generate_invoice_placeholders,
    generate_order_placeholders,
    template_renderer_sandbox,
)
from src.events.models import Event
from src.files.service import storage_key_for_file
from src.invoices.models import Invoice
from src.orders.models import Order
from src.storage.s3 import get_storage

log = logging.getLogger("src.document_templates")

# configure logger
logging.getLogger("fontTools").setLevel(logging.WARNING)
logging.getLogger("fontTools.subset").setLevel(logging.WARNING)
logging.getLogger("fontTools.subset.timer").setLevel(logging.WARNING)
logging.getLogger("fontTools.ttLib.ttFont").setLevel(logging.WARNING)

DOCUMENT_FONTS: list[dict[str, str | int]] = [
    {
        'filename': 'Roboto-Condensed.ttf',
        'name': 'Roboto Condensed',
        'weight': 400
    },
    {
        'filename': 'Roboto-Condensed-Bold.ttf',
        'name': 'Roboto Condensed Bold',
        'weight': 600
    },

]


def resolve_font(
        url: str,
        document_template_files: list[DocumentTemplateFile]
) -> dict[str, str | bytes]:
    filename = url.removeprefix('font://')
    filename: str = filename.replace(os.sep, '')
    filename: str = filename.replace('..', '')

    # check if font is in document_template_files
    for document_template_file in document_template_files:
        if (str(document_template_file.id) == filename and
                document_template_file.type == "font"):

            file = document_template_file.file

            # get file from storage
            contents = get_storage().get(storage_key_for_file(file))

            return {
                'mime_type': file.mime,
                'string': contents
            }

    # check if default font exists
    fonts_dir = os.path.abspath(
        os.path.join(Path(__file__).resolve().parent.parent, 'default_fonts'))

    path = os.path.abspath(os.path.join(fonts_dir, filename))

    # Path traversal protection: ensure path is within root_dir
    if not path.startswith(fonts_dir + os.sep):
        raise PermissionError(
            f'Access denied outside root directory: {path}')

    if not os.path.isfile(path):
        log.error(f'Font not found: {path}')
        return {
            'mime_type': '',
            'string': b''
        }

    for font in DOCUMENT_FONTS:
        if font['filename'] == filename:
            contents = Path(path).read_bytes()
            mime_type, _mime_type = mimetypes.guess_type(path)
            return {
                'mime_type': mime_type or 'font/ttf',
                'string': contents
            }

    # font not available
    return {
        'mime_type': '',
        'string': b''
    }


def resolve_image(
        url: str,
        document_template_files: list[DocumentTemplateFile]
) -> dict[str, str | bytes]:
    filename: str = url.removeprefix('image://')
    filename: str = filename.replace(os.sep, '')
    filename: str = filename.replace('..', '')

    # check if image is in document_template_files
    for document_template_file in document_template_files:
        if (str(document_template_file.id) == filename and
                document_template_file.type == "image"):

            file = document_template_file.file

            # get file from storage
            contents = get_storage().get(storage_key_for_file(file))

            return {
                'mime_type': file.mime,
                'string': contents
            }

    # check if default image exists
    images_dir = os.path.abspath(
        os.path.join(Path(__file__).resolve(),
                     '..',
                     'default_images'))

    path = os.path.abspath(os.path.join(images_dir, filename))

    # Path traversal protection: ensure path is within root_dir
    if not path.startswith(images_dir + os.sep):
        raise PermissionError(
            f'Access denied outside root directory: {path}')

    if not os.path.isfile(path):
        log.error(f'File not found: {path}')
        return {
            'mime_type': '',
            'string': b''
        }

    # load file
    contents = Path(path).read_bytes()
    mime_type, _mime_type = mimetypes.guess_type(path)
    return {
        'mime_type': mime_type or 'application/octet-stream',
        'string': contents
    }


def resolve_qrcode(url: str) -> dict[str, str | bytes]:
    data = url.removeprefix('qrcode://')

    qr = QRCode(
        version=None,
        error_correction=constants.ERROR_CORRECT_M,
        box_size=4,
        border=4,

    )
    qr.add_data(data)
    qr.make(fit=True)
    buf = BytesIO()
    qr.make_image().save(buf)
    buf.seek(0)

    return {
        'mime_type': 'image/png',
        'string': buf.read()
    }


def generate_font_css(document_template_files: list[DocumentTemplateFile]):
    css = ''
    for font in DOCUMENT_FONTS:
        css += f'''
@font-face {{
  font-family: {font['name']};
  font-weight: {font['weight']};
  src: url(font://{font['filename']});
}}
'''

    for document_template_file in document_template_files:
        if document_template_file.type == "font":
            css += f'''
@font-face {{
  font-family: {document_template_file.font_name};
  font-weight: {document_template_file.font_weight};
  src: url(font://{document_template_file.id});
}}
'''
    return css


def _default_finisher(_document: Any, _pdf: pydyf.PDF) -> None:
    return None


def render_document(
    document_template: DocumentTemplate,
        locale: str,
        event: Event,
        order: Order | None = None,
        invoice: Invoice | None = None,
        attachments: list[Attachment] | None = None,
        pdf_variant: str | None = None,
        finisher: Any | None = None,
) -> BytesIO:

    # generate placeholder data
    placeholders: dict[str, str | dict[str, str]] = {
        'locale': locale,
        'event': generate_event_placeholders(event, locale),
        'order': generate_order_placeholders(order, locale),
        'invoice': generate_invoice_placeholders(invoice, locale),
        'template': generate_document_template_placeholders(document_template, locale),
        'images': generate_image_placeholders(document_template, locale),
    }

    # personalize html
    content = document_template.html
    try:
        html_template = template_renderer_sandbox.from_string(
            document_template.html or "")
        content = html_template.render(**placeholders)
    except exceptions.SecurityError as e:
        print(f'Security error: {e}')

    # personalize template
    styles = document_template.css
    try:
        css_template = template_renderer_sandbox.from_string(
            document_template.css or "")
        styles = css_template.render(**placeholders)
    except exceptions.SecurityError as e:
        print(f'Security error: {e}')

    # fetch list of document files
    document_template_files: list[DocumentTemplateFile] = document_template.document_template_files

    # generate a fetcher function
    def url_fetcher(url: str) -> dict[str, str | bytes]:
        if url.startswith('font://'):
            return resolve_font(url, document_template_files)

        if url.startswith('qrcode://'):
            return resolve_qrcode(url)

        if url.startswith('image://'):
            return resolve_image(url, document_template_files)

        # assume: if url.startswith('file://'):
        return {
            'mime_type': '',
            'string': b''
        }

    # get all font definitions
    font_config = FontConfiguration()
    fonts = CSS(
        string=generate_font_css(document_template.document_template_files),
        font_config=font_config,
        url_fetcher=url_fetcher
    )

    # load document template
    html = HTML(
        string=content,
        url_fetcher=url_fetcher
    )

    # load css
    css = CSS(
        string=styles,
        font_config=font_config,
        url_fetcher=url_fetcher
    )

    # generate pdf
    data = BytesIO()
    html.write_pdf(  # type: ignore
        data,
        stylesheets=[fonts, css],
        font_config=font_config,
        finisher=finisher or _default_finisher,
        attachments=attachments,
        pdf_variant=pdf_variant,
        custom_metadata=True,
    )
    data.seek(0)

    # return generated document
    return data
