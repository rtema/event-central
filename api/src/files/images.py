from __future__ import annotations

import base64
import logging
import warnings
from io import BytesIO

from PIL import Image

from src.core.errors import AppError

log = logging.getLogger("src.files")

# Constants
PREVIEW_MAX_EDGE = 128  # preview images are fixed to max 128x128 pixels


def open_image_safely(raw: bytes) -> Image.Image | None:
    """Return a fully-decoded, verified PIL image, or ``None`` if not an image.

    Raises ``FileRejected`` for decompression bombs or corrupt image data.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as probe:
                probe.verify()  # structural check; consumes the handle
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise AppError("Image exceeds the maximum allowed pixel count",
                       error="invalid_image",
                       http_status=400
                       ) from Image.DecompressionBombError
    except Exception:
        return None  # not a (recognizable) image

    # verify() leaves the image unusable — reopen and force a full decode.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            img = Image.open(BytesIO(raw))
            img.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise AppError("Image exceeds the maximum allowed pixel count",
                       error="invalid_image",
                       http_status=400
                       ) from Image.DecompressionBombError
    except Exception:
        raise AppError("Image could not be decoded",
                       error="invalid_image",
                       http_status=400
                       ) from None
    return img


# generate preview image
def generate_image_preview(image: Image.Image) -> str | None:
    """Base64 WebP thumbnail (<= PREVIEW_MAX_EDGE on the longest side)."""
    try:
        thumb = image.copy()
        thumb.thumbnail((PREVIEW_MAX_EDGE, PREVIEW_MAX_EDGE))
        if thumb.mode not in ("RGB", "RGBA"):
            thumb = thumb.convert("RGBA" if "A" in thumb.getbands() else "RGB")
        buf = BytesIO()
        thumb.save(buf, format="WEBP", quality=70, method=6)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        log.warning("preview generation failed", exc_info=True)
        return None

def _read_data(data: BytesIO | bytes | bytearray | memoryview) -> bytes:
    if isinstance(data, (bytes, bytearray, memoryview)):
        return bytes(data)
    # data is now narrowed to BytesIO -> tell/seek/read are fully typed
    pos = data.tell()
    data.seek(0)
    raw = data.read()
    data.seek(pos)
    return raw

# Standard JPEG (Annex K) luminance quantization table — used to estimate the
# encoding quality of a source JPEG.
_STD_LUMA_QT = (
    16, 11, 10, 16, 24, 40, 51, 61,
    12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56,
    14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68, 109, 103, 77,
    24, 35, 55, 64, 81, 104, 113, 92,
    49, 64, 78, 87, 103, 121, 120, 101,
    72, 92, 95, 98, 112, 100, 103, 99,
)


def _estimate_jpeg_quality(image: Image.Image) -> int | None:
    """Estimate a source JPEG's quality (1-100) from its quantization tables.

    Uses the means of the luminance table vs. the standard table, which is
    independent of zig-zag vs. natural ordering (libjpeg scales every entry by
    the same factor, so the relationship between means is linear).
    """
    qt = getattr(image, "quantization", None)
    if not qt:
        return None
    table = qt.get(0) or next(iter(qt.values()), None)
    if not table:
        return None

    mean_q = sum(table) / len(table)
    mean_base = sum(_STD_LUMA_QT) / len(_STD_LUMA_QT)
    if mean_base == 0:
        return None
    s = (mean_q * 100.0 - 50.0) / mean_base  # libjpeg scale factor
    if s <= 0:
        return 100
    quality = (200.0 - s) / 2.0 if s < 100 else 5000.0 / s
    return max(1, min(100, round(quality)))


def _has_alpha(image: Image.Image) -> bool:
    if image.mode in ("RGBA", "LA"):
        return True
    return image.mode == "P" and "transparency" in image.info


def _is_graphic(image: Image.Image) -> bool:
    """Few distinct colors => screenshot/logo/diagram => lossless wins."""
    try:
        return image.getcolors(maxcolors=256) is not None
    except Exception:
        return False


def create_webp(
    data: BytesIO | bytes | Image.Image,
    *,
    max_edge: int,
) -> bytes:
    """Downscale an image and re-encode it as WebP.

    The encoding mode is chosen from the *source* characteristics:

    * any transparency (PNG-style alpha)        -> lossless WebP (crisp alpha/edges)
    * opaque graphic (few colors, e.g. a PNG)  -> lossless WebP
    * already-degraded JPEG (low est. quality)  -> lossy WebP, capped near source
    * photographic / high-quality source        -> lossy WebP at a good default
    """
    if isinstance(data, Image.Image):
        image = data
    else:
        image = open_image_safely(_read_data(data))
        if image is None:
            raise AppError("Not a decodable image",
                           error="invalid_image",
                           http_status=400
                           )

    # Inspect source traits BEFORE copy/thumbnail (those drop .format / quant tables).
    source_format = (image.format or "").upper()
    alpha = _has_alpha(image)
    graphic = _is_graphic(image)
    jpeg_quality = _estimate_jpeg_quality(
        image) if source_format == "JPEG" else None

    # Downscale only (never upscale), preserving aspect ratio.
    if max(image.size) > max_edge:
        image = image.copy()
        image.thumbnail((max_edge, max_edge))

    save_kwargs: dict[str, object] = {"method": 6}
    if alpha:
        if image.mode not in ("RGBA", "LA"):
            image = image.convert("RGBA")
        if source_format == "PNG" or graphic:
            save_kwargs.update(lossless=True)
        else:
            save_kwargs.update(lossless=False, quality=82)
    else:
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        if source_format == "JPEG":
            if jpeg_quality is not None and jpeg_quality < 70:
                # Already lossy/degraded — don't spend bits re-preserving artifacts.
                save_kwargs.update(
                    lossless=False, quality=min(jpeg_quality + 5, 75))
            else:
                save_kwargs.update(lossless=False, quality=82)
        elif source_format == "PNG" and graphic:
            save_kwargs.update(lossless=True)
        else:
            save_kwargs.update(lossless=False, quality=82)

    buf = BytesIO()
    image.save(buf, format="WEBP", **save_kwargs)
    return buf.getvalue()
